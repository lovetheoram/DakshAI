from dataclasses import dataclass
from typing import List, Dict


# ==========================================================
# INSPECTION UNITS (FIXED)
# ==========================================================

INSPECTION_UNITS = [
    "IU-01 Zero condition",
    "IU-02 Dominance",
    "IU-03 Symmetry cancellation",
    "IU-04 Necessary vs sufficient",
    "IU-05 Directional behavior"
]


# ==========================================================
# AXIS POOLS
# ==========================================================

AXIS_POOLS = {
    "intent": [
        "identify_correct",
        "identify_incorrect",
        "comparison",
        "elimination"
    ],
    "framing": [
        "direct",
        "which_statement",
        "assertion_reason",
        "matching"
    ],
    "trap": [
        "overgeneralization",
        "sign_confusion",
        "symmetry_misread",
        "partial_condition_error"
    ],
    "difficulty": ["L1", "L2"]
}


# ==========================================================
# STATE
# ==========================================================

@dataclass
class GenerationState:
    total_generated: int = 0


# ==========================================================
# AXIS ENGINE
# ==========================================================

class AxisEngine:

    def __init__(self, state: GenerationState, entity_sets: List[str]):
        self.state = state
        self.entity_sets = entity_sets

        if not entity_sets:
            raise ValueError("Entity sets cannot be empty")


    def generate_batch(self, batch_size: int = 20) -> List[Dict]:

        combinations = []

        for i in range(batch_size):

            global_index = self.state.total_generated + i

            iu = INSPECTION_UNITS[global_index % len(INSPECTION_UNITS)]

            intent = AXIS_POOLS["intent"][
                (global_index * 3) % len(AXIS_POOLS["intent"])
            ]

            framing = AXIS_POOLS["framing"][
                (global_index * 5) % len(AXIS_POOLS["framing"])
            ]

            trap = AXIS_POOLS["trap"][
                (global_index * 7) % len(AXIS_POOLS["trap"])
            ]

            difficulty = AXIS_POOLS["difficulty"][global_index % 2]

            entity = self.entity_sets[
                (global_index * 11) % len(self.entity_sets)
            ]

            combinations.append({
                "iu": iu,
                "intent": intent,
                "framing": framing,
                "entity": entity,
                "trap": trap,
                "difficulty": difficulty,
                "axis_signature": (
                    f"{iu} | {intent} | {framing} | "
                    f"{entity} | {trap} | {difficulty}"
                )
            })

        self.state.total_generated += batch_size

        return combinations