from pathlib import Path

import streamlit as st

from inputhandle import (
    CVProcessingError,
    build_interview_payload,
    payload_to_json,
    save_interview_json,
)


APP_DIR = Path(__file__).resolve().parent
SAVE_DIR = APP_DIR / "saved_inputs"


st.set_page_config(
    page_title="AI Interview Practice Coach",
    page_icon="🎯",
    layout="centered",
)

st.title("AI Interview Practice Coach")
st.write("Add your CV and the role details to prepare an interview practice session.")

with st.sidebar:
    st.header("Responsible AI")
    st.info(
        "Keep your interview anonymous. Where possible, remove your name, address, "
        "photo, date of birth, and other identifying details from your CV."
    )
    st.markdown(
        """
        - Feedback should assess role-relevant skills and answers only.
        - Protected characteristics must not influence questions or feedback.
        - AI feedback is guidance, not a hiring decision.
        - Uploaded data should only be retained for as long as necessary.
        """
    )

with st.form("interview_intake_form"):
    uploaded_cv = st.file_uploader(
        "Upload your CV (PDF)",
        type=["pdf"],
        help="Drag and drop a PDF here, or browse files on your computer.",
    )
    job_title = st.text_input(
        "Job title",
        placeholder="e.g. Graduate Software Engineer",
    )
    company = st.text_input(
        "Company",
        placeholder="e.g. Example Ltd",
    )
    job_description = st.text_area(
        "Job description",
        placeholder="Paste the full job description here...",
        height=220,
    )
    privacy_confirmation = st.checkbox(
        "I understand that candidate identity should remain anonymous in AI processing."
    )
    submitted = st.form_submit_button(
        "Save interview details",
        use_container_width=True,
    )

if submitted:
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
    else:
        try:
            interview_payload = build_interview_payload(
                cv_pdf=uploaded_cv,
                job_title=job_title,
                company=company,
                job_description=job_description,
            )
            json_output = payload_to_json(interview_payload)
            json_path = save_interview_json(interview_payload, SAVE_DIR)

            st.session_state["interview_inputs"] = interview_payload
            st.session_state["interview_json"] = json_output
            st.success(f"Anonymous interview payload saved to {json_path.name}.")

            with st.expander("View API payload"):
                st.json(interview_payload)

            st.download_button(
                "Download JSON payload",
                data=json_output,
                file_name="interview_payload.json",
                mime="application/json",
                use_container_width=True,
            )
        except CVProcessingError as exc:
            st.error(str(exc))
