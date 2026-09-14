"""
NEET UG specific prompts.

Designed for:
- NEET UG (Medical Entrance Examination)
- Physics, Chemistry, Biology (Botany & Zoology)

Primary emphasis:
- Strict NCERT textbook line-by-line alignment
- Assertion-Reason, Statement I & II, Match the Column
- Conceptual clarity & fast recognition (180 questions in 200 minutes)
"""

import json
from django.db import transaction
from quiz.models import Question
from ..engines.neet_axis_engine import NEETAxisEngine, NEETState


# ==========================================================
# KNOWLEDGE MAP PROMPT
# ==========================================================

FORMULA_PROMPT = """
You are a senior NEET UG curriculum and assessment designer with expert knowledge of NCERT Class 11 and 12 Physics, Chemistry, and Biology.

Your job is to create a COMPLETE, NCERT-SUFFICIENT knowledge map for the given NEET concept.
Output STRICTLY valid JSON. No markdown. No commentary. No additional keys.

==================================================
STRICT JSON SCHEMA
==================================================

{
  "meta": {
    "concept": "string",
    "chapter": "string",
    "subject": "Physics/Chemistry/Biology",
    "syllabus_level": "NEET UG (NCERT)"
  },
  "ncert_key_definitions_and_facts": [
    {
      "id": "F1",
      "fact": "string",
      "ncert_reference_context": "string"
    }
  ],
  "core_formulas_or_equations": [
    {
      "id": "EQ1",
      "formula": "string",
      "used_for": "string"
    }
  ],
  "biological_or_chemical_pathways": [
    {
      "id": "P1",
      "process": "string",
      "key_steps_or_enzymes": "string"
    }
  ],
  "scientific_terms_and_classifications": [
    {
      "id": "T1",
      "term": "string",
      "definition_or_example": "string"
    }
  ],
  "ncert_exceptions_and_anomalies": [
    {
      "id": "EX1",
      "general_rule": "string",
      "exception": "string"
    }
  ],
  "assertion_reason_traps": [
    {
      "id": "AR1",
      "assertion": "string",
      "reason": "string",
      "is_reason_correct_explanation": true
    }
  ]
}

==================================================
CORE RULES
==================================================
1. Stay strictly within NCERT Class 11 & 12 syllabus boundaries for NEET.
2. Highlight exact NCERT keywords, scientific names, enzymes, reagents, and physical units.
3. Include critical exceptions (e.g. anomalous expansion of water, exceptions in periodic trends, atypical cell divisions).
4. All math and symbols must use clean Unicode (e.g. H₂SO₄, ATP → ADP + Pi, v = u + at, λ = h/p, sinθ). No LaTeX (no $ or \\).
5. Output ONLY valid JSON.
"""


def get_formula_prompt(concept_name, description, chapter):
    return FORMULA_PROMPT + f"""

CONCEPT: "{concept_name}"
DESCRIPTION: "{description or 'N/A'}"
CHAPTER: "{chapter or 'N/A'}"
EXAM SCOPE: NEET UG (NCERT Class 11 & 12 Standard)
"""


# ==========================================================
# QUESTION GENERATION PROMPT
# ==========================================================

QUESTION_PROMPT = """
You are a senior NEET UG Question Paper Setter.
Generate EXACTLY 20 high-quality NEET-grade MCQs based on NCERT guidelines.

==================================================
KNOWLEDGE MAP
==================================================
{concept_data}

==================================================
QUESTION COVERAGE PLAN
==================================================
{axis_text}

==================================================
CONSTRAINTS & RULES
==================================================
1. Strict NCERT textbook alignment.
2. Include exam formats typical of NEET:
   - Direct NCERT line recall
   - Statement I and Statement II questions
   - Assertion and Reason questions
   - Match Column I with Column II
3. Solvable within 40–50 seconds per question.
4. Exactly 4 options (A, B, C, D) with 1 correct option.
5. All symbols and formulas must use clean Unicode (e.g., ΔH, H₂O, f = 1/2π√(LC), α-amino acid). Do NOT use LaTeX.
6. Do not repeat question templates inside this batch.

==================================================
OUTPUT
==================================================
Return ONLY a JSON array of exactly 20 objects. No markdown. No explanations.

Each object MUST follow this exact structure:
{{
  "question_id": "",
  "question_title": "",
  "concept": "{concept_name}",
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
"""


def get_question_prompt(concept_data, concept, question_ids, axis_text):
    id_text = "\n".join(f"{i + 1}. {qid}" for i, qid in enumerate(question_ids))
    return QUESTION_PROMPT.format(
        concept_data=json.dumps(concept_data, ensure_ascii=False, indent=2),
        concept_name=concept.name,
        axis_text=f"{axis_text}\n\nQUESTION IDs:\n{id_text}"
    )


def build_question_prompt(concept_data, concept):
    with transaction.atomic():
        existing_count = Question.objects.select_for_update().filter(concept=concept).count()
        batch_size = 20
        question_ids = [f"C{concept.id}-Q{existing_count + i + 1}" for i in range(batch_size)]

    state = NEETState(total_generated=existing_count)
    engine = NEETAxisEngine(state=state)
    axis_batch = engine.generate_batch(batch_size=20)
    axis_text = "\n".join([f"{i+1}. {item['axis_signature']}" for i, item in enumerate(axis_batch)])

    return get_question_prompt(
        concept_data=concept_data,
        concept=concept,
        question_ids=question_ids,
        axis_text=axis_text
    )


def get_single_question_prompt(concept):
    return f"""
You are a NEET UG Question Paper Setter.
Generate EXACTLY ONE high-quality NEET UG MCQ (NCERT Standard).

CONCEPT: {concept.name}
CONTEXT: {concept.description or "N/A"}

JSON FORMAT:
{{
  "header": "",
  "question_title": "",
  "question": "",
  "options": {{ "A": "", "B": "", "C": "", "D": "" }},
  "answer": "A",
  "explanation": "",
  "sub_questions": []
}}
"""