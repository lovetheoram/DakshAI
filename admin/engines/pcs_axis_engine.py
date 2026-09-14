"""
State PCS Coverage / Axis Engine.

Designed for:
- BPSC
- UPPSC
- Other State PCS examinations

The engine creates a deterministic coverage plan.

It does NOT generate random questions.

It tells the LLM WHAT aspect of the concept should be tested.

The LLM then realizes that assessment target as an actual
PCS-style MCQ.
"""

from dataclasses import dataclass
from typing import List, Dict


# ==========================================================
# KNOWLEDGE TARGETS
# ==========================================================

KNOWLEDGE_TARGETS = [

    "core_facts",

    "key_terms_and_entities",

    "chronology",

    "cause_effect",

    "relationships",

    "comparisons",

    "state_specific_facts",

    "common_traps",

]


# ==========================================================
# REASONING MODES
# ==========================================================

REASONING_MODES = [

    "recognize",

    "distinguish",

    "order",

    "connect",

    "infer",

    "eliminate",

    "verify",

]


# ==========================================================
# QUESTION FORMS
# ==========================================================

QUESTION_FORMS = [

    "direct_fact",

    "statement_analysis",

    "chronology",

    "match_following",

    "cause_effect",

    "pair_identification",

    "correct_statement",

    "incorrect_statement",

    "conceptual_distinction",

    "elimination",

    "state_specific",

]


# ==========================================================
# TRAPS
# ==========================================================

TRAPS = [

    "none",

    "similar_concept",

    "wrong_chronology",

    "reversed_relationship",

    "partial_truth",

    "common_misconception",

    "state_fact_confusion",

    "terminology_confusion",

]


# ==========================================================
# DIFFICULTY
# ==========================================================

DIFFICULTIES = [

    "L1",

    "L2",

    "L3",

]


# ==========================================================
# PCS COVERAGE TEMPLATE
# ==========================================================

"""
The 20 questions roughly cover:

1–3   Core facts / terminology
4–5   Relationships
6–7   Chronology / sequence
8–9   Cause and effect
10–11 Comparisons / distinctions
12–13 Statement analysis
14–15 Elimination
16–17 Common traps
18    State-specific
19    Mixed application
20    High-value synthesis

The prompt adapts the exact question to the concept.

The engine deliberately does NOT force every target
to be applicable. The LLM is instructed to adapt when
a target is irrelevant.
"""

