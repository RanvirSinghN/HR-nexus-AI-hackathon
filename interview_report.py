"""
PERSON 3 — Score answers + build final report
AI Interview Practice Coach (hackathon build)

Person 1 sends interview_output.json: raw questions + answers, NO scores.
This module:
  1. Scores every answer with the LLM (relevance / evidence / structure / role_alignment)
  2. Computes all aggregate NUMBERS in plain Python (never trusts the LLM for maths)
  3. Uses the LLM only for the PROSE (recurring themes, priorities, readiness, improved answers)
  4. Returns per-answer feedback + the full final report

SETUP:  pip install openai ; export OPENAI_API_KEY="..."
USAGE:  from interview_report import process_interview
        result = process_interview(person1_json)
        # result = {"per_response": [...], "final_report": {...}}
"""

import json
import re
from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o-mini"

CATEGORIES = ["relevance", "evidence", "structure", "role_alignment"]
WEIGHTS = {"relevance": 0.30, "evidence": 0.30, "structure": 0.20, "role_alignment": 0.20}

DISCLAIMER = ("This is a practice tool, not careers, employment or legal advice. "
              "For personalised guidance, speak to a careers advisor, mentor, "
              "or the National Careers Service.")


def _parse_json(raw: str):
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _round1(x):
    return round(x, 1)


# ---------------------------------------------------------------------------
# STEP 1 — score a single answer
# ---------------------------------------------------------------------------

EVAL_SYSTEM_PROMPT = """You are a rigorous but supportive interview answer evaluator inside a practice tool. Respond in JSON.

Score ONE candidate answer against the question asked, the CV and the job description.

CATEGORIES (each 1-10, integers):
- relevance: does the answer actually address the QUESTION ASKED? If the answer is about something else, relevance is 1-2 even if the content is good.
- evidence: specificity - concrete examples, numbers, named tools, measurable results
- structure: clarity and organisation (STAR: Situation, Task, Action, Result)
- role_alignment: connection to the skills in the job description

CALIBRATION:
- 1-3: off-topic, vague, or one line with no example
- 4-5: on-topic but generic; no measurable outcome
- 6-7: relevant real example but missing one key element (no result, unclear contribution)
- 8-9: relevant, specific, structured, measurable result, linked to the role
- 10: exceptional; rare
A weak answer MUST score low; a strong one MUST score high. Do not cluster at 6-7.

IMPORTANT: if the answer does not match the question (e.g. answers a different question), score relevance 1-2 and note the mismatch in missing_information.

EDGE CASES: empty/whitespace -> all 1, note "no answer provided". One or two words -> 1-2.

overall_score = relevance*0.30 + evidence*0.30 + structure*0.20 + role_alignment*0.20, rounded to 1 dp.

FEEDBACK: specific, tied to THIS answer + CV + job description. Never "be more confident" unless the wording justifies it.

Respond with ONLY this JSON:
{
  "scores": {"relevance": int, "evidence": int, "structure": int, "role_alignment": int},
  "overall_score": float,
  "strengths": [str, ...],
  "improvements": [str, ...],
  "missing_information": [str, ...]
}"""


def _score_answer(question, answer, cv_text, job_description, role, company, category):
    if answer is None or str(answer).strip() == "":
        return {
            "scores": {c: 1 for c in CATEGORIES},
            "overall_score": 1.0,
            "strengths": [],
            "improvements": ["No answer was provided."],
            "missing_information": ["no answer provided"],
        }
    user_prompt = f"""ROLE: {role} at {company}
CATEGORY: {category}

JOB DESCRIPTION:
{job_description}

CANDIDATE CV:
{cv_text}

QUESTION:
{question}

ANSWER:
{answer}"""
    try:
        raw = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": EVAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        ).choices[0].message.content
        return _parse_json(raw)
    except Exception as e:
        return {
            "scores": {c: 0 for c in CATEGORIES},
            "overall_score": 0.0,
            "strengths": [],
            "improvements": ["This answer could not be evaluated automatically."],
            "missing_information": [f"evaluation error: {type(e).__name__}"],
        }


# ---------------------------------------------------------------------------
# STEP 2 — read Person 1's structure and score everything
# ---------------------------------------------------------------------------

def _score_all(payload: dict):
    ctx = payload.get("candidate_context", {})
    cv = ctx.get("cv_text", "")
    jd = ctx.get("job_description", "")
    company = ctx.get("company", "")
    role = ctx.get("role", "")

    scored = []
    for line in payload.get("lines_of_questioning", []):
        category = line.get("category", "General")
        for resp in line.get("responses", []):
            ev = _score_answer(
                resp.get("question", ""), resp.get("answer", ""),
                cv, jd, role, company, category,
            )
            scored.append({
                "line_id": line.get("line_id"),
                "category": category,
                "question_type": resp.get("question_type", "main"),
                "question": resp.get("question", ""),
                "answer": resp.get("answer", ""),
                "scores": {c: ev["scores"].get(c, 0) for c in CATEGORIES},
                "overall_score": ev.get("overall_score", 0),
                "strengths": ev.get("strengths", []),
                "improvements": ev.get("improvements", []),
                "missing_information": ev.get("missing_information", []),
            })
    return scored, {"cv": cv, "jd": jd, "company": company, "role": role}


