# registry.py

from ..engines.jee_axis_engine import AxisEngine as JeeQuestionEngine
from ..engines.placement_axis_engine import PlacementAxisEngine as PlacementQuestionEngine

QUESTION_ENGINE_REGISTRY = {
    "jee": JeeQuestionEngine,
    "placement": PlacementQuestionEngine,
}