COVERAGE_TEMPLATE = [

    # ======================================================
    # FOUNDATION
    # ======================================================

    {
        "knowledge_target": "core_facts",
        "reasoning": "recognize",
        "question_form": "direct_fact",
        "trap": "none",
        "difficulty": "L1",
    },

    {
        "knowledge_target": "key_terms_and_entities",
        "reasoning": "recognize",
        "question_form": "pair_identification",
        "trap": "terminology_confusion",
        "difficulty": "L1",
    },

    {
        "knowledge_target": "core_facts",
        "reasoning": "distinguish",
        "question_form": "correct_statement",
        "trap": "partial_truth",
        "difficulty": "L1",
    },

    # ======================================================
    # RELATIONSHIPS
    # ======================================================

    {
        "knowledge_target": "relationships",
        "reasoning": "connect",
        "question_form": "match_following",
        "trap": "reversed_relationship",
        "difficulty": "L2",
    },

    {
        "knowledge_target": "relationships",
        "reasoning": "distinguish",
        "question_form": "conceptual_distinction",
        "trap": "similar_concept",
        "difficulty": "L2",
    },

    # ======================================================
    # CHRONOLOGY
    # ======================================================

    {
        "knowledge_target": "chronology",
        "reasoning": "order",
        "question_form": "chronology",
        "trap": "wrong_chronology",
        "difficulty": "L2",
    },

    {
        "knowledge_target": "chronology",
        "reasoning": "verify",
        "question_form": "statement_analysis",
        "trap": "wrong_chronology",
        "difficulty": "L2",
    },

    # ======================================================
    # CAUSE / EFFECT
    # ======================================================

    {
        "knowledge_target": "cause_effect",
        "reasoning": "connect",
        "question_form": "cause_effect",
        "trap": "reversed_relationship",
        "difficulty": "L2",
    },

    {
        "knowledge_target": "cause_effect",
        "reasoning": "infer",
        "question_form": "statement_analysis",
        "trap": "partial_truth",
        "difficulty": "L2",
    },

    # ======================================================
    # COMPARISON
    # ======================================================

    {
        "knowledge_target": "comparisons",
        "reasoning": "distinguish",
        "question_form": "conceptual_distinction",
        "trap": "similar_concept",
        "difficulty": "L2",
    },

    {
        "knowledge_target": "comparisons",
        "reasoning": "eliminate",
        "question_form": "incorrect_statement",
        "trap": "partial_truth",
        "difficulty": "L2",
    },

    # ======================================================
    # STATEMENT ANALYSIS
    # ======================================================

    {
        "knowledge_target": "core_facts",
        "reasoning": "verify",
        "question_form": "statement_analysis",
        "trap": "common_misconception",
        "difficulty": "L2",
    },

    {
        "knowledge_target": "relationships",
        "reasoning": "eliminate",
        "question_form": "statement_analysis",
        "trap": "reversed_relationship",
        "difficulty": "L2",
    },

    # ======================================================
    # ELIMINATION
    # ======================================================

    {
        "knowledge_target": "core_facts",
        "reasoning": "eliminate",
        "question_form": "incorrect_statement",
        "trap": "partial_truth",
        "difficulty": "L2",
    },

    {
        "knowledge_target": "common_traps",
        "reasoning": "eliminate",
        "question_form": "statement_analysis",
        "trap": "common_misconception",
        "difficulty": "L2",
    },

    # ======================================================
    # COMMON TRAPS
    # ======================================================

    {
        "knowledge_target": "common_traps",
        "reasoning": "distinguish",
        "question_form": "correct_statement",
        "trap": "similar_concept",
        "difficulty": "L2",
    },

    {
        "knowledge_target": "common_traps",
        "reasoning": "verify",
        "question_form": "incorrect_statement",
        "trap": "terminology_confusion",
        "difficulty": "L2",
    },

    # ======================================================
    # STATE-SPECIFIC
    # ======================================================

    {
        "knowledge_target": "state_specific_facts",
        "reasoning": "recognize",
        "question_form": "state_specific",
        "trap": "state_fact_confusion",
        "difficulty": "L1",
    },

    # ======================================================
    # MIXED APPLICATION
    # ======================================================

    {
        "knowledge_target": "core_facts",
        "reasoning": "connect",
        "question_form": "statement_analysis",
        "trap": "none",
        "difficulty": "L2",
    },

    {
        "knowledge_target": "common_traps",
        "reasoning": "eliminate",
        "question_form": "elimination",
        "trap": "partial_truth",
        "difficulty": "L3",
    },
]


# ==========================================================
# STATE
# ==========================================================

@dataclass
class PCSState:

    total_generated: int = 0


# ==========================================================
# ENGINE
# ==========================================================

class PCSAxisEngine:

    def __init__(
        self,
        state: PCSState
    ):

        self.state = state

    # ------------------------------------------------------
    # GENERATE BATCH
    # ------------------------------------------------------

    def generate_batch(
        self,
        batch_size: int = 20
    ) -> List[Dict]:

        rows = []

        for i in range(batch_size):

            global_index = (
                self.state.total_generated + i
            )

            template_index = (
                global_index % len(COVERAGE_TEMPLATE)
            )

            template = COVERAGE_TEMPLATE[
                template_index
            ]

            rows.append({

                "question_number":
                    global_index + 1,

                "knowledge_target":
                    template["knowledge_target"],

                "reasoning":
                    template["reasoning"],

                "question_form":
                    template["question_form"],

                "trap":
                    template["trap"],

                "difficulty":
                    template["difficulty"],

                "axis_signature": (
                    f"TARGET={template['knowledge_target']} | "
                    f"REASONING={template['reasoning']} | "
                    f"FORM={template['question_form']} | "
                    f"TRAP={template['trap']} | "
                    f"LEVEL={template['difficulty']}"
                )
            })

        self.state.total_generated += batch_size

        return rows


# ==========================================================
# COVERAGE SUMMARY
# ==========================================================

def get_coverage_summary(
    axis_batch: List[Dict]
) -> Dict:

    summary = {}

    for row in axis_batch:

        target = row["knowledge_target"]

        summary[target] = (
            summary.get(target, 0) + 1
        )

    return summary