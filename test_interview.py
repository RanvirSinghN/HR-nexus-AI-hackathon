"""
Test the full pipeline against Person 1's real interview_output.json.
    python3 test_interview.py
"""

import json
from interview_report import process_interview

payload = json.load(open("interview_output.json"))
result = process_interview(payload)

print("=" * 55)
print("PER-RESPONSE SCORES")
print("=" * 55)
for r in result["per_response"]:
    tag = r["question_type"]
    print(f"[line {r['line_id']} {tag:9}] {r['overall_score']}/10  "
          f"(rel {r['scores']['relevance']}, ev {r['scores']['evidence']}, "
          f"str {r['scores']['structure']}, role {r['scores']['role_alignment']})")
    print(f"    Q: {r['question'][:70]}")
    print(f"    A: {r['answer'][:70]}")
    if r["missing_information"]:
        print(f"    missing: {r['missing_information']}")
    print()

rep = result["final_report"]
print("=" * 55)
print("FINAL REPORT")
print("=" * 55)
print(f"Overall score:     {rep['overall_score']}/10")
print(f"Category averages: {rep['category_averages']}")
print(f"Strongest line:    {rep['strongest_line']}")
print(f"Weakest line:      {rep['weakest_line']}")
print()
print("Recurring strengths:", rep["recurring_strengths"])
print("Recurring weaknesses:", rep["recurring_weaknesses"])
print()
print("Priority improvements:")
for p in rep["priority_improvements"]:
    print("  -", p)
print()
print("Readiness:", rep["readiness_assessment"])
print()
print("Next steps:", rep["next_steps"])
print()
print("Improved examples:")
for ex in rep["improved_answer_examples"]:
    print("  Q:", ex["question"])
    print("  A:", ex["improved_answer"])
    print()
print("Disclaimer:", rep["human_next_step"])
