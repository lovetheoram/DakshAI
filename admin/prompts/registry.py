from ..engines.jee_axis_engine import AxisEngine as JeeQuestionEngine
from ..engines.placement_axis_engine import PlacementAxisEngine as PlacementQuestionEngine
from ..engines.pcs_axis_engine import PCSAxisEngine as PcsQuestionEngine
from ..engines.neet_axis_engine import NEETAxisEngine as NeetQuestionEngine

QUESTION_ENGINE_REGISTRY = {
    "jee": JeeQuestionEngine,
    "placement": PlacementQuestionEngine,
    "pcs": PcsQuestionEngine,
    "neet": NeetQuestionEngine,
}