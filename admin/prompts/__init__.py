from . import jee
from . import placement
from . import pcs
from . import neet

def get_prompt_module(exam_type):
    etype = (exam_type or "jee").lower()
    if etype == "placement":
        return placement
    elif etype == "pcs":
        return pcs
    elif etype == "neet":
        return neet
    return jee

