import json
import uuid
import random
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import Question, SubQuestion, QuizSession, QuizAnswer
from .serializers import QuestionSerializer
from syllabus.models import Concept
from progress.services import ProgressService

# Behavioral event tracking
try:
    from behavior.services.event_processor import EventProcessor as _EventProcessor
except Exception:
    _EventProcessor = None


def build_single_question_prompt(concept):
    return f"""
You are an API, not a chatbot.

Generate EXACTLY ONE exam-grade MCQ.
Output ONLY valid JSON.
No markdown. No explanations. Stop after output.

JSON FORMAT:
{{
  "header": "",
  "question_title": "",
  "question": "",
  "options": {{ "A":"", "B":"", "C":"", "D":"" }},
  "answer": "A",
  "explanation": ""
}}

ABSOLUTE RULES:
- Use only: π √ / ^ ( )
- No LaTeX, no backslashes, no words like pi or sqrt
- One clear concept
- Exactly ONE correct option

CONCEPT: {concept.name}
CONTEXT: {concept.description or "N/A"}
"""


class QuizService:

    @staticmethod
    @transaction.atomic
    def start_pyqs_quiz(user, concept, num):
        questions = list(
            Question.objects
            .filter(concept=concept, source="PYQS")
            .prefetch_related("sub_questions")[:num]
        )

        if len(questions) < num:
            from syllabus.models import PYQ
            pyqs = PYQ.objects.filter(concept=concept)[:num]
            for p_idx, pyq in enumerate(pyqs):
                opts = pyq.options if isinstance(pyq.options, list) else []
                q_id = f"PYQ-C{concept.id}-{pyq.id}"
                q_obj, _ = Question.objects.get_or_create(
                    qid=q_id,
                    defaults={
                        "concept": concept,
                        "question_title": f"{pyq.exam_source or 'State PCS'} PYQ",
                        "question": pyq.question_text,
                        "option_a": opts[0] if len(opts) > 0 else "Statement 1",
                        "option_b": opts[1] if len(opts) > 1 else "Statement 2",
                        "option_c": opts[2] if len(opts) > 2 else "Statement 3",
                        "option_d": opts[3] if len(opts) > 3 else "Statement 4",
                        "correct_option": pyq.correct_answer or "A",
                        "explanation": pyq.explanation or "Ghatnachakra verified past year solution.",
                        "mode": "PYQS",
                        "source": "PYQS",
                    }
                )
                if q_obj not in questions:
                    questions.append(q_obj)

        session = QuizSession.objects.create(
            user=user,
            total_questions=len(questions[:num]),
            mode="PYQS"
        )
        session.questions.set(questions[:num])

        return session, questions[:num]

    @staticmethod
    @transaction.atomic
    def start_full_exam_quiz(user, concept, num):
        questions = list(
            Question.objects
            .filter(concept=concept, source="PYQS")
            .prefetch_related("sub_questions")[:num]
        )

        if len(questions) < num:
            from syllabus.models import PYQ
            pyqs = PYQ.objects.filter(concept=concept)[:num]
            for p_idx, pyq in enumerate(pyqs):
                opts = pyq.options if isinstance(pyq.options, list) else []
                q_id = f"PYQ-C{concept.id}-{pyq.id}"
                q_obj, _ = Question.objects.get_or_create(
                    qid=q_id,
                    defaults={
                        "concept": concept,
                        "question_title": f"{pyq.exam_source or 'State PCS'} PYQ",
                        "question": pyq.question_text,
                        "option_a": opts[0] if len(opts) > 0 else "Statement 1",
                        "option_b": opts[1] if len(opts) > 1 else "Statement 2",
                        "option_c": opts[2] if len(opts) > 2 else "Statement 3",
                        "option_d": opts[3] if len(opts) > 3 else "Statement 4",
                        "correct_option": pyq.correct_answer or "A",
                        "explanation": pyq.explanation or "Ghatnachakra verified past year solution.",
                        "mode": "PYQS",
                        "source": "PYQS",
                    }
                )
                if q_obj not in questions:
                    questions.append(q_obj)

        session = QuizSession.objects.create(
            user=user,
            total_questions=len(questions[:num]),
            mode="FULL_EXAM"
        )
        session.questions.set(questions[:num])

        return session, questions[:num]

    @staticmethod
    def generate_ai_questions_stream(concept, num):
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3,
            api_key=settings.GEMINI_API_KEY
        )

        for _ in range(num):
            prompt = build_single_question_prompt(concept)
            buffer = ""

            for chunk in llm.stream(prompt):
                text = getattr(chunk, "content", "")
                if not text:
                    continue

                buffer += text
                cleaned = buffer.replace("```json", "").replace("```", "").strip()

                try:
                    question_json = json.loads(cleaned)
                    yield question_json
                    break
                except Exception:
                    continue

    @staticmethod
    def start_ai_quiz_stream(user, concept, num):
        questions = []

        try:
            for q in QuizService.generate_ai_questions_stream(concept, num):
                opts = q.get("options") if isinstance(q.get("options"), dict) else {}

                question = Question.objects.create(
                    qid=f"AI-{uuid.uuid4().hex[:8]}",
                    header=q.get("header", f"{concept.name} Practice"),
                    question_title=q.get("question_title", "AI Practice"),
                    question=q.get("question", ""),
                    option_a=opts.get("A", ""),
                    option_b=opts.get("B", ""),
                    option_c=opts.get("C", ""),
                    option_d=opts.get("D", ""),
                    correct_option=q.get("answer", "A"),
                    explanation=q.get("explanation", ""),
                    concept=concept,
                    source="NEW",
                    mode="LLM"
                )

                questions.append(question)

                q_data = json.dumps({
                    'type': 'question',
                    'question': QuestionSerializer(question).data
                })
                yield f"data: {q_data}\n\n".encode("utf-8")

        except GeneratorExit:
            return
        except Exception as err:
            err_data = json.dumps({'type': 'error', 'message': str(err)})
            yield f"data: {err_data}\n\n".encode("utf-8")
            return

        session = QuizSession.objects.create(
            user=user,
            total_questions=len(questions),
            mode="LLM"
        )
        session.questions.set(questions)

        done_data = json.dumps({
            'type': 'done',
            'session_id': session.id,
            'total_questions': len(questions)
        })
        yield f"data: {done_data}\n\n".encode("utf-8")

    @staticmethod
    @transaction.atomic
    def submit_quiz(user, session_id, answers_payload, duration_seconds=None):
        session = QuizSession.objects.select_for_update().get(
            id=session_id,
            user=user
        )

        if session.completed_at:
            raise ValueError("Quiz already submitted")

        QuizAnswer.objects.filter(session=session).delete()

        correct_main = 0
        answered = set()

        for ans in answers_payload:
            q_id = ans.get("question_id")
            q = session.questions.filter(qid=q_id).first()
            if not q:
                continue

            sq = None
            if ans.get("sub_question_type"):
                sq = SubQuestion.objects.filter(
                    parent=q,
                    type=ans["sub_question_type"]
                ).first()

            marked = ans["marked_option"]
            correct = sq.correct_option if sq else q.correct_option
            is_correct = marked == correct

            if not sq and q.qid not in answered:
                answered.add(q.qid)
                if is_correct:
                    correct_main += 1

            QuizAnswer.objects.create(
                session=session,
                question=q if not sq else None,
                sub_question=sq,
                marked_option=marked,
                is_correct=is_correct
            )

        session.score = correct_main / session.total_questions if session.total_questions > 0 else 0.0
        session.completed_at = timezone.now()
        session.duration_seconds = duration_seconds
        session.save()

        ProgressService.update_progress_with_session(user, session)

        if _EventProcessor:
            concept = session.questions.first().concept if session.questions.exists() else None
            concept_name = concept.name if concept else ""
            concept_id   = concept.id   if concept else None
            score_pct    = round(session.score * 100, 1)

            if session.score >= 0.60:
                _EventProcessor.log(user, "QUIZ_PASSED", {
                    "concept_id":   concept_id,
                    "concept_name": concept_name,
                    "score":        score_pct,
                })
            else:
                from behavior.models import UserBehaviorEvent
                prior_fails = UserBehaviorEvent.objects.filter(
                    user=user,
                    event_type__in=["QUIZ_FAILED", "QUIZ_FAILED_REPEAT"],
                    metadata__concept_id=concept_id
                ).count()
                evt = "QUIZ_FAILED_REPEAT" if prior_fails >= 2 else "QUIZ_FAILED"
                _EventProcessor.log(user, evt, {
                    "concept_id":    concept_id,
                    "concept_name":  concept_name,
                    "score":         score_pct,
                    "attempt_count": prior_fails + 1,
                })

        return session