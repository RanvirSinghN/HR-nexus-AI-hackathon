"""Convert interview intake data into an anonymised API-ready payload."""

import json
import re
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


SCHEMA_VERSION = "1.1"

NON_NAME_LABELS = {
    "curriculum vitae",
    "personal profile",
    "professional summary",
    "technical skills",
    "work experience",
    "employment history",
    "professional experience",
    "academic background",
}

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_PATTERN = re.compile(
    r"\b(?:https?://|www\.|linkedin\.com/|github\.com/)\S+", re.IGNORECASE
)
UK_POSTCODE_PATTERN = re.compile(
    r"\b(?:GIR\s?0AA|[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})\b", re.IGNORECASE
)
DATE_OF_BIRTH_PATTERN = re.compile(
    r"\b(?:date\s+of\s+birth|d\.?\s*o\.?\s*b\.?|dob)\s*[:-]?\s*[^\n]+",
    re.IGNORECASE,
)
PERSONAL_FIELD_PATTERN = re.compile(
    r"^\s*(?:nationality|gender|sex|marital status|age|pronouns?)\s*[:-].*$",
    re.IGNORECASE,
)


class CVProcessingError(ValueError):
    """Raised when an uploaded CV cannot produce usable interview text."""


def _read_pdf_bytes(pdf_source: bytes | bytearray | BinaryIO) -> bytes:
    if isinstance(pdf_source, (bytes, bytearray)):
        return bytes(pdf_source)

    if hasattr(pdf_source, "getvalue"):
        return bytes(pdf_source.getvalue())

    if hasattr(pdf_source, "read"):
        current_position = pdf_source.tell() if hasattr(pdf_source, "tell") else None
        data = pdf_source.read()
        if current_position is not None and hasattr(pdf_source, "seek"):
            pdf_source.seek(current_position)
        return bytes(data)

    raise CVProcessingError("The CV must be supplied as PDF bytes or a file-like object.")


def extract_pdf_text(pdf_source: bytes | bytearray | BinaryIO) -> str:
    """Extract the complete text from a PDF without saving the original file."""
    pdf_bytes = _read_pdf_bytes(pdf_source)
    if not pdf_bytes.startswith(b"%PDF-"):
        raise CVProcessingError("The uploaded CV is not a valid PDF file.")

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise CVProcessingError("Password-protected CVs are not supported.") from exc
        page_text = [(page.extract_text() or "").strip() for page in reader.pages]
    except (PdfReadError, OSError, ValueError) as exc:
        raise CVProcessingError("The CV PDF could not be read.") from exc

    text = "\n".join(part for part in page_text if part)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if not text:
        raise CVProcessingError(
            "No text could be extracted from the CV. Please use a text-based PDF rather than a scan."
        )

    return text


def _contains_phone_number(text: str) -> bool:
    for match in re.finditer(r"(?<!\w)\+?[\d][\d\s().-]{7,}\d(?!\w)", text):
        if len(re.sub(r"\D", "", match.group())) >= 9:
            return True
    return False


def _looks_like_candidate_name(line: str, nearby_lines: list[str]) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", line)
    if not 2 <= len(words) <= 5 or len(line) > 60:
        return False

    if line.casefold().strip(":") in NON_NAME_LABELS:
        return False

    looks_title_cased = all(word[0].isupper() for word in words)
    nearby_contact_details = any(
        EMAIL_PATTERN.search(item) or URL_PATTERN.search(item) or _contains_phone_number(item)
        for item in nearby_lines
    )
    return looks_title_cased and nearby_contact_details


def _redact_phone_numbers(text: str) -> tuple[str, int]:
    count = 0

    def replace_phone(match: re.Match) -> str:
        nonlocal count
        if len(re.sub(r"\D", "", match.group())) < 9:
            return match.group()
        count += 1
        return "[PHONE REDACTED]"

    redacted = re.sub(r"(?<!\w)\+?[\d][\d\s().-]{7,}\d(?!\w)", replace_phone, text)
    return redacted, count


def anonymise_cv_text(text: str) -> tuple[str, list[str]]:
    """Remove likely direct identifiers while retaining interview-relevant evidence."""
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    candidate_name = None

    for index, line in enumerate(non_empty_lines[:6]):
        if _looks_like_candidate_name(line, non_empty_lines[index + 1 : index + 5]):
            candidate_name = line
            break

    redactions: set[str] = set()
    anonymised_lines = []

    for line in lines:
        if PERSONAL_FIELD_PATTERN.match(line):
            redactions.add("protected_or_personal_characteristics")
            continue

        if candidate_name and line.casefold() == candidate_name.casefold():
            anonymised_lines.append("[NAME REDACTED]")
            redactions.add("candidate_name")
            continue

        if candidate_name:
            line, name_count = re.subn(
                re.escape(candidate_name), "[NAME REDACTED]", line, flags=re.IGNORECASE
            )
            if name_count:
                redactions.add("candidate_name")

        line, email_count = EMAIL_PATTERN.subn("[EMAIL REDACTED]", line)
        line, url_count = URL_PATTERN.subn("[PROFILE LINK REDACTED]", line)
        line, postcode_count = UK_POSTCODE_PATTERN.subn("[POSTCODE REDACTED]", line)
        line, dob_count = DATE_OF_BIRTH_PATTERN.subn("[DATE OF BIRTH REDACTED]", line)
        line, phone_count = _redact_phone_numbers(line)

        if email_count:
            redactions.add("email_address")
        if url_count:
            redactions.add("profile_url")
        if postcode_count:
            redactions.add("postcode")
        if dob_count:
            redactions.add("date_of_birth")
        if phone_count:
            redactions.add("phone_number")

        anonymised_lines.append(line)

    anonymised_text = "\n".join(anonymised_lines)
    anonymised_text = re.sub(r"\n{3,}", "\n\n", anonymised_text).strip()
    return anonymised_text, sorted(redactions)


def build_interview_payload(
    cv_pdf: bytes | bytearray | BinaryIO,
    job_title: str,
    company: str,
    job_description: str,
) -> dict:
    """Return a JSON-serialisable payload for the interview API."""
    required_fields = {
        "job title": job_title,
        "company": company,
        "job description": job_description,
    }
    missing = [label for label, value in required_fields.items() if not value.strip()]
    if missing:
        raise ValueError("Missing required fields: " + ", ".join(missing))

    cv_text = extract_pdf_text(cv_pdf)
    anonymised_text, redactions = anonymise_cv_text(cv_text)

    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": "anonymous_candidate",
        "cv_text": anonymised_text,
        "job": {
            "title": job_title.strip(),
            "company": company.strip(),
            "description": job_description.strip(),
        },
        "interview_preferences": {
            "answer_mode": "typed",
            "question_delivery": "one_at_a_time",
            "use_follow_up_questions": True,
            "provide_final_report": True,
        },
        "responsible_ai": {
            "candidate_identity": "anonymous",
            "direct_identifiers_removed": redactions,
            "exclude_protected_characteristics": True,
            "evaluate_role_relevant_information_only": True,
            "automated_anonymisation_is_best_effort": True,
            "manual_review_recommended_before_external_api_use": True,
        },
    }


def payload_to_json(payload: dict) -> str:
    """Serialise an interview payload for an API body or local file."""
    return json.dumps(payload, indent=2, ensure_ascii=False)


def save_interview_json(payload: dict, output_directory: str | Path) -> Path:
    """Save a payload locally and return its path."""
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "latest_interview_payload.json"
    json_path.write_text(payload_to_json(payload), encoding="utf-8")
    return json_path
