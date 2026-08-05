from interview_engine import evaluate_follow_up_need


sample_cv = """
The candidate has experience using Python for data analysis and has
worked on collaborative technical projects.

They have presented results to technical and non-technical audiences.
"""

sample_job_description = """
Example Organisation is recruiting for a Graduate Analyst.

The role requires teamwork, problem solving, data analysis and clear
communication.
"""

main_question = """
Tell me about a time you worked with others to solve a difficult problem.
"""

candidate_answer = """
During a university project, I worked in a team of four people.
We divided the work between us and completed the project successfully.
"""

result = evaluate_follow_up_need(
    main_question=main_question,
    candidate_answer=candidate_answer,
    cv_text=sample_cv,
    job_description=sample_job_description,
    role="Graduate Analyst",
    interview_type="Competency",
    previous_follow_ups=[],
    follow_up_count=0,
    maximum_follow_ups=3,
)

print("\nFollow-up decision:")
print(f"Ask follow-up: {result['ask_follow_up']}")
print(f"Question: {result['follow_up_question']}")
print(f"Missing information: {result['missing_information']}")
print(f"Reason: {result['reason']}")
print(f"Line complete: {result['line_complete']}")