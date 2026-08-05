def build_question_generation_prompt(
    cv_text: str,
    job_description: str,
    company: str,
    role: str,
    interview_type: str,
    number_of_questions: int,
) -> str:
    """
    Build the prompt used to generate tailored primary interview questions.
    """

    return f"""
You are an expert interview coach designing a realistic mock interview.

Generate exactly {number_of_questions} primary interview questions for the candidate.

Candidate information:

COMPANY:
{company}

ROLE:
{role}

INTERVIEW TYPE:
{interview_type}

CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

Your task:

1. Identify the candidate's most relevant experience, skills and achievements.
2. Identify the most important requirements in the job description.
3. Generate questions that test the candidate against those requirements.
4. Tailor the questions to the candidate's actual CV.
5. Use a varied set of categories.
6. Avoid duplicate or overly similar questions.
7. Do not generate follow-up questions yet.
8. Do not provide model answers or feedback.
9. Return valid JSON only.

The questions should include an appropriate mixture of:

- Motivation and company fit
- Role understanding
- Competency or behavioural examples
- Technical or analytical skills
- Teamwork and communication
- Problem solving
- Strengths, development or reflection

Prioritise categories that are most relevant to the selected interview type.

Each question must have:

- id: an integer beginning at 1
- category: a short category name
- question: the exact question to ask the candidate
- reason: a concise explanation of why this question was selected

Return the result in exactly this structure:

{{
    "questions": [
        {{
            "id": 1,
            "category": "Motivation",
            "question": "Why are you interested in this role?",
            "reason": "The role requires clear motivation and understanding of the organisation."
        }}
    ]
}}

Important requirements:

- Return exactly {number_of_questions} questions.
- Use consecutive IDs beginning at 1.
- Every question must be answerable using the candidate's experience or motivation.
- Questions should sound natural when spoken by an interviewer.
- Do not include Markdown.
- Do not include code fences.
- Do not include any text before or after the JSON.
""".strip()

def build_follow_up_prompt(
    main_question: str,
    candidate_answer: str,
    cv_text: str,
    job_description: str,
    role: str,
    interview_type: str,
    previous_follow_ups: list[dict],
    follow_up_count: int,
    maximum_follow_ups: int = 3,
) -> str:
    """
    Build the prompt used to decide whether a follow-up question is needed.
    """

    previous_follow_up_text = (
        "\n".join(
            [
                (
                    f"Follow-up {index + 1}: {item['question']}\n"
                    f"Answer: {item['answer']}"
                )
                for index, item in enumerate(previous_follow_ups)
            ]
        )
        if previous_follow_ups
        else "No follow-up questions have been asked yet."
    )

    return f"""
You are conducting an adaptive mock interview.

Your task is to decide whether the candidate's current line of
questioning requires another follow-up question.

TARGET ROLE:
{role}

INTERVIEW TYPE:
{interview_type}

ORIGINAL QUESTION:
{main_question}

LATEST CANDIDATE ANSWER:
{candidate_answer}

PREVIOUS FOLLOW-UPS AND ANSWERS:
{previous_follow_up_text}

CANDIDATE CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

FOLLOW-UP COUNT:
{follow_up_count}

MAXIMUM FOLLOW-UPS:
{maximum_follow_ups}

Assess whether the complete line of questioning provides enough
information about:

- The candidate's individual contribution
- The specific actions taken by the candidate
- Any challenge, difficulty or constraint
- The result or outcome
- Measurable evidence where reasonably available
- Evidence of skills relevant to the target role
- What the candidate learnt or would improve
- The connection between the example and the target role

Do not ask a follow-up merely because more detail could theoretically
be provided.

Ask a follow-up only when one important unresolved gap prevents the
answer from being reasonably assessed.

A line does not need to cover every possible assessment category.
Stop the line when the original question has been answered with enough
specific evidence.

Do not continue asking questions merely to obtain every possible detail.
Prefer completing the line over asking a weak, repetitive or marginal
follow-up.

The follow-up question must:

- Target only the single most important missing detail
- Ask one thing only
- Be concise and natural
- Usually contain no more than 20 words
- Avoid joining multiple requests with "and"
- Avoid repeating any earlier question
- Take account of all previous answers in this line of questioning
- Not ask for information the candidate has already provided
- Relate directly to the original question
- Not provide feedback or suggest the answer

If {maximum_follow_ups} follow-up questions have already been asked,
you must not generate another follow-up.

The missing_information list must contain no more than three items.
Only include the most important unresolved gaps.
Do not list every assessment category.

Return valid JSON only in exactly this structure:

{{
    "ask_follow_up": true,
    "follow_up_question": "What was your individual contribution?",
    "missing_information": [
        "individual contribution",
        "measurable result"
    ],
    "reason": "The candidate described the team but did not explain their own actions.",
    "line_complete": false
}}

When no follow-up is needed, return:

{{
    "ask_follow_up": false,
    "follow_up_question": null,
    "missing_information": [],
    "reason": "The answer contains enough information to assess the candidate.",
    "line_complete": true
}}

Do not include Markdown.
Do not include code fences.
Do not include any text before or after the JSON.
""".strip()