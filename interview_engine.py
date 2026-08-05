
import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from prompts import build_question_generation_prompt


load_dotenv()


class InterviewEngineError(Exception):
    """Raised when the interview engine cannot generate a valid result."""


def get_openai_client() -> OpenAI:
    """
    Create and return an OpenAI client using the API key stored in .env.
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise InterviewEngineError(
            "OPENAI_API_KEY was not found. Add it to your .env file."
        )

    return OpenAI(api_key=api_key)


def generate_questions(
    cv_text: str,
    job_description: str,
    company: str,
    role: str,
    interview_type: str,
    number_of_questions: int = 5,
    client: OpenAI | None = None,
) -> list[dict[str, Any]]:
    """
    Generate tailored primary interview questions.

    Args:
        cv_text:
            Extracted or pasted CV text.

        job_description:
            Extracted or pasted job-description text.

        company:
            Name of the company.

        role:
            Target role title.

        interview_type:
            Interview style, such as competency, behavioural,
            technical or mixed.

        number_of_questions:
            Number of main questions to generate. Must be between 4 and 6.

        client:
            Optional OpenAI client. This makes testing easier because a
            fake client can be supplied.

    Returns:
        A list of interview-question dictionaries.

    Raises:
        ValueError:
            If required inputs are missing or the number of questions
            is outside the allowed range.

        InterviewEngineError:
            If the AI response cannot be generated or validated.
    """
    validate_question_inputs(
        cv_text=cv_text,
        job_description=job_description,
        company=company,
        role=role,
        interview_type=interview_type,
        number_of_questions=number_of_questions,
    )

    prompt = build_question_generation_prompt(
        cv_text=cv_text,
        job_description=job_description,
        company=company,
        role=role,
        interview_type=interview_type,
        number_of_questions=number_of_questions,
    )

    if client is None:
        client = get_openai_client()

    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            input=prompt,
        )
    except Exception as exc:
        raise InterviewEngineError(
            f"Question generation failed: {exc}"
        ) from exc

    raw_output = response.output_text

    questions = parse_json_response(raw_output)
    validate_generated_questions(
        questions=questions,
        expected_count=number_of_questions,
    )

    return questions


def validate_question_inputs(
    cv_text: str,
    job_description: str,
    company: str,
    role: str,
    interview_type: str,
    number_of_questions: int,
) -> None:
    """
    Validate the information supplied by the front end.
    """
    required_fields = {
        "CV text": cv_text,
        "job description": job_description,
        "company": company,
        "role": role,
        "interview type": interview_type,
    }

    missing_fields = [
        field_name
        for field_name, value in required_fields.items()
        if not value or not value.strip()
    ]

    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Missing required information: {missing}")

    if not 4 <= number_of_questions <= 6:
        raise ValueError(
            "number_of_questions must be between 4 and 6."
        )


def parse_json_response(raw_output: str) -> list[dict[str, Any]]:
    """
    Convert the model's JSON response into a Python list.

    The function also removes Markdown code fences in case the model
    returns the JSON inside a ```json block.
    """
    cleaned_output = raw_output.strip()

    if cleaned_output.startswith("```"):
        cleaned_output = cleaned_output.removeprefix("```json")
        cleaned_output = cleaned_output.removeprefix("```")
        cleaned_output = cleaned_output.removesuffix("```")
        cleaned_output = cleaned_output.strip()

    try:
        parsed_output = json.loads(cleaned_output)
    except json.JSONDecodeError as exc:
        raise InterviewEngineError(
            "The model did not return valid JSON."
        ) from exc

    if isinstance(parsed_output, dict):
        questions = parsed_output.get("questions")
    else:
        questions = parsed_output

    if not isinstance(questions, list):
        raise InterviewEngineError(
            "The model response must contain a list called 'questions'."
        )

    return questions


def validate_generated_questions(
    questions: list[dict[str, Any]],
    expected_count: int,
) -> None:
    """
    Check that every generated question has the fields needed by the app.
    """
    if len(questions) != expected_count:
        raise InterviewEngineError(
            f"Expected {expected_count} questions, "
            f"but received {len(questions)}."
        )

    required_fields = {
        "id",
        "category",
        "question",
        "reason",
    }

    seen_ids = set()

    for position, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            raise InterviewEngineError(
                f"Question {position} is not a dictionary."
            )

        missing_fields = required_fields - question.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise InterviewEngineError(
                f"Question {position} is missing: {missing}"
            )

        question_id = question["id"]

        if question_id in seen_ids:
            raise InterviewEngineError(
                f"Duplicate question ID found: {question_id}"
            )

        seen_ids.add(question_id)

        if not str(question["question"]).strip():
            raise InterviewEngineError(
                f"Question {position} has no question text."
            )


def get_question_by_index(
    questions: list[dict[str, Any]],
    question_index: int,
) -> dict[str, Any] | None:
    """
    Return the question at the given position.

    Returns None when the interview has reached the end.
    """
    if question_index < 0:
        raise ValueError("question_index cannot be negative.")

    if question_index >= len(questions):
        return None

    return questions[question_index]


def has_more_questions(
    questions: list[dict[str, Any]],
    current_index: int,
) -> bool:
    """
    Check whether another main question remains.
    """
    return current_index + 1 < len(questions)
