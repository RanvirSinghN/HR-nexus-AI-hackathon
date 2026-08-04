import streamlit as st

st.title("Job Support Assistant")

st.write(
    "This tool helps people understand job adverts "
    "and prepare stronger applications."
)

job_description = st.text_area(
    "Paste a job description",
    height=200,
)

candidate_experience = st.text_area(
    "Describe your experience",
    height=200,
)

if st.button("Analyse job"):
    if not job_description.strip():
        st.warning("Please paste a job description.")

    elif not candidate_experience.strip():
        st.warning("Please describe your experience.")

    else:
        st.success("Your application is ready to be analysed.")

        st.subheader("Job description")
        st.write(job_description)

        st.subheader("Your experience")
        st.write(candidate_experience)