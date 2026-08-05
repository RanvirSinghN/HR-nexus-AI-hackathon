"""End-to-end Streamlit interface for the interview practice coach."""

import json
from pathlib import Path

import streamlit as st

from inputhandle import (
    CVProcessingError,
    build_interview_payload,
    payload_to_json,
    save_interview_json,
)
from interview_engine import (
    InterviewEngineError,
    build_interview_output,
    create_interview_session,
    generate_questions,
    get_current_line,
    process_candidate_answer,
    skip_current_question,
)
from interview_report import evaluate_response, process_interview


APP_DIR = Path(__file__).resolve().parent
SAVE_DIR = APP_DIR / "saved_inputs"
INTERVIEW_TYPES = ["Mixed", "Behavioural", "Competency", "Technical"]
INTERVIEW_STATE_KEYS = (
    "interview_session",
    "active_question_type",
    "active_question_text",
    "latest_response_key",
    "feedback_by_response",
    "final_report",
    "pending_action",
    "answer_error",
    "ended_early",
)


def initialise_state() -> None:
    st.session_state.setdefault("flow", "intake")
    st.session_state.setdefault("feedback_by_response", {})
    st.session_state.setdefault("pending_action", None)
    st.session_state.setdefault("ended_early", False)


def clear_interview_state(keep_inputs: bool = True) -> None:
    for key in INTERVIEW_STATE_KEYS:
        st.session_state.pop(key, None)
    if not keep_inputs:
        st.session_state.pop("interview_inputs", None)
        st.session_state.pop("interview_json", None)
        st.session_state["flow"] = "intake"
    else:
        st.session_state["flow"] = "ready"
    st.session_state["feedback_by_response"] = {}


def render_feedback(feedback: dict) -> None:
    score = feedback.get("overall_score", 0)
    st.metric("Answer score", f"{score:.1f}/10")

    strengths = feedback.get("strengths", [])
    improvements = feedback.get("improvements", [])
    missing = feedback.get("missing_information", [])

    if strengths:
        st.markdown("**What worked**")
        for item in strengths:
            st.write(f"- {item}")
    if improvements:
        st.markdown("**Improve next time**")
        for item in improvements:
            st.write(f"- {item}")
    if missing:
        st.markdown("**Missing evidence**")
        for item in missing:
            st.write(f"- {item}")


def render_history(session: dict) -> None:
    responses_exist = any(line["responses"] for line in session["lines_of_questioning"])
    if not responses_exist:
        return

    with st.expander("Interview transcript", expanded=False):
        for line in session["lines_of_questioning"]:
            for response_index, response in enumerate(line["responses"]):
                label = "Follow-up" if response["question_type"] == "follow_up" else line["category"]
                st.markdown(f"**{label}: {response['question']}**")
                st.write(response["answer"] or "_Skipped_")

                feedback_key = f"{line['line_id']}:{response_index}"
                feedback = st.session_state["feedback_by_response"].get(feedback_key)
                if feedback:
                    with st.expander("View feedback", expanded=False):
                        render_feedback(feedback)
                st.divider()


def render_latest_feedback_action(session: dict) -> None:
    response_key = st.session_state.get("latest_response_key")
    if not response_key:
        return

    feedback_by_response = st.session_state["feedback_by_response"]
    if response_key in feedback_by_response:
        with st.expander("Feedback on your latest answer", expanded=True):
            render_feedback(feedback_by_response[response_key])
        return

    line_id_text, response_index_text = response_key.split(":")
    line_id = int(line_id_text)
    response_index = int(response_index_text)
    line = next(item for item in session["lines_of_questioning"] if item["line_id"] == line_id)
    response = line["responses"][response_index]
    context = session["candidate_context"]

    if st.button("Get feedback on latest answer", use_container_width=True):
        with st.spinner("Reviewing your answer..."):
            feedback = evaluate_response(
                question=response["question"],
                answer=response["answer"],
                cv_text=context["cv_text"],
                job_description=context["job_description"],
                role=context["role"],
                company=context["company"],
                category=line["category"],
            )
        feedback_by_response[response_key] = feedback
        st.rerun()


