from syllabus.models import Concept
from quiz.models import Question
from .service import generate_formula_meta, generate_questions_from_meta


def generate_meta_task(concept_id, chapter):
    try:
        concept = Concept.objects.select_related(
            "subtopic__topic__subject__exam"
        ).get(id=concept_id)
        exam_type = concept.subtopic.topic.subject.exam.exam_type

        placeholder = {'estimated_time': None, 'resources': None}

        if concept.ai_meta == placeholder or not concept.ai_meta:
            meta_json = generate_formula_meta(
                concept.name,
                concept.description,
                chapter,
                exam_type=exam_type
            )
            concept.ai_meta = meta_json
            concept.save(update_fields=["ai_meta"])

    except Exception as e:
        print("Meta thread error:", e)


def generate_questions_task(concept_id):
    try:
        concept = Concept.objects.select_related(
            "subtopic__topic__subject__exam"
        ).get(id=concept_id)
        exam_type = concept.subtopic.topic.subject.exam.exam_type

        if not concept.ai_meta:
            return

        questions_json = generate_questions_from_meta(
            concept.ai_meta,
            concept,
            exam_type=exam_type
        )

        for item in questions_json:
            Question.objects.get_or_create(
                qid=item["question_id"],
                defaults={
                    "question_title": item["question_title"],
                    "concept": concept,
                    "question": item["question"],
                    "option_a": item["options"]["A"],
                    "option_b": item["options"]["B"],
                    "option_c": item["options"]["C"],
                    "option_d": item["options"]["D"],
                    "correct_option": item["answer"],
                }
            )

    except Exception as e:
        print("Question thread error:", e)