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