def start_interview(payload: dict) -> None:
    preferences = payload["interview_preferences"]
    job = payload["job"]
    questions = generate_questions(
        cv_text=payload["cv_text"],
        job_description=job["description"],
        company=job["company"],
        role=job["title"],
        interview_type=preferences["interview_type"],
        number_of_questions=preferences["number_of_questions"],
    )
    session = create_interview_session(
        questions=questions,
        cv_text=payload["cv_text"],
        job_description=job["description"],
        company=job["company"],
        role=job["title"],
        interview_type=preferences["interview_type"],
    )
    st.session_state["interview_session"] = session
    st.session_state["active_question_type"] = "main"
    st.session_state["active_question_text"] = questions[0]["question"]
    st.session_state["feedback_by_response"] = {}
    st.session_state["latest_response_key"] = None
    st.session_state["final_report"] = None
    st.session_state["pending_action"] = None
    st.session_state["ended_early"] = False
    st.session_state["flow"] = "interview"


def apply_interview_action(result: dict) -> None:
    if result["action"] == "ask_follow_up":
        st.session_state["active_question_type"] = "follow_up"
        st.session_state["active_question_text"] = result["follow_up_question"]
    elif result["action"] == "ask_main_question":
        st.session_state["active_question_type"] = "main"
        st.session_state["active_question_text"] = result["next_question"]["question"]
    else:
        st.session_state["flow"] = "complete"


def submit_answer(answer: str) -> None:
    session = st.session_state["interview_session"]
    current_line = get_current_line(session)
    if current_line is None:
        st.session_state["flow"] = "complete"
        return

    response_index = len(current_line["responses"])
    response_key = f"{current_line['line_id']}:{response_index}"
    question_type = st.session_state["active_question_type"]
    follow_up_question = (
        st.session_state["active_question_text"]
        if question_type == "follow_up"
        else None
    )

    result = process_candidate_answer(
        session=session,
        answer=answer,
        question_type=question_type,
        follow_up_question=follow_up_question,
    )
    st.session_state["latest_response_key"] = response_key
    apply_interview_action(result)


def skip_active_question() -> None:
    session = st.session_state["interview_session"]
    current_line = get_current_line(session)
    if current_line is None:
        st.session_state["flow"] = "complete"
        return

    response_index = len(current_line["responses"])
    response_key = f"{current_line['line_id']}:{response_index}"
    question_type = st.session_state["active_question_type"]
    follow_up_question = (
        st.session_state["active_question_text"]
        if question_type == "follow_up"
        else None
    )
    result = skip_current_question(
        session=session,
        question_type=question_type,
        follow_up_question=follow_up_question,
    )
    st.session_state["latest_response_key"] = response_key
    apply_interview_action(result)


def queue_answer(answer_key: str) -> None:
    answer = st.session_state.get(answer_key, "").strip()
    if not answer:
        st.session_state["answer_error"] = "Please enter an answer or choose Skip question."
        return
    st.session_state["answer_error"] = None
    st.session_state["pending_action"] = {
        "type": "answer",
        "answer": answer,
    }


def queue_skip() -> None:
    st.session_state["answer_error"] = None
    st.session_state["pending_action"] = {"type": "skip"}


def end_interview_early() -> None:
    session = st.session_state["interview_session"]
    session["interview_complete"] = True
    st.session_state["pending_action"] = None
    st.session_state["ended_early"] = True
    st.session_state["final_report"] = None
    st.session_state["flow"] = "complete"


