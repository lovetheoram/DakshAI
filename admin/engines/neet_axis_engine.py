"""
NEET UG Coverage / Axis Engine.

Designed for:
- NEET UG (Medical Entrance)
- Physics, Chemistry, Biology (Botany & Zoology)

Primary Focus:
- Strict NCERT adherence
- Fact recognition, scientific names, biological diagrams, cycle steps
- Assertion & Reason, Statement I & Statement II
- Formula applications, unit conversions, exception cases
"""

from dataclasses import dataclass
from typing import List, Dict


# ==========================================================
# KNOWLEDGE TARGETS
# ==========================================================

KNOWLEDGE_TARGETS = [
    "ncert_facts_and_definitions",
    "scientific_names_and_classifications",
    "biological_cycles_and_pathways",
    "chemical_reactions_and_reagents",
    "physics_formulas_and_units",
    "diagrams_and_structural_labels",
    "exceptions_and_anomalies",
    "assertion_reason_couplets",
]


# ==========================================================
# REASONING MODES
# ==========================================================

REASONING_MODES = [
    "direct_recall",
    "step_identification",
    "cause_effect_analysis",
    "statement_verification",
    "pair_matching",
    "numerical_calculation",
    "exception_spotting",
]


# ==========================================================
# QUESTION FORMS
# ==========================================================

QUESTION_FORMS = [
    "direct_mcq",
    "statement_1_and_2",
    "assertion_reason",
    "match_column_i_and_ii",
    "correct_incorrect_statements",
    "sequence_ordering",
    "numerical_formula_based",
]


# ==========================================================
# TRAPS
# ==========================================================

TRAPS = [
    "none",
    "ncert_wording_confusion",
    "organelle_or_tissue_misattribution",
    "reversed_direction_or_sign",
    "similar_sounding_terms",
    "partial_truth",
    "exception_overlook",
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
# NEET COVERAGE TEMPLATE (20 Questions Batch)
# ==========================================================

COVERAGE_TEMPLATE = [
    # 1–4: NCERT Core Facts & Terminology
    {
        "knowledge_target": "ncert_facts_and_definitions",
        "reasoning": "direct_recall",
        "question_form": "direct_mcq",
        "trap": "none",
        "difficulty": "L1",
    },
    {
        "knowledge_target": "scientific_names_and_classifications",
        "reasoning": "pair_matching",
        "question_form": "match_column_i_and_ii",
        "trap": "similar_sounding_terms",
        "difficulty": "L1",
    },
    {
        "knowledge_target": "ncert_facts_and_definitions",
        "reasoning": "statement_verification",
        "question_form": "correct_incorrect_statements",
        "trap": "ncert_wording_confusion",
        "difficulty": "L1",
    },
    {
        "knowledge_target": "exceptions_and_anomalies",
        "reasoning": "exception_spotting",
        "question_form": "direct_mcq",
        "trap": "exception_overlook",
        "difficulty": "L2",
    },
    # 5–8: Biological Pathways, Cycles & Chemical Reactions
    {
        "knowledge_target": "biological_cycles_and_pathways",
        "reasoning": "step_identification",
        "question_form": "sequence_ordering",
        "trap": "organelle_or_tissue_misattribution",
        "difficulty": "L2",
    },
    {
        "knowledge_target": "chemical_reactions_and_reagents",
        "reasoning": "cause_effect_analysis",
        "question_form": "direct_mcq",
        "trap": "partial_truth",
        "difficulty": "L2",
    },
    {
        "knowledge_target": "biological_cycles_and_pathways",
        "reasoning": "statement_verification",
        "question_form": "statement_1_and_2",
        "trap": "partial_truth",
        "difficulty": "L2",
    },
    {
        "knowledge_target": "assertion_reason_couplets",
        "reasoning": "cause_effect_analysis",
        "question_form": "assertion_reason",
        "trap": "ncert_wording_confusion",
        "difficulty": "L2",
    },
    # 9–12: Physics Formulas & Calculations / Physical Chemistry
    {
        "knowledge_target": "physics_formulas_and_units",
        "reasoning": "numerical_calculation",
        "question_form": "numerical_formula_based",
        "trap": "reversed_direction_or_sign",
        "difficulty": "L2",
    },
    {
        "knowledge_target": "physics_formulas_and_units",
        "reasoning": "direct_recall",
        "question_form": "direct_mcq",
        "trap": "none",
        "difficulty": "L1",
    },
    {
        "knowledge_target": "diagrams_and_structural_labels",
        "reasoning": "direct_recall",
        "question_form": "match_column_i_and_ii",
        "trap": "organelle_or_tissue_misattribution",
        "difficulty": "L2",
    },
    {
        "knowledge_target": "chemical_reactions_and_reagents",
        "reasoning": "pair_matching",
        "question_form": "match_column_i_and_ii",
        "trap": "similar_sounding_terms",
        "difficulty": "L2",
    },
    # 13–16: Statement Analysis & NCERT Precision
    {
        "knowledge_target": "ncert_facts_and_definitions",
        "reasoning": "statement_verification",
        "question_form": "statement_1_and_2",
        "trap": "partial_truth",
        "difficulty": "L2",
    },
    {
        "knowledge_target": "assertion_reason_couplets",
        "reasoning": "cause_effect_analysis",
        "question_form": "assertion_reason",
        "trap": "ncert_wording_confusion",
        "difficulty": "L3",
    },
    {
        "knowledge_target": "exceptions_and_anomalies",
        "reasoning": "statement_verification",
        "question_form": "correct_incorrect_statements",
        "trap": "exception_overlook",
        "difficulty": "L2",
    },
    {
        "knowledge_target": "scientific_names_and_classifications",
        "reasoning": "statement_verification",
        "question_form": "correct_incorrect_statements",
        "trap": "similar_sounding_terms",
        "difficulty": "L2",
    },
    # 17–20: Advanced NCERT Integration & High Yield Topics
    {
        "knowledge_target": "biological_cycles_and_pathways",
        "reasoning": "cause_effect_analysis",
        "question_form": "direct_mcq",
        "trap": "organelle_or_tissue_misattribution",
        "difficulty": "L2",
    },
    {
        "knowledge_target": "physics_formulas_and_units",
        "reasoning": "numerical_calculation",
        "question_form": "numerical_formula_based",
        "trap": "reversed_direction_or_sign",
        "difficulty": "L3",
    },
    {
        "knowledge_target": "ncert_facts_and_definitions",
        "reasoning": "statement_verification",
        "question_form": "statement_1_and_2",
        "trap": "ncert_wording_confusion",
        "difficulty": "L3",
    },
    {
        "knowledge_target": "assertion_reason_couplets",
        "reasoning": "cause_effect_analysis",
        "question_form": "assertion_reason",
        "trap": "partial_truth",
        "difficulty": "L3",
    },
]


@dataclass
class NEETState:
    total_generated: int = 0


class NEETAxisEngine:
    def __init__(self, state: NEETState):
        self.state = state

    def generate_batch(self, batch_size: int = 20) -> List[Dict]:
        rows = []
        for i in range(batch_size):
            global_index = self.state.total_generated + i
            template_index = global_index % len(COVERAGE_TEMPLATE)
            template = COVERAGE_TEMPLATE[template_index]

            rows.append({
                "question_number": global_index + 1,
                "knowledge_target": template["knowledge_target"],
                "reasoning": template["reasoning"],
                "question_form": template["question_form"],
                "trap": template["trap"],
                "difficulty": template["difficulty"],
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
