import json
from django.db import transaction
from syllabus.models import Concept
from quiz.models import Question, SubQuestion

@transaction.atomic
def load_sdqb_questions(json_path):

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        print(item["concept"])
        # MAIN concept (safe + idempotent)
        concept, _ = Concept.objects.get_or_create(
            name=item["concept"].strip()
        )

        # Skip duplicate question
        if Question.objects.filter(qid=item["question_id"]).exists():
            continue

        # Create main question
        q = Question.objects.create(
            qid=item["question_id"],
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
        for sq in item.get("sub_questions", []):

            sq_concept, _ = Concept.objects.get_or_create(
                name=sq["concept"].strip()
            )

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
load_sdqb_questions("quiz/jee_sdqb1.json")


