import json
from django.db import transaction
from syllabus.models import Concept
from quiz.models import Question, SubQuestion

@transaction.atomic
def load_sdqb_questions(json_path):
    """
    Load SDQB questions from JSON and save into DB.
    Assumes syllabus (Concepts) already exists.
    """

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        # Find the concept in syllabus
        try:
            concept = Concept.objects.get(name=item["concept"])
        except Concept.DoesNotExist:
            print(f"Concept not found: {item['concept']}")
            continue

        # Skip if question already exists
        if Question.objects.filter(qid=item["question_id"]).exists():
            continue

        # Create main question
        q = Question.objects.create(
            qid=item["question_id"],
            header=item["header"],
            question_title=item["question_title"],
            concept=concept,
            question=item["question"],
            option_a=item["options"]["A"],
            option_b=item["options"]["B"],
            option_c=item["options"]["C"],
            option_d=item["options"]["D"],
            correct_option=item["answer"],
        )

        # Create sub-questions
        for sq in item["sub_questions"]:
            try:
                sq_concept = Concept.objects.get(name=sq["concept"])
            except Concept.DoesNotExist:
                sq_concept = concept  # fallback to main concept

            SubQuestion.objects.create(
                parent=q,
                type=sq["type"],
                concept=sq_concept,
                question=sq["question"],
                option_a=sq["options"]["A"],
                option_b=sq["options"]["B"],
                option_c=sq["options"]["C"],
                option_d=sq["options"]["D"],
                correct_option=sq["answer"],
            )

# Usage
load_sdqb_questions("quiz/jee_sdqb.json")
