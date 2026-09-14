"""
State PCS prompts.

Designed for:
- BPSC
- UPPSC
- Other State PCS examinations

Primary domains:
- Indian History
- Ancient / Medieval / Modern India
- Bihar / Uttar Pradesh specific history
- Indian Polity
- Geography
- Economy
- Environment
- Science
- Art & Culture
- Current Affairs
- State-specific GK

Philosophy:
PCS preparation is not simply question generation.
The system should build a compact knowledge map and then
inspect whether the learner actually understands and remembers
that knowledge from multiple exam-relevant angles.
"""

import json
from django.db import transaction
from quiz.models import Question
from ..engines.pcs_axis_engine import PCSAxisEngine, PCSState


# ==========================================================
# KNOWLEDGE MAP PROMPT
# ==========================================================

FORMULA_PROMPT = """
You are a senior State PCS examination content designer
with deep experience designing questions for BPSC, UPPSC, and State PCS examinations.

Your job is to create a COMPLETE but concise knowledge map for the given PCS concept.
Output STRICTLY valid JSON. No markdown. No commentary. No additional keys.

==================================================
STRICT JSON SCHEMA
==================================================

{
  "meta": {
    "concept": "string",
    "chapter": "string",
    "domain": "string",
    "exam_scope": "BPSC/UPPSC/State PCS"
  },
  "core_facts": [
    {
      "id": "F1",
      "fact": "string",
      "importance": "high"
    }
  ],
  "key_terms_and_entities": [
    {
      "id": "T1",
      "term": "string",
      "meaning": "string"
    }
  ],
  "chronology": [
    {
      "id": "CH1",
      "event": "string",
      "year_or_period": "string",
      "significance": "string"
    }
  ],
  "cause_effect": [
    {
      "id": "CE1",
      "cause": "string",
      "effect": "string"
    }
  ],
  "relationships": [
    {
      "id": "R1",
      "entity_a": "string",
      "entity_b": "string",
      "relationship": "string"
    }
  ],
  "comparisons": [
    {
      "id": "C1",
      "item_a": "string",
      "item_b": "string",
      "difference": "string"
    }
  ],
  "state_specific_facts": [
    {
      "id": "S1",
      "state": "string",
      "fact": "string",
      "significance": "string"
    }
  ],
  "common_traps": [
    {
      "id": "TR1",
      "incorrect_belief": "string",
      "correct_fact": "string"
    }
  ],
  "exam_patterns": [
    {
      "id": "EP1",
      "pattern": "string",
      "how_tested": "string"
    }
  ]
}

==================================================
CORE RULES
==================================================
1. Stay strictly within the supplied concept.
2. Include only reliable and established information.
3. Do NOT invent dates, places, people, books, organizations, or constitutional provisions.
4. Prefer information relevant to actual PCS examinations.
5. Include chronology, cause/effect, and state-specific facts (BPSC/UPPSC).
6. Return ONLY valid JSON.
"""


def get_formula_prompt(concept_name, description, chapter):
    return FORMULA_PROMPT + f"""

CONCEPT: "{concept_name}"
DESCRIPTION: "{description or 'N/A'}"
CHAPTER: "{chapter or 'N/A'}"
EXAM SCOPE: State PCS — BPSC / UPPSC / similar examinations
"""


# ==========================================================
# QUESTION GENERATION PROMPT
# ==========================================================

QUESTION_PROMPT = """
You are a senior State PCS Prelims question setter.
Generate EXACTLY 20 high-quality PCS-style MCQs.

==================================================
KNOWLEDGE MAP
==================================================
{concept_data}

==================================================
QUESTION COVERAGE PLAN
==================================================
{axis_text}

==================================================
OUTPUT
==================================================
Return ONLY a JSON array of exactly 20 objects. No markdown. No explanations.

Each object MUST follow this exact structure:
{{
  "question_id": "",
  "question_title": "",
  "concept": "",
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
        axis_text=f"{axis_text}\n\nQUESTION IDs:\n{id_text}"
    )


def build_question_prompt(concept_data, concept):
    with transaction.atomic():
        existing_count = Question.objects.select_for_update().filter(concept=concept).count()
        batch_size = 20
        question_ids = [f"C{concept.id}-Q{existing_count + i + 1}" for i in range(batch_size)]

    state = PCSState(total_generated=existing_count)
    engine = PCSAxisEngine(state=state)
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
You are a State PCS Prelims question setter.
Generate EXACTLY ONE high-quality State PCS MCQ.

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
