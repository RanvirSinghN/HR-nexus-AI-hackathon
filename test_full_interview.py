import json

from interview_engine import (
    build_interview_output,
    create_interview_session,
    get_current_line,
    process_candidate_answer,
)


sample_cv = """
The candidate has experience using Python for data analysis,
technical research, teamwork and presenting findings clearly.

They completed an independent project involving a large dataset
and have contributed to collaborative technical assignments.
"""

sample_job_description = """
Example Organisation is recruiting for a Graduate Analyst.

The role requires analytical thinking, teamwork, communication,
problem solving and experience working with data.
"""

sample_questions = [
    {
        "id": 1,
        "category": "Teamwork",
        "question": (
            "Tell me about a time you worked with others to solve "
            "a difficult problem."
        ),
        "reason": (
            "The role requires collaboration and problem solving."
        ),
    },
    {
        "id": 2,
        "category": "Problem solving",
        "question": (
            "Describe a time when your original approach did not work."
        ),
        "reason": (
            "The role requires adaptability and analytical judgement."
        ),
    },
]


session = create_interview_session(
    questions=sample_questions,
    cv_text=sample_cv,
    job_description=sample_job_description,
    company="Example Organisation",
    role="Graduate Analyst",
    interview_type="Competency",
)


print("\nINTERVIEW STARTED")
print(f"Session ID: {session['session_id']}")


while not session["interview_complete"]:
    current_line = get_current_line(session)

    if current_line is None:
        break

    main_question = current_line["main_question"]["question"]

    print("\nMAIN QUESTION")
    print(main_question)

    if current_line["line_id"] == 1:
        main_answer = (
            "I worked in a university team project. We divided the "
            "work and completed the project successfully."
        )
    else:
        main_answer = (
            "During a technical project, my original method produced "
            "incorrect results. I reviewed the code, tested smaller "
            "examples and found an error in my assumptions. I corrected "
            "the approach and successfully completed the analysis."
        )

    print("\nANSWER")
    print(main_answer)

    result = process_candidate_answer(
        session=session,
        answer=main_answer,
        question_type="main",
    )

    while result["action"] == "ask_follow_up":
        follow_up_question = result["follow_up_question"]

        print("\nFOLLOW-UP QUESTION")
        print(follow_up_question)

        follow_up_count = result["follow_up_count"]

        if follow_up_count == 1:
            follow_up_answer = (
                "I cleaned the dataset, wrote the Python analysis code "
                "and explained the results to the rest of the team."
            )
        elif follow_up_count == 2:
            follow_up_answer = (
                "The main challenge was inconsistent data formatting, "
                "so I created a repeatable cleaning process."
            )
        else:
            follow_up_answer = (
                "We submitted the project before the deadline and "
                "received strong feedback on the accuracy of the analysis."
            )

        print("\nFOLLOW-UP ANSWER")
        print(follow_up_answer)

        result = process_candidate_answer(
            session=session,
            answer=follow_up_answer,
            question_type="follow_up",
            follow_up_question=follow_up_question,
        )

    print("\nENGINE ACTION")
    print(result["action"])


final_output = build_interview_output(session)

with open(
    "completed_interview_output.json",
    "w",
    encoding="utf-8",
) as output_file:
    json.dump(
        final_output,
        output_file,
        indent=2,
        ensure_ascii=False,
    )


print("\nINTERVIEW COMPLETE")
print(json.dumps(final_output["summary"], indent=2))
print("\nSaved to completed_interview_output.json")