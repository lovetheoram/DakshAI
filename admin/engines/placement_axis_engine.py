# from dataclasses import dataclass


# SCENARIOS = [
#     "interview",
#     "production",
#     "debugging",
#     "system_design"
# ]

# REASONING = [
#     "edge_case",
#     "tradeoff",
#     "dry_run",
#     "output_prediction"
# ]

# TRAPS = [
#     "common_misconception",
#     "partial_truth",
#     "implementation_detail",
#     "terminology_confusion"
# ]

# DIFFICULTY = [
#     "easy",
#     "medium"
# ]


# @dataclass
# class PlacementState:
#     total_generated: int = 0


# class PlacementAxisEngine:

#     def __init__(self, state):
#         self.state = state

#     def generate_batch(
#         self,
#         batch_size=20
#     ):

#         rows = []

#         for i in range(batch_size):

#             idx = self.state.total_generated + i

#             scenario = SCENARIOS[
#                 idx % len(SCENARIOS)
#             ]

#             reasoning = REASONING[
#                 (idx * 3) % len(REASONING)
#             ]

#             trap = TRAPS[
#                 (idx * 5) % len(TRAPS)
#             ]

#             difficulty = DIFFICULTY[
#                 idx % len(DIFFICULTY)
#             ]

#             rows.append({
#                 "axis_signature":
#                     f"{scenario} | "
#                     f"{reasoning} | "
#                     f"{trap} | "
#                     f"{difficulty}"
#             })

#         self.state.total_generated += batch_size

#         return rows


"""
Placement Prompt Module

Designed for:

* Core CS
* DSA
* Aptitude
* AI Engineering

Focus:

Beginner → Interview Ready

This module owns:

1. Meta generation
2. Question prompt generation
3. PlacementAxisEngine integration
   """

import json

from django.db import transaction

from quiz.models import Question

from engines.placement_axis_engine import (
PlacementAxisEngine,
PlacementState
)

# ==========================================================

# KNOWLEDGE MAP PROMPT

# ==========================================================

FORMULA_PROMPT = """
You are a Senior Software Engineer,
Technical Interviewer,
Hiring Manager,
Assessment Designer.

Generate a COMPLETE interview-focused knowledge map.

Output STRICT JSON.

No markdown.
No commentary.
No explanations.

SCHEMA:

{
"meta": {
"concept": "",
"domain": "",
"difficulty": ""
},

"core_facts": [],

"decision_rules": [],

"tradeoffs": [],

"edge_cases": [],

"interview_traps": [],

"scenarios": [],

"related_concepts": []
}

RULES

1. Cover everything required for campus placements.

2. core_facts:
   Fundamental truths a candidate must know.

3. decision_rules:
   Rules used to eliminate options.

4. tradeoffs:
   Performance, scalability,
   memory, latency,
   accuracy tradeoffs.

5. edge_cases:
   Interview edge cases.

6. interview_traps:
   Common mistakes made by candidates.

7. scenarios:
   Real-world situations.

8. related_concepts:
   Concepts frequently asked together.

9. Keep facts concise.

10. No paragraphs.

11. No MCQs.

12. No code solutions.

13. No markdown.

DOMAIN RULES

Coding & DSA:

* Complexity
* Data structure behavior
* Algorithm selection

Core CS:

* OS
* DBMS
* Networks
* OOP
* System Design

Aptitude:

* Time & Work
* Probability
* Speed Distance
* Logical Reasoning

AI Engineering:

* ML
* LLM
* RAG
* Vector DB
* Prompt Engineering

Return valid JSON only.
"""

def get_formula_prompt(
concept_name,
description,
chapter
):
return FORMULA_PROMPT + f"""

CONCEPT:
{concept_name}

DESCRIPTION:
{description}

CHAPTER:
{chapter}

"""

# ==========================================================

# QUESTION PROMPT

# ==========================================================

def get_question_prompt(
concept_data,
concept,
question_ids,
axis_text
):

```
id_text = "\n".join([
    f"{i+1}. {qid}"
    for i, qid in enumerate(question_ids)
])

return f"""
```

You are generating EXACTLY 20 placement-grade questions.

CONCEPT DATA

{json.dumps(concept_data, ensure_ascii=False)}

QUESTION IDS

{id_text}

AXIS COMBINATIONS

{axis_text}

QUESTION DISTRIBUTION

4 Core Fact Questions

3 Concept Understanding Questions

3 Scenario Questions

3 Tradeoff Questions

3 Interview Trap Questions

2 Complexity Questions

2 Bug Finding Questions

RULES

1. Questions must test understanding.

2. Avoid pure memorization.

3. Focus on reasoning.

4. Focus on interview patterns.

5. One correct answer.

6. Exactly four options.

7. Do not repeat templates.

8. Difficulty should gradually increase.

9. Questions should teach concepts.

10. Questions must be solvable within
    15-45 seconds.

11. No trick wording.

12. Use clean Unicode.

13. No LaTeX.

14. No markdown.

OUTPUT FORMAT

[
{{
"question_id": "",
"question_title": "",
"concept": "{concept.name}",
"question": "",
"options": {{
"A": "",
"B": "",
"C": "",
"D": ""
}},
"answer": "",
"sub_questions": []
}}
]

Return JSON array only.
"""

# ==========================================================

# SINGLE QUESTION PROMPT

# ==========================================================

def get_single_question_prompt(concept):



return f"""
```

You are a Technical Placement Assessment API.

Generate EXACTLY ONE question.

Output ONLY valid JSON.

FORMAT

{{
"header": "",
"question_title": "",
"question": "",
"options": {{
"A":"",
"B":"",
"C":"",
"D":""
}},
"answer": "",
"explanation": "",

"sub_questions": [
{{
"type": "comfort",
"question": "",
"options": {{
"A":"",
"B":"",
"C":"",
"D":""
}},
"answer": ""
}},
{{
"type": "grounding",
"question": "",
"options": {{
"A":"",
"B":"",
"C":"",
"D":""
}},
"answer": ""
}},
{{
"type": "precursor",
"question": "",
"options": {{
"A":"",
"B":"",
"C":"",
"D":""
}},
"answer": ""
}}
]
}}

RULES

* Interview grade question
* One concept only
* One correct option
* Focus on understanding
* No LaTeX
* No markdown

CONCEPT:
{concept.name}

DESCRIPTION:
{concept.description or "N/A"}
"""

# ==========================================================

# BUILD QUESTION PROMPT

# ==========================================================

def build_question_prompt(
concept_data,
concept
):

```
with transaction.atomic():

    existing_count = (
        Question.objects
        .select_for_update()
        .filter(concept=concept)
        .count()
    )

    batch_size = 20

    question_ids = [
        f"{concept.name.upper()}-{existing_count+i+1}"
        for i in range(batch_size)
    ]

state = PlacementState(
    total_generated=existing_count
)

engine = PlacementAxisEngine(
    state=state
)

axis_batch = engine.generate_batch(
    batch_size=batch_size
)

axis_text = "\n".join([
    f"{i+1}. {item['axis_signature']}"
    for i, item in enumerate(axis_batch)
])

return get_question_prompt(
    concept_data=concept_data,
    concept=concept,
    question_ids=question_ids,
    axis_text=axis_text
)