# ---------------------------------------------------------------------------
# STEP 3 — compute aggregates in plain Python (no LLM)
# ---------------------------------------------------------------------------

def _compute_metrics(scored, payload):
    n = len(scored)
    if n == 0:
        return {"overall_score": 0.0, "category_averages": {c: 0.0 for c in CATEGORIES},
                "line_averages": [], "strongest_line": None, "weakest_line": None}

    cat_avgs = {c: _round1(sum(r["scores"][c] for r in scored) / n) for c in CATEGORIES}
    overall = _round1(sum(cat_avgs[c] * WEIGHTS[c] for c in CATEGORIES))

    line_scores = {}
    for line in payload.get("lines_of_questioning", []):
        lid = line.get("line_id")
        vals = [r["overall_score"] for r in scored if r["line_id"] == lid]
        if vals:
            line_scores[lid] = {
                "line_id": lid,
                "category": line.get("category", "General"),
                "average_score": _round1(sum(vals) / len(vals)),
            }

    strongest = max(line_scores.values(), key=lambda x: x["average_score"]) if line_scores else None
    weakest = min(line_scores.values(), key=lambda x: x["average_score"]) if line_scores else None

    return {
        "overall_score": overall,
        "category_averages": cat_avgs,
        "line_averages": list(line_scores.values()),
        "strongest_line": strongest,
        "weakest_line": weakest,
    }


# ---------------------------------------------------------------------------
# STEP 4 — LLM writes the prose only
# ---------------------------------------------------------------------------

PROSE_SYSTEM_PROMPT = """You are writing the qualitative sections of a practice-interview report. Respond in JSON.

You are given the CV, the job description, and every scored response (scores, strengths, improvements, missing info already identified). You do NOT calculate scores.

RULES:
- "Recurring" = appears in 2+ responses.
- priority_improvements: exactly 3, ordered by impact, specific.
- improved_answer_examples: rewrite the weakest 1-2 answers using ONLY facts in the candidate's answers or CV. Never invent experience.
- readiness_assessment: one honest, encouraging paragraph. Practice tool - do NOT predict pass/fail.
- Avoid generic advice like "be more confident" unless evidence supports it.

Respond with ONLY this JSON:
{
  "recurring_strengths": [str, ...],
  "recurring_weaknesses": [str, ...],
  "priority_improvements": [str, str, str],
  "readiness_assessment": str,
  "next_steps": [str, ...],
  "improved_answer_examples": [{"question": str, "improved_answer": str}]
}"""


def _write_prose(scored, ctx, metrics):
    user_prompt = f"""CANDIDATE CV:
{ctx['cv']}

JOB DESCRIPTION:
{ctx['jd']}

COMPUTED SCORES (use as-is, do not change):
overall: {metrics['overall_score']}
category_averages: {json.dumps(metrics['category_averages'])}
weakest line: {json.dumps(metrics.get('weakest_line'))}

ALL SCORED RESPONSES:
{json.dumps(scored, indent=2)}"""
    try:
        raw = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PROSE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        ).choices[0].message.content
        return _parse_json(raw)
    except Exception as e:
        return {
            "recurring_strengths": [], "recurring_weaknesses": [],
            "priority_improvements": [], "readiness_assessment": "Summary unavailable.",
            "next_steps": [], "improved_answer_examples": [],
            "error": f"{type(e).__name__}",
        }


# ---------------------------------------------------------------------------
# PUBLIC — one call Person 1 uses
# ---------------------------------------------------------------------------

def process_interview(payload: dict) -> dict:
    """
    Takes Person 1's interview_output.json (raw Q&As, no scores).
    Returns: {"per_response": [...], "final_report": {...}}
    """
    scored, ctx = _score_all(payload)
    metrics = _compute_metrics(scored, payload)
    prose = _write_prose(scored, ctx, metrics)

    final_report = {
        "overall_score": metrics["overall_score"],
        "category_averages": metrics["category_averages"],
        "line_averages": metrics["line_averages"],
        "strongest_line": metrics["strongest_line"],
        "weakest_line": metrics["weakest_line"],
        "recurring_strengths": prose.get("recurring_strengths", []),
        "recurring_weaknesses": prose.get("recurring_weaknesses", []),
        "priority_improvements": prose.get("priority_improvements", []),
        "readiness_assessment": prose.get("readiness_assessment", ""),
        "next_steps": prose.get("next_steps", []),
        "improved_answer_examples": prose.get("improved_answer_examples", []),
        "human_next_step": DISCLAIMER,
    }
    return {"per_response": scored, "final_report": final_report}
