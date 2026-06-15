"""
Placement Prep specific prompts — tailored for Technical Interviews, Coding, Core CS, Aptitude, and AI Engineering.

Functions:
    get_formula_prompt(concept_name, description, chapter) -> str
    get_question_prompt(concept_data, concept, question_ids, axis_text) -> str
    get_single_question_prompt(concept) -> str
"""

import json

# ═══════════════════════════════════════════════════════════
# FORMULA / KNOWLEDGE MAP PROMPT
# ═══════════════════════════════════════════════════════════

FORMULA_PROMPT = """
You are a Senior Software Engineering Assessment Designer and Campus Placement Technical Lead.

Generate a COMPLETE, precise knowledge map for the given software engineering, aptitude, or AI concept.

Output STRICTLY valid JSON.
No markdown.
No commentary.
No extra keys.

────────────────
SCHEMA (STRICT)
────────────────

{
  "meta": {
    "concept": "string",
    "chapter": "string",
    "syllabus_level": "Placement Assessment"
  },
  "layer_1_hard_formulas": [
    {
      "id": "F1",
      "formula": "string",
      "used_for": "string"
    }
  ],
  "layer_2_rule_based_logics": [
    {
      "id": "R1",
      "rule": "string",
      "applied_when": "string"
    }
  ],
  "layer_3_derived_consequences": [
    {
      "id": "C1",
      "consequence": "string",
      "derived_from": "F1 or R1"
    }
  ]
}

────────────────
MANDATORY RULES
────────────────

1. Include ALL core formulas/equations relevant to the topic:
   - For Coding/DSA: recurrence relations (Master Theorem), time/space complexity bounds (e.g. O(V + E), O(N log N)), index calculations.
   - For Core CS: network metrics (RTT, throughput, latency), page-table address translations, database keys, or normal form conditions.
   - For Aptitude: work-rate equations, distance-speed-time formulas, probability/combinatorics equations, or logical series formulas.
   - For AI: weight update rules, loss functions (cross-entropy, MSE), activation bounds, attention calculation metrics.
2. Include ALL decision rules (Layer 2) used to evaluate system states or eliminate wrong options (e.g., deadlock necessary conditions, ACID constraints, OOP inheritance rules, machine learning overfitting indicators, RAG retrieval metrics).
3. Layer 3 (consequences) must focus on trade-offs (time vs. space, precision vs. recall, latency vs. accuracy), side effects of thread/state mutations, deadlock outcomes, evaluation score impacts, or runtime behavior of edge cases (empty lists, null pointers, zero values).
4. Each formula and rule must generate at least 2 derived consequences.
5. Do NOT use LaTeX. All math and symbols must be written in clean Unicode scientific form (e.g. O(log N), sum(x_i), sqrt(n), W = R * T, P(A|B) = P(A and B)/P(B)).

No solved code snippets in this stage.
No questions.
No raw paragraphs of theory.

────────────────
INPUT
────────────────
"""


def get_formula_prompt(concept_name, description, chapter):
    return FORMULA_PROMPT + f"""
    CONCEPT: "{concept_name} {description}"
    CHAPTER: "{chapter}"
    SYLLABUS LEVEL: Technical Placement Assessment
    """


# ═══════════════════════════════════════════════════════════
# QUESTION GENERATION PROMPT
# ═══════════════════════════════════════════════════════════

def get_question_prompt(concept_data, concept, question_ids, axis_text):
    id_text = "\n".join(
        [f"{i+1}. {qid}" for i, qid in enumerate(question_ids)]
    )

    return f"""
        You are generating EXACTLY 20 placement-grade technical/aptitude MCQs.

        CONCEPT DATA:
        {json.dumps(concept_data, ensure_ascii=False)}

        INSPECTION UNITS
        IU-01 Edge cases & boundaries (null values, division-by-zero, empty inputs)
        IU-02 Complexity impact & runtime trade-offs (changing array to heap, scaling elements)
        IU-03 State changes & dry-runs (thread transitions, variable tracking, packet header updates)
        IU-04 Necessary vs sufficient (deadlock requirements, normalization criteria, ACID violations)
        IU-05 Evaluation metrics & results (Precision/Recall balance, model drift, SQL output rows)

        AXIS COMBINATIONS (FOLLOW EXACTLY)

        {axis_text}

        Constraints:
        1. No long calculations. Focus on inspection, reasoning, and algorithmic intuition.
        2. Solvable in 15–30 seconds.
        3. Exactly 4 options.
        4. One correct answer.
        5. All code elements or mathematical symbols must be written in clean Unicode (e.g. O(N log N), SQL JOIN, 1/r^2, cos theta). Do not use LaTeX ($ or \\).
        6. Do not repeat question templates inside this batch.

        Use the following question IDs EXACTLY in order:
        {id_text}

        Each object MUST follow this exact structure and key order:

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

        Return JSON array of 20 questions only.
        """


# ═══════════════════════════════════════════════════════════
# SINGLE QUESTION PROMPT (for AI quiz streaming)
# ═══════════════════════════════════════════════════════════

def get_single_question_prompt(concept):
    return f"""
You are a placement assessment API.

Generate EXACTLY ONE exam-grade Technical Placement MCQ.
Output ONLY valid JSON.
No markdown. No explanations. Stop after output.

JSON FORMAT:
{{
  "header": "",
  "question_title": "",
  "question": "",
  "options": {{ "A":"", "B":"", "C":"", "D":"" }},
  "answer": "A",
  "explanation": "",
  "sub_questions": [
    {{
      "type": "comfort",
      "question": "",
      "options": {{ "A":"", "B":"", "C":"", "D":"" }},
      "answer": "A"
    }},
    {{
      "type": "grounding",
      "question": "",
      "options": {{ "A":"", "B":"", "C":"", "D":"" }},
      "answer": "A"
    }},
    {{
      "type": "precursor",
      "question": "",
      "options": {{ "A":"", "B":"", "C":"", "D":"" }},
      "answer": "A"
    }}
  ]
}}

ABSOLUTE RULES:
- The question must test code dry-runs, logical deductions, system architecture, database queries, or mathematical aptitude shortcuts.
- Use only standard text/Unicode symbols. Do not use LaTeX.
- One clear concept tested.
- Exactly ONE correct option.

CONCEPT: {concept.name}
CONTEXT: {concept.description or "N/A"}
"""


from django.db import transaction

from quiz.models import Question

from ..engines.placement_axis_engine import (
    PlacementAxisEngine,
    PlacementState
)


def build_question_prompt(
    concept_data,
    concept
):

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
        batch_size=20
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