from typing import Any, TypedDict


class InterviewQuestion(TypedDict):
    id: int
    category: str
    question: str
    reason: str


class InterviewResponse(TypedDict, total=False):
    question_type: str
    question: str
    answer: str
    follow_up_number: int
    skipped: bool


class InterviewLine(TypedDict):
    line_id: int
    category: str
    main_question: InterviewQuestion
    responses: list[InterviewResponse]
    follow_up_count: int
    line_complete: bool


class InterviewSession(TypedDict):
    session_id: str
    candidate_context: dict[str, Any]
    questions: list[InterviewQuestion]
    current_question_index: int
    lines_of_questioning: list[InterviewLine]
    interview_complete: bool

