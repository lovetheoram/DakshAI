from syllabus.models import Concept
from quiz.models import Question
from .service import generate_formula_meta, generate_questions_from_meta


def generate_meta_task(concept_id, chapter):
    try:
        concept = Concept.objects.select_related(
            "subtopic__topic__subject__exam"
        ).get(id=concept_id)
        exam_type = concept.subtopic.topic.subject.exam.exam_type

        if not concept.ai_meta or concept.ai_meta == {}:
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

        if not concept.ai_meta or concept.ai_meta == {}:
            chapter = concept.subtopic.topic.name if concept.subtopic and concept.subtopic.topic else "General"
            meta_json = generate_formula_meta(
                concept.name,
                concept.description,
                chapter,
                exam_type=exam_type
            )
            concept.ai_meta = meta_json
            concept.save(update_fields=["ai_meta"])

        if concept.ai_meta:
            questions_json = generate_questions_from_meta(
                concept.ai_meta,
                concept,
                exam_type=exam_type
            )

        for idx, item in enumerate(questions_json):
            qid = item.get("question_id") or f"C{concept.id}-Q{idx+1}"
            if not qid.startswith(f"C{concept.id}-"):
                qid = f"C{concept.id}-{qid}"

            Question.objects.update_or_create(
                qid=qid,
                defaults={
                    "question_title": item.get("question_title", "Concept Practice"),
                    "concept": concept,
                    "question": item.get("question", ""),
                    "option_a": item.get("options", {}).get("A", ""),
                    "option_b": item.get("options", {}).get("B", ""),
                    "option_c": item.get("options", {}).get("C", ""),
                    "option_d": item.get("options", {}).get("D", ""),
                    "correct_option": item.get("answer", "A"),
                    "mode": "LLM",
                    "source": "LLM",
                }
            )

    except Exception as e:
        print("Question thread error:", e)