"""
JEE-specific prompts — the original, battle-tested prompts.

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
    You are an expert JEE Main Chemistry curriculum designer.

Generate a COMPLETE and EXAM-SUFFICIENT knowledge map for the given concept.

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
    "syllabus_level": "JEE Main"
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

1. Include ALL formulas required for JEE Main (NCERT standard).
2. Include ALL decision rules used to eliminate options.
3. Include proportional trends, sign logic, symmetry, extreme cases.
4. Do NOT invent formulas.
5. Do NOT include JEE Advanced only material.
6. Layer 3 size must be greater than Layer 1 + Layer 2 combined.
7. Each formula and rule must generate at least 2 consequences.
8. Maximum 4 consequences per formula/rule.
9. Keep concept internally closed and self-sufficient.

No solved examples.
No questions.
No theory paragraphs.

────────────────
INPUT
────────────────

"""


def get_formula_prompt(concept_name, description, chapter):
    return FORMULA_PROMPT + f"""

    CONCEPT: "{concept_name} {description}"
    CHAPTER: "{chapter}"
    SYLLABUS LEVEL: JEE Main
    """


# ═══════════════════════════════════════════════════════════
# QUESTION GENERATION PROMPT
# ═══════════════════════════════════════════════════════════

def get_question_prompt(concept_data, concept, question_ids, axis_text):
    id_text = "\n".join(
        [f"{i+1}. {qid}" for i, qid in enumerate(question_ids)]
    )

    return f"""
        You are generating EXACTLY 20 inspection-based MCQs.

        CONCEPT DATA:
        {json.dumps(concept_data, ensure_ascii=False)}

        INSPECTION UNITS
        IU-01 Zero condition
        IU-02 Dominance
        IU-03 Symmetry cancellation
        IU-04 Necessary vs sufficient
        IU-05 Directional behavior

        AXIS COMBINATIONS (FOLLOW EXACTLY)

        {axis_text}

        Constraints:
        1. No calculation.
        2. Solvable in 5–10 seconds.
        3. Exactly 4 options.
        4. One correct answer.
        5. Must test recognition, not solving.
        6. Do not repeat logical structure inside batch.
        7. All formulas and symbols must be written in clean Unicode scientific form (e.g., Q = A × B, 1/r², √(Q₁Q₂), cosθ, CO₃²⁻, m·s⁻¹).
        8. Do not use LaTeX ($, \\, {{}}, ^{{}}, _{{}}). Symbols must appear exactly as they would in a printed textbook and remain valid inside JSON.
        9. Do not reuse question templates within this batch.

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
You are an API, not a chatbot.

Generate EXACTLY ONE exam-grade JEE MCQ.
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
- Use only: π √ / ^ ( )
- No LaTeX, no backslashes, no words like pi or sqrt
- One clear concept
- Exactly ONE correct option

CONCEPT: {concept.name}
CONTEXT: {concept.description or "N/A"}
"""



from django.db import transaction

from quiz.models import Question

from ..engines.jee_axis_engine import (
    AxisEngine,
    GenerationState
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

    state = GenerationState(
        total_generated=existing_count
    )

    engine = AxisEngine(
        state=state,
        entity_sets=[
            "Entity-A",
            "Entity-B",
            "Entity-C",
            "Entity-D"
        ]
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