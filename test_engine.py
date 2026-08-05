from interview_engine import generate_questions


sample_cv = """
Candidate has experience using Python for data analysis, statistical
modelling and visualisation.

They completed an independent research project involving large datasets
and presented technical findings to different audiences.

They have also worked in teams on technical projects.
"""

sample_job_description = """
Example Organisation is recruiting for a Graduate Data Analyst.

The role requires Python, data analysis, problem solving, teamwork and
the ability to explain technical findings clearly.

The successful candidate will analyse datasets, create reports and work
with technical and non-technical colleagues.
"""

questions = generate_questions(
    cv_text=sample_cv,
    job_description=sample_job_description,
    company="Example Organisation",
    role="Graduate Data Analyst",
    interview_type="Mixed",
    number_of_questions=5,
)

for question in questions:
    print()
    print(f"Question {question['id']}: {question['question']}")
    print(f"Category: {question['category']}")
    print(f"Reason: {question['reason']}")