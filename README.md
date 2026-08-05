# HR-nexus-AI-hackathon

# Project Context: AI Interview Practice Coach
_#PERSON 1#_
We are building an AI-powered interview practice coach for a hackathon.

The application allows a user to:

* Upload or paste their CV
* Upload or paste a job description
* Enter the company name, role title and interview type
* Receive tailored interview questions
* Answer questions one at a time
* Receive relevant follow-up questions
* Receive feedback after each line of questioning
* Receive a final overall interview performance report

My responsibility is the front end and input-handling section of the application.

I am responsible for:

* Building the Streamlit user interface
* Creating CV and job-description upload or paste fields
* Collecting the company name, role title and interview type
* Extracting text from uploaded PDF and Word files
* Displaying one interview question at a time
* Providing a text box for candidate responses
* Displaying follow-up questions
* Managing buttons, page flow and user navigation
* Managing Streamlit session state
* Displaying feedback and final report outputs created by the other team members

The front end should call functions created by the other team members rather than containing all AI logic directly.

Expected external functions may include:

```python
generate_questions(
    cv_text,
    job_description,
    company,
    role,
    interview_type
)

evaluate_response(
    question,
    response,
    cv_text,
    job_description,
    interview_history
)

generate_final_report(
    interview_history
)
```

The first version should use typed answers. Audio recording and transcription are stretch features and should only be added after the full typed-response flow works.

The application should prioritise simplicity, reliability and a clear demonstration flow over complex styling.


_#PERSON 2#_
# Project Context: AI Interview Practice Coach

We are building an AI-powered interview practice coach for a hackathon.

The application allows a user to:

* Upload or paste their CV
* Upload or paste a job description
* Enter the company name, role title and interview type
* Receive tailored interview questions
* Answer questions one at a time
* Receive relevant follow-up questions
* Receive feedback after each line of questioning
* Receive a final overall interview performance report

My responsibility is the interview engine and question-generation section of the application.

I am responsible for:

* Combining the candidate’s CV, job description, company, role and interview type
* Identifying the candidate’s most relevant experience
* Identifying the main skills and requirements in the job description
* Generating tailored primary interview questions
* Grouping questions into clear interview topics or lines of questioning
* Tracking the current question and follow-up count
* Generating relevant follow-up questions based on missing information
* Limiting follow-up questions to a maximum of three
* Deciding when a line of questioning is complete
* Moving the interview to the next primary question

The interview should feel adaptive rather than using a fixed list of questions.

Follow-up questions should be asked when an answer lacks important information such as:

* The candidate’s individual contribution
* Specific actions taken
* A challenge or difficulty
* A measurable result
* Evidence of a relevant skill
* Connection to the target role

The engine should return structured Python dictionaries or JSON rather than unstructured paragraphs.

An example question structure is:

```python
{
    "id": 1,
    "category": "Teamwork",
    "question": "Tell me about a time you worked effectively within a team.",
    "reason": "The job description emphasises cross-functional collaboration."
}
```

An example follow-up output is:

```python
{
    "ask_follow_up": True,
    "follow_up_question": "What was your individual contribution to the project?",
    "missing_information": [
        "individual contribution",
        "measurable result"
    ],
    "line_complete": False
}
```

The first working version should generate approximately four to six main questions. Reliability and clear structured output are more important than generating a large number of questions.

_#PERSON 3#_
# Project Context: AI Interview Practice Coach

We are building an AI-powered interview practice coach for a hackathon.

The application allows a user to:

* Upload or paste their CV
* Upload or paste a job description
* Enter the company name, role title and interview type
* Receive tailored interview questions
* Answer questions one at a time
* Receive relevant follow-up questions
* Receive feedback after each line of questioning
* Receive a final overall interview performance report

My responsibility is the answer-evaluation, feedback and final-report section of the application.

I am responsible for:

* Evaluating each candidate response
* Scoring responses using consistent categories
* Identifying strengths and weaknesses
* Identifying missing information
* Determining whether a follow-up question is needed
* Providing feedback after each completed line of questioning
* Generating suggested improvements
* Producing improved example answers where useful
* Combining all interview results into a final report
* Calculating overall and category-level scores

Each answer should be scored using categories such as:

* Relevance
* Evidence and specificity
* Structure and clarity
* Alignment with the role

A suggested weighting is:

```text
Relevance: 30%
Evidence and specificity: 30%
Structure and clarity: 20%
Role alignment: 20%
```

The evaluation should return structured Python dictionaries or JSON.

Example:

```python
{
    "scores": {
        "relevance": 8,
        "evidence": 6,
        "structure": 7,
        "role_alignment": 8
    },
    "overall_score": 7.3,
    "strengths": [
        "The answer directly addressed the question.",
        "The candidate explained the situation clearly."
    ],
    "improvements": [
        "Include a measurable result.",
        "Explain the candidate's individual contribution."
    ],
    "missing_information": [
        "measurable result",
        "individual contribution"
    ],
    "ask_follow_up": True,
    "suggested_follow_up_focus": "Ask about the candidate's individual contribution."
}
```

The final report should include:

* Overall interview score
* Average score for each category
* Strongest answers
* Weakest answers
* Recurring strengths
* Recurring weaknesses
* Three priority improvements
* Overall interview-readiness assessment
* Suggested next steps
* Improved answer examples

The feedback should be constructive, specific and linked to the candidate’s CV and target job description. Generic feedback such as “be more confident” should be avoided unless supported by clear evidence.

