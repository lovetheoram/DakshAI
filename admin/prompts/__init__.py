from . import jee
from . import placement

def get_prompt_module(exam_type):
    if exam_type == "placement":
        return placement
    return jee