def render_intake() -> None:
    st.subheader("Set up your interview")
    with st.form("interview_intake_form"):
        uploaded_cv = st.file_uploader(
            "Upload your CV",
            type=["pdf"],
            help="Use a text-based PDF so the content can be extracted.",
        )
        left, right = st.columns(2)
        with left:
            job_title = st.text_input("Job title", placeholder="Graduate Software Engineer")
            interview_type = st.selectbox("Interview style", INTERVIEW_TYPES)
        with right:
            company = st.text_input("Company", placeholder="Example Ltd")
            number_of_questions = st.number_input(
                "Main questions",
                min_value=1,
                max_value=19,
                value=4,
                step=1,
            )
        job_description = st.text_area(
            "Job description",
            placeholder="Paste the full job description here...",
            height=220,
        )
        privacy_confirmation = st.checkbox(
            "I understand that candidate identity should remain anonymous in AI processing."
        )
        submitted = st.form_submit_button("Prepare interview", use_container_width=True)

    if not submitted:
        return

    missing_fields = []
    if uploaded_cv is None:
        missing_fields.append("CV PDF")
    if not job_title.strip():
        missing_fields.append("job title")
    if not company.strip():
        missing_fields.append("company")
    if not job_description.strip():
        missing_fields.append("job description")
    if not privacy_confirmation:
        missing_fields.append("anonymity confirmation")

    if missing_fields:
        st.error("Please complete: " + ", ".join(missing_fields) + ".")
        return

    try:
        payload = build_interview_payload(
            cv_pdf=uploaded_cv,
            job_title=job_title,
            company=company,
            job_description=job_description,
            interview_type=interview_type,
            number_of_questions=number_of_questions,
        )
        json_output = payload_to_json(payload)
        save_interview_json(payload, SAVE_DIR)
        st.session_state["interview_inputs"] = payload
        st.session_state["interview_json"] = json_output
        clear_interview_state(keep_inputs=True)
        st.rerun()
    except (CVProcessingError, ValueError) as exc:
        st.error(str(exc))


def render_ready() -> None:
    payload = st.session_state["interview_inputs"]
    job = payload["job"]
    preferences = payload["interview_preferences"]

    st.success("Your interview details are ready.")
    st.subheader(f"{job['title']} at {job['company']}")
    left, right = st.columns(2)
    left.metric("Interview style", preferences["interview_type"])
    right.metric("Main questions", preferences["number_of_questions"])

    with st.expander("Review anonymised input", expanded=False):
        st.json(payload)

    st.download_button(
        "Download input JSON",
        data=st.session_state["interview_json"],
        file_name="interview_payload.json",
        mime="application/json",
        use_container_width=True,
    )

    if st.button("Start interview", type="primary", use_container_width=True):
        try:
            with st.spinner("Creating your tailored interview..."):
                start_interview(payload)
            st.rerun()
        except (InterviewEngineError, ValueError) as exc:
            st.error(str(exc))


def render_interview() -> None:
    session = st.session_state["interview_session"]
    current_line = get_current_line(session)
    completed = session["current_question_index"]
    total = len(session["questions"])

    progress_column, end_column = st.columns([3, 1])
    progress_column.progress(
        completed / total,
        text=f"Main question {min(completed + 1, total)} of {total}",
    )
    if end_column.button("End interview", use_container_width=True):
        end_interview_early()
        st.rerun()

    render_history(session)
    render_latest_feedback_action(session)

    pending_action = st.session_state.get("pending_action")
    if pending_action:
        message = (
            "Answer submitted. Preparing the next question..."
            if pending_action["type"] == "answer"
            else "Skipping this question..."
        )
        st.info(message)
        try:
            with st.spinner("Updating your interview..."):
                if pending_action["type"] == "answer":
                    submit_answer(pending_action["answer"])
                else:
                    skip_active_question()
            st.session_state["pending_action"] = None
            st.rerun()
        except (InterviewEngineError, ValueError) as exc:
            st.session_state["pending_action"] = None
            st.session_state["answer_error"] = str(exc)
            st.rerun()

    if current_line is None:
        st.session_state["flow"] = "complete"
        st.rerun()

    question_kind = st.session_state["active_question_type"]
    label = "Follow-up" if question_kind == "follow_up" else current_line["category"]
    st.caption(label)
    st.subheader(st.session_state["active_question_text"])

    response_count = sum(len(line["responses"]) for line in session["lines_of_questioning"])
    answer_key = f"answer_{response_count}"
    answer_error = st.session_state.pop("answer_error", None)
    if answer_error:
        st.error(answer_error)

    with st.form(f"answer_form_{response_count}", clear_on_submit=True):
        st.text_area(
            "Your answer",
            height=180,
            placeholder="Type your answer here...",
            key=answer_key,
        )
        submit_column, skip_column = st.columns(2)
        submit_column.form_submit_button(
            "Submit answer",
            type="primary",
            use_container_width=True,
            on_click=queue_answer,
            args=(answer_key,),
        )
        skip_column.form_submit_button(
            "Skip question",
            use_container_width=True,
            on_click=queue_skip,
        )


def render_report(report: dict) -> None:
    final = report["final_report"]
    st.subheader("Final feedback report")
    st.metric("Overall interview score", f"{final['overall_score']:.1f}/10")

    columns = st.columns(4)
    labels = {
        "relevance": "Relevance",
        "evidence": "Evidence",
        "structure": "Structure",
        "role_alignment": "Role alignment",
    }
    for column, (key, label) in zip(columns, labels.items()):
        column.metric(label, f"{final['category_averages'].get(key, 0):.1f}")

    st.markdown("**Readiness assessment**")
    st.write(final["readiness_assessment"])

    for heading, key in (
        ("Priority improvements", "priority_improvements"),
        ("Recurring strengths", "recurring_strengths"),
        ("Next steps", "next_steps"),
    ):
        items = final.get(key, [])
        if items:
            st.markdown(f"**{heading}**")
            for item in items:
                st.write(f"- {item}")

    examples = final.get("improved_answer_examples", [])
    if examples:
        with st.expander("Improved answer examples", expanded=False):
            for example in examples:
                st.markdown(f"**{example['question']}**")
                st.write(example["improved_answer"])

    st.info(final["human_next_step"])


def render_complete() -> None:
    session = st.session_state["interview_session"]
    if st.session_state.get("ended_early"):
        st.warning("Interview ended early. Your report will cover the responses submitted so far.")
    else:
        st.success("Interview complete.")
    render_history(session)
    render_latest_feedback_action(session)

    report = st.session_state.get("final_report")
    if report is None:
        if st.button("Generate final feedback report", type="primary", use_container_width=True):
            try:
                with st.spinner("Scoring your interview and preparing the report..."):
                    report = process_interview(build_interview_output(session))
                st.session_state["final_report"] = report
                st.rerun()
            except Exception as exc:
                st.error(f"The final report could not be generated: {exc}")
        return

    render_report(report)
    st.download_button(
        "Download final report JSON",
        data=json.dumps(report, indent=2),
        file_name="interview_report.json",
        mime="application/json",
        use_container_width=True,
    )


st.set_page_config(
    page_title="AI Interview Practice Coach",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed",
)
initialise_state()

with st.sidebar:
    st.header("Responsible AI")
    st.info(
        "Keep your interview anonymous. Remove names, addresses, photos, dates of birth, "
        "and other identifying details where possible."
    )
    st.write("AI feedback is practice guidance, not a hiring decision.")
    if st.session_state["flow"] != "intake":
        if st.button("Start over", use_container_width=True):
            clear_interview_state(keep_inputs=False)
            st.rerun()

st.title("AI Interview Practice Coach")
st.caption("A tailored, adaptive mock interview based on your CV and target role.")

flow = st.session_state["flow"]
if flow == "intake":
    render_intake()
elif flow == "ready":
    render_ready()
elif flow == "interview":
    render_interview()
else:
    render_complete()
