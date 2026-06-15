from dataclasses import dataclass

SCENARIOS = [
    "interview",
    "production",
    "debugging",
    "system_design"
]

REASONING = [
    "edge_case",
    "tradeoff",
    "dry_run",
    "output_prediction"
]

TRAPS = [
    "common_misconception",
    "partial_truth",
    "implementation_detail",
    "terminology_confusion"
]

DIFFICULTY = [
    "easy",
    "medium"
]


@dataclass
class PlacementState:
    total_generated: int = 0


class PlacementAxisEngine:

    def __init__(self, state):
        self.state = state

    def generate_batch(
        self,
        batch_size=20
    ):

        rows = []

        for i in range(batch_size):

            idx = self.state.total_generated + i

            scenario = SCENARIOS[
                idx % len(SCENARIOS)
            ]

            reasoning = REASONING[
                (idx * 3) % len(REASONING)
            ]

            trap = TRAPS[
                (idx * 5) % len(TRAPS)
            ]

            difficulty = DIFFICULTY[
                idx % len(DIFFICULTY)
            ]

            rows.append({
                "axis_signature":
                    f"{scenario} | "
                    f"{reasoning} | "
                    f"{trap} | "
                    f"{difficulty}"
            })

        self.state.total_generated += batch_size

        return rows
