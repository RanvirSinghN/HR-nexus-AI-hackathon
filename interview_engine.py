
import json
import os
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI

from prompts import (
    build_follow_up_prompt,
    build_question_generation_prompt,
)


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

def create_interview_session(
    questions: list[dict[str, Any]],
    cv_text: str,
    job_description: str,
    company: str,
    role: str,
    interview_type: str,
) -> dict[str, Any]:
    """
    Create the initial interview session after generating the questions.
    """
    if not questions:
        raise ValueError("At least one interview question is required.")

    lines_of_questioning = []

    for question in questions:
        lines_of_questioning.append(
            {
                "line_id": question["id"],
                "category": question["category"],
                "main_question": question,
                "responses": [],
                "follow_up_count": 0,
                "line_complete": False,
            }
        )

    return {
        "session_id": str(uuid4()),
        "candidate_context": {
            "cv_text": cv_text,
            "job_description": job_description,
            "company": company,
            "role": role,
            "interview_type": interview_type,
        },
        "questions": questions,
        "current_question_index": 0,
        "lines_of_questioning": lines_of_questioning,
        "interview_complete": False,
    }

def get_current_line(
    session: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Return the active line of questioning.
    """
    current_index = session["current_question_index"]
    lines = session["lines_of_questioning"]

    if current_index >= len(lines):
        return None

    return lines[current_index]

def record_response(
    session: dict[str, Any],
    question: str,
    answer: str,
    question_type: str,
    follow_up_number: int | None = None,
) -> dict[str, Any]:
    """
    Add a candidate response to the current line of questioning.
    """
    if not answer or not answer.strip():
        raise ValueError("Candidate answer cannot be empty.")

    if question_type not in {"main", "follow_up"}:
        raise ValueError(
            "question_type must be either 'main' or 'follow_up'."
        )

    current_line = get_current_line(session)

    if current_line is None:
        raise InterviewEngineError(
            "There is no active line of questioning."
        )

    response = {
        "question_type": question_type,
        "question": question,
        "answer": answer,
    }

    if question_type == "follow_up":
        if follow_up_number is None:
            raise ValueError(
                "follow_up_number is required for a follow-up response."
            )

        response["follow_up_number"] = follow_up_number

    current_line["responses"].append(response)

    return response

def get_previous_follow_ups(
    line: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Return previous follow-up questions and answers from a line.
    """
    return [
        {
            "question": response["question"],
            "answer": response["answer"],
        }
        for response in line["responses"]
        if response["question_type"] == "follow_up"
    ]

def normalise_question_text(question: str) -> set[str]:
    """
    Convert a question into a simplified set of meaningful words.
    """
    ignored_words = {
        "a",
        "an",
        "and",
        "are",
        "can",
        "could",
        "did",
        "do",
        "for",
        "how",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "was",
        "were",
        "what",
        "which",
        "with",
        "you",
        "your",
    }

    cleaned_text = "".join(
        character.lower()
        if character.isalnum() or character.isspace()
        else " "
        for character in question
    )

    return {
        word
        for word in cleaned_text.split()
        if word not in ignored_words
    }


def questions_are_too_similar(
    first_question: str,
    second_question: str,
    similarity_threshold: float = 0.6,
) -> bool:
    """
    Check whether two questions contain substantially similar wording.
    """
    first_words = normalise_question_text(first_question)
    second_words = normalise_question_text(second_question)

    if not first_words or not second_words:
        return False

    overlap = first_words & second_words
    smaller_word_count = min(
        len(first_words),
        len(second_words),
    )

    similarity = len(overlap) / smaller_word_count

    return similarity >= similarity_threshold

def complete_current_line(
    session: dict[str, Any],
) -> None:
    """
    Mark the current line as complete and move to the next main question.
    """
    current_line = get_current_line(session)

    if current_line is None:
        raise InterviewEngineError(
            "There is no active line to complete."
        )

    current_line["line_complete"] = True
    session["current_question_index"] += 1

    if session["current_question_index"] >= len(
        session["lines_of_questioning"]
    ):
        session["interview_complete"] = True

def process_candidate_answer(
    session: dict[str, Any],
    answer: str,
    question_type: str = "main",
    follow_up_question: str | None = None,
    client: OpenAI | None = None,
) -> dict[str, Any]:
    """
    Record an answer and decide what the interview should do next.
    """
    current_line = get_current_line(session)

    if current_line is None:
        return {
            "action": "interview_complete",
            "interview_complete": True,
        }

    if question_type == "main":
        current_question = current_line["main_question"]["question"]
        follow_up_number = None
    elif question_type == "follow_up":
        if not follow_up_question:
            raise ValueError(
                "follow_up_question is required for a follow-up answer."
            )

        current_question = follow_up_question
        follow_up_number = current_line["follow_up_count"]
    else:
        raise ValueError(
            "question_type must be either 'main' or 'follow_up'."
        )

    record_response(
        session=session,
        question=current_question,
        answer=answer,
        question_type=question_type,
        follow_up_number=follow_up_number,
    )

    candidate_context = session["candidate_context"]

    previous_follow_ups = get_previous_follow_ups(current_line)
    current_line["follow_up_count"] = len(previous_follow_ups)

    follow_up_result = evaluate_follow_up_need(
        main_question=current_line["main_question"]["question"],
        candidate_answer=answer,
        cv_text=candidate_context["cv_text"],
        job_description=candidate_context["job_description"],
        role=candidate_context["role"],
        interview_type=candidate_context["interview_type"],
        previous_follow_ups=previous_follow_ups,
        follow_up_count=current_line["follow_up_count"],
        maximum_follow_ups=3,
        client=client,
    )

    if follow_up_result["ask_follow_up"]:
        generated_question = follow_up_result["follow_up_question"]

        previous_questions = [
            item["question"]
            for item in previous_follow_ups
        ]

        repeated_question = any(
            questions_are_too_similar(
                generated_question,
                previous_question,
            )
            for previous_question in previous_questions
        )

        if repeated_question:
            complete_current_line(session)

            if session["interview_complete"]:
                return {
                    "action": "interview_complete",
                    "line_complete": True,
                    "interview_complete": True,
                    "completion_reason": (
                        "The proposed follow-up was too similar to an "
                        "earlier question."
                    ),
                }

            next_line = get_current_line(session)

            return {
                "action": "ask_main_question",
                "next_question": next_line["main_question"],
                "line_complete": True,
                "interview_complete": False,
                "completion_reason": (
                    "The proposed follow-up was too similar to an "
                    "earlier question."
                ),
            }

        current_line["follow_up_count"] += 1

        return {
            "action": "ask_follow_up",
            "follow_up_question": generated_question,
            "missing_information": follow_up_result[
                "missing_information"
            ],
            "reason": follow_up_result["reason"],
            "follow_up_count": current_line["follow_up_count"],
            "line_complete": False,
            "interview_complete": False,
        }

    complete_current_line(session)

    if session["interview_complete"]:
        return {
            "action": "interview_complete",
            "line_complete": True,
            "interview_complete": True,
        }

    next_line = get_current_line(session)

    return {
        "action": "ask_main_question",
        "next_question": next_line["main_question"],
        "line_complete": True,
        "interview_complete": False,
    }

def build_interview_output(
    session: dict[str, Any],
) -> dict[str, Any]:
    """
    Produce the structured output for the feedback mechanism.
    """
    completed_main_questions = sum(
        1
        for line in session["lines_of_questioning"]
        if line["line_complete"]
    )

    total_follow_ups = sum(
        line["follow_up_count"]
        for line in session["lines_of_questioning"]
    )

    total_responses = sum(
        len(line["responses"])
        for line in session["lines_of_questioning"]
    )

    return {
        "session_id": session["session_id"],
        "candidate_context": session["candidate_context"],
        "interview_status": (
            "completed"
            if session["interview_complete"]
            else "in_progress"
        ),
        "lines_of_questioning": session[
            "lines_of_questioning"
        ],
        "summary": {
            "completed_main_questions": completed_main_questions,
            "total_main_questions": len(session["questions"]),
            "total_follow_up_questions": total_follow_ups,
            "total_responses": total_responses,
        },
    }

def evaluate_follow_up_need(
    main_question: str,
    candidate_answer: str,
    cv_text: str,
    job_description: str,
    role: str,
    interview_type: str,
    previous_follow_ups: list[dict[str, str]] | None = None,
    follow_up_count: int = 0,
    maximum_follow_ups: int = 3,
    client: OpenAI | None = None,
) -> dict[str, Any]:
    """
    Decide whether another follow-up question should be asked.

    Args:
        main_question:
            The original primary interview question.

        candidate_answer:
            The candidate's latest answer.

        cv_text:
            Candidate CV text.

        job_description:
            Target job-description text.

        role:
            Target role title.

        interview_type:
            Selected interview style.

        previous_follow_ups:
            Earlier follow-up questions and answers from the same line
            of questioning.

        follow_up_count:
            Number of follow-up questions already asked.

        maximum_follow_ups:
            Maximum number of follow-ups allowed.

        client:
            Optional OpenAI client for testing.

    Returns:
        A dictionary describing whether another follow-up is needed.
    """
    if previous_follow_ups is None:
        previous_follow_ups = []

    validate_follow_up_inputs(
        main_question=main_question,
        candidate_answer=candidate_answer,
        cv_text=cv_text,
        job_description=job_description,
        role=role,
        interview_type=interview_type,
        previous_follow_ups=previous_follow_ups,
        follow_up_count=follow_up_count,
        maximum_follow_ups=maximum_follow_ups,
    )

    if follow_up_count >= maximum_follow_ups:
        return {
            "ask_follow_up": False,
            "follow_up_question": None,
            "missing_information": [],
            "reason": "The maximum number of follow-up questions has been reached.",
            "line_complete": True,
        }

    prompt = build_follow_up_prompt(
        main_question=main_question,
        candidate_answer=candidate_answer,
        cv_text=cv_text,
        job_description=job_description,
        role=role,
        interview_type=interview_type,
        previous_follow_ups=previous_follow_ups,
        follow_up_count=follow_up_count,
        maximum_follow_ups=maximum_follow_ups,
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
            f"Follow-up generation failed: {exc}"
        ) from exc

    result = parse_json_object_response(response.output_text)
    validate_follow_up_result(result)

    return result

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

def validate_follow_up_inputs(
    main_question: str,
    candidate_answer: str,
    cv_text: str,
    job_description: str,
    role: str,
    interview_type: str,
    previous_follow_ups: list[dict[str, str]],
    follow_up_count: int,
    maximum_follow_ups: int,
) -> None:
    """
    Validate the information used to generate a follow-up question.
    """
    required_fields = {
        "main question": main_question,
        "candidate answer": candidate_answer,
        "CV text": cv_text,
        "job description": job_description,
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

    if follow_up_count < 0:
        raise ValueError("follow_up_count cannot be negative.")

    if maximum_follow_ups < 0:
        raise ValueError("maximum_follow_ups cannot be negative.")

    if follow_up_count != len(previous_follow_ups):
        raise ValueError(
            "follow_up_count must match the number of previous follow-ups."
        )

    for index, follow_up in enumerate(previous_follow_ups, start=1):
        if not isinstance(follow_up, dict):
            raise ValueError(
                f"Previous follow-up {index} must be a dictionary."
            )

        if "question" not in follow_up or "answer" not in follow_up:
            raise ValueError(
                f"Previous follow-up {index} must contain "
                "'question' and 'answer'."
            )


def parse_json_object_response(
    raw_output: str,
) -> dict[str, Any]:
    """
    Convert a model response containing one JSON object into a dictionary.
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

    if not isinstance(parsed_output, dict):
        raise InterviewEngineError(
            "The follow-up response must be a JSON object."
        )

    return parsed_output


def validate_follow_up_result(
    result: dict[str, Any],
) -> None:
    """
    Check that a generated follow-up decision has the required structure.
    """
    required_fields = {
        "ask_follow_up",
        "follow_up_question",
        "missing_information",
        "reason",
        "line_complete",
    }

    missing_fields = required_fields - result.keys()

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise InterviewEngineError(
            f"Follow-up result is missing: {missing}"
        )

    if not isinstance(result["ask_follow_up"], bool):
        raise InterviewEngineError(
            "ask_follow_up must be True or False."
        )

    if not isinstance(result["line_complete"], bool):
        raise InterviewEngineError(
            "line_complete must be True or False."
        )

    if not isinstance(result["missing_information"], list):
        raise InterviewEngineError(
            "missing_information must be a list."
        )

    if not isinstance(result["reason"], str):
        raise InterviewEngineError(
            "reason must be a string."
        )

    if result["ask_follow_up"]:
        if not isinstance(result["follow_up_question"], str):
            raise InterviewEngineError(
                "A follow-up question must be provided when "
                "ask_follow_up is True."
            )

        if not result["follow_up_question"].strip():
            raise InterviewEngineError(
                "The follow-up question cannot be empty."
            )

        if result["line_complete"]:
            raise InterviewEngineError(
                "line_complete cannot be True when another "
                "follow-up is required."
            )

    else:
        if result["follow_up_question"] is not None:
            raise InterviewEngineError(
                "follow_up_question must be None when "
                "ask_follow_up is False."
            )

        if not result["line_complete"]:
            raise InterviewEngineError(
                "line_complete must be True when no follow-up "
                "is required."
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
