# registry.py

from .engines.jee_engine import JeeQuestionEngine
from .engines.placement_engine import PlacementQuestionEngine

QUESTION_ENGINE_REGISTRY = {
    "jee": JeeQuestionEngine(),
    "placement": PlacementQuestionEngine(),
}