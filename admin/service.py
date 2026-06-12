# import json
# from django.conf import settings
# from .question_axis_engine import AxisEngine, GenerationState
# from django.db import transaction

# from quiz.models import Question
# from .prompts import get_prompt_module, resolve_exam_type

# import google.generativeai as genai
# from django.conf import settings

# genai.configure(api_key=settings.GEMINI_API_KEY)

# model = genai.GenerativeModel("gemini-2.5-flash")


# def generate_formula_meta(concept_name, description, chapter, exam_type="jee"):

#     prompt_module = get_prompt_module(exam_type)
#     prompt = prompt_module.get_formula_prompt(concept_name, description, chapter)

#     response = model.generate_content(
#         prompt,
#         generation_config={
#             "temperature": 0.2,
#             "response_mime_type": "application/json"
#         }
#     )

#     text = response.text.strip()

#     try:
#         return json.loads(text)
#     except:
#         raise Exception("Invalid JSON from Gemini")
    


# def generate_questions_from_meta(meta_json: dict, concept, exam_type="jee"):
#     """
#     meta_json   -> concept knowledge map
#     concept     -> Concept model instance
#     exam_type   -> key to select prompt module
#     """

#     prompt_module = get_prompt_module(exam_type)

#     question_prompt = build_question_prompt(
#         concept_data=meta_json,
#         concept=concept,
#         prompt_module=prompt_module,
#     )
#     response = model.generate_content(
#         question_prompt,
#         generation_config={
#             "temperature": 0.4,
#             "response_mime_type": "application/json"
#         }
#     )

#     try:
#         return json.loads(response.text)
#     except:
#         raise Exception("Invalid JSON from Gemini")
    



# def build_question_prompt(concept_data: dict, concept, prompt_module):

#     # 1️⃣ Get current total from DB (THIS is the real state)
#     with transaction.atomic():

#         # Lock rows of this concept (prevents race condition)
#         existing_count = (
#             Question.objects
#             .select_for_update()
#             .filter(concept=concept)
#             .count()
#         )

#         batch_size = 20

#         # Generate IDs safely
#         question_ids = [
#             f"{concept.name.upper()}-{existing_count + i + 1}"
#             for i in range(batch_size)
#         ]

#     print(existing_count,"..............")

#     # 2️⃣ Create fresh state
#     state = GenerationState(
#         total_generated=existing_count
#     )
#     entity_sets = ["Entity-A", "Entity-B", "Entity-C", "Entity-D"]
#     # 4️⃣ Create engine
#     engine = AxisEngine(
#         state=state,
#         entity_sets=entity_sets
#     )

#     # 5️⃣ Generate axis batch
#     axis_batch = engine.generate_batch(batch_size=20)
#     axis_text = "\n".join(
#         [f"{i+1}. {item['axis_signature']}" for i, item in enumerate(axis_batch)]
#     )

#     # 6️⃣ Use exam-specific prompt
#     return prompt_module.get_question_prompt(
#         concept_data=concept_data,
#         concept=concept,
#         question_ids=question_ids,
#         axis_text=axis_text,
#     )




import json

import google.generativeai as genai

from django.conf import settings

from .prompts import get_prompt_module

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


def generate_formula_meta(
    concept_name,
    description,
    chapter,
    exam_type="jee"
):
    prompt_module = get_prompt_module(exam_type)

    prompt = prompt_module.get_formula_prompt(
        concept_name,
        description,
        chapter
    )

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json"
        }
    )

    return json.loads(response.text)


def generate_questions_from_meta(
    meta_json,
    concept,
    exam_type="jee"
):

    prompt_module = get_prompt_module(exam_type)

    question_prompt = prompt_module.build_question_prompt(
        concept_data=meta_json,
        concept=concept
    )

    response = model.generate_content(
        question_prompt,
        generation_config={
            "temperature": 0.4,
            "response_mime_type": "application/json"
        }
    )

    return json.loads(response.text)