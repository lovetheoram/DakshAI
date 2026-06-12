

import json
import uuid
from django.conf import settings
from django.db import transaction
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import Question, SubQuestion, QuizSession,QuizAnswer
from .serializers import QuestionSerializer
from django.utils import timezone
from django.db import transaction
from django.utils import timezone
from .models import QuizSession, QuizAnswer, Question, SubQuestion
from syllabus.models import Concept
from progress.services import ProgressService
import uuid, random
from langchain_google_genai import ChatGoogleGenerativeAI
import json


def build_single_question_prompt(concept):
    return f"""
You are an API, not a chatbot.

Generate EXACTLY ONE exam-grade JEE MCQ.
Output ONLY valid JSON.
No markdown. No explanations. Stop after output.

JSON FORMAT:
{{
  "header": "",
  "question_title": "",
  "question": "",
  "options": {{ "A":"", "B":"", "C":"", "D":"" }},
  "answer": "A",
  "explanation": "",
  "sub_questions": [
    {{
      "type": "comfort",
      "question": "",
      "options": {{ "A":"", "B":"", "C":"", "D":"" }},
      "answer": "A"
    }},
    {{
      "type": "grounding",
      "question": "",
      "options": {{ "A":"", "B":"", "C":"", "D":"" }},
      "answer": "A"
    }},
    {{
      "type": "precursor",
      "question": "",
      "options": {{ "A":"", "B":"", "C":"", "D":"" }},
      "answer": "A"
    }}
  ]
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

        session = QuizSession.objects.create(
            user=user,
            total_questions=len(questions)
        )
        session.questions.set(questions)

        return session, questions
    



    

    # @staticmethod
    # def generate_ai_questions_stream(concept, num):
    #     llm = ChatGoogleGenerativeAI(
    #         model="gemini-2.5-flash",
    #         temperature=0.3,
    #         api_key=settings.GEMINI_API_KEY
    #     )

        
    #     # prompt = f"""
    #     #     You are generating exam-grade MCQs.

    #     #     Generate EXACTLY {num} MCQs as a JSON ARRAY.
    #     #     Output MUST be valid JSON. No markdown. No extra text.

    #     #     HARD RULES:
    #     #     - Use ONLY standard math symbols: π √ / ^ ( )
    #     #     - DO NOT use LaTeX, \\frac, \\sqrt, or words like "pi", "root"
    #     #     - All math must be human-readable plain text
    #     #     Example: π/6√3 , (x^2 + 1)/(x - 1)

    #     #     - Each question must test ONE clear concept
    #     #     - Difficulty: JEE Main → JEE Advanced 
    #     #     - No vague or opinion-based questions
    #     #     - Exactly ONE correct option

    #     #     JSON FORMAT (STRICT):

    #     #     [
    #     #     {{
    #     #         "header": "",
    #     #         "question_title": "",
    #     #         "question": "",
    #     #         "options": {{ "A":"", "B":"", "C":"", "D":"" }},
    #     #         "answer": "A",
    #     #         "explanation": "",
    #     #         "sub_questions": [
    #     #         {{
    #     #             "type": "comfort",
    #     #             "question": "",
    #     #             "options": {{ "A":"", "B":"", "C":"", "D":"" }},
    #     #             "answer": "A"
    #     #         }}
    #     #         ]
    #     #     }}
    #     #     ]

    #     #     CONTENT RULES:
    #     #     - Options must be clean, complete, readable
    #     #     - No broken symbols, no line breaks inside options
            

    #     #     CONCEPT:
    #     #     {concept.name}

    #     #     CONTEXT:
    #     #     {concept.description or "N/A"}
    #     #     """
    #     prompt = f"""
    #         You are generating exam-grade JEE MCQs with learning scaffolding.

    #         Generate EXACTLY {num} MCQs as a JSON ARRAY.
    #         Output MUST be valid JSON ONLY. No markdown. No extra text.

    #         ABSOLUTE MATH RULES:
    #         - Use ONLY these symbols: π √ / ^ ( )
    #         - DO NOT use LaTeX, backslashes, or words like pi, sqrt, power
    #         - All math must be plain readable text
    #         Examples: π/6√3 , (x^2+1)/(x-1)

    #         QUESTION RULES:
    #         - One clear concept per question
    #         - Difficulty: JEE Main → JEE Advanced
    #         - Exactly ONE correct option
    #         - Options must be clean, complete, readable
    #         - No broken symbols or line breaks inside options

    #         SCAFFOLDING RULE (MANDATORY):
    #         Each question MUST include EXACTLY 3 sub-questions:

    #         (A) comfort:
    #         - No calculation
    #         - Recall formula / identity / definition

    #         (B) grounding:
    #         - ONE simple numeric operation
    #         - Same concept
    #         - No new formulas

    #         (C) precursor:
    #         - Compute the SAME intermediate result used in the final step
    #         - Do NOT compute the final answer
    #         - After this, only ONE obvious step remains

    #         If (C) is solved, the main question must feel obvious.

    #         STRICT JSON FORMAT:

    #         [
    #         {{
    #             "header": "",
    #             "question_title": "",
    #             "question": "",
    #             "options": {{ "A":"", "B":"", "C":"", "D":"" }},
    #             "answer": "A",
    #             "explanation": "",
    #             "sub_questions": [
    #             {{
    #                 "type": "comfort",
    #                 "question": "",
    #                 "options": {{ "A":"", "B":"", "C":"", "D":"" }},
    #                 "answer": "A"
    #             }},
    #             {{
    #                 "type": "grounding",
    #                 "question": "",
    #                 "options": {{ "A":"", "B":"", "C":"", "D":"" }},
    #                 "answer": "A"
    #             }},
    #             {{
    #                 "type": "precursor",
    #                 "question": "",
    #                 "options": {{ "A":"", "B":"", "C":"", "D":"" }},
    #                 "answer": "A"
    #             }}
    #             ]
    #         }}
    #         ]

    #         CONCEPT:
    #         {concept.name}

    #         CONTEXT:
    #         {concept.description or "N/A"}
    #         """

    #     full_text = ""

    #     for chunk in llm.stream(prompt):
    #         text = getattr(chunk, "content", "")
    #         if text:
    #             full_text += text
    #             yield {
    #                 "type": "chunk",
    #                 "text": text
    #             }

    #     # FINAL EVENT
    #     yield {
    #         "type": "complete",
    #         "full_text": full_text
    #     }

    

    
    # @staticmethod
    # def start_ai_quiz_stream(user, concept, num):
    #     collected_text = ""

    #     for event in QuizService.generate_ai_questions_stream(concept, num):
    #         if event["type"] == "chunk":
    #             collected_text += event["text"]
    #             yield f"data: {json.dumps(event)}\n\n".encode("utf-8")

    #     # Parse AI JSON
    #     try:
    #         collected_text = collected_text.replace("```json", "").replace("```", "").strip()
    #         ai_questions = json.loads(collected_text)
    #     except Exception:
    #         yield f"data: {json.dumps({'type': 'error','message':'Invalid JSON'})}\n\n".encode("utf-8")
    #         return

    #     questions = []

    #     for q in ai_questions:
    #         print(q)
    #         question = Question.objects.create(
    #             qid=f"AI-{uuid.uuid4().hex[:8]}",
    #             header=q.get("header", ""),
    #             question_title=q.get("question_title", ""),
    #             concept=concept,
    #             question=q.get("question", ""),
    #             option_a=q["options"].get("A", ""),
    #             option_b=q["options"].get("B", ""),
    #             option_c=q["options"].get("C", ""),
    #             option_d=q["options"].get("D", ""),
    #             correct_option=q.get("answer", "A"),
    #             explanation=q.get("explanation", ""),
    #             source="NEW"
    #         )

    #         questions.append(question)

        
    #         sub_questions = q.get("sub_questions", [])

    #         if isinstance(sub_questions, list):
    #             for sq in sub_questions:
    #                 sq_options = sq.get("options", {})

    #                 SubQuestion.objects.create(
    #                     parent=question,
    #                     concept=concept,
    #                     type=sq.get("type"),  # comfort / grounding / precursor
    #                     question=sq.get("question", ""),
    #                     option_a=sq_options.get("A", ""),
    #                     option_b=sq_options.get("B", ""),
    #                     option_c=sq_options.get("C", ""),
    #                     option_d=sq_options.get("D", ""),
    #                     correct_option=sq.get("answer", "A")
    #                 )

    #         question.refresh_from_db()

    #         yield f"data: {json.dumps({
    #             'type': 'question',
    #             'question': QuestionSerializer(question).data
    #         })}\n\n".encode("utf-8")

    #     session = QuizSession.objects.create(user=user, total_questions=len(questions))
    #     session.questions.set(questions)

    #     yield f"data: {json.dumps({
    #         'type': 'done',
    #         'session_id': session.id,
    #         'total_questions': len(questions)
    #     })}\n\n".encode("utf-8")


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

                try:
                    question_json = json.loads(buffer)
                except Exception:
                    continue  # JSON not complete yet

                yield question_json
                break  # move to next question



    @staticmethod
    def start_ai_quiz_stream(user, concept, num):
        questions = []

        try:
            for q in QuizService.generate_ai_questions_stream(concept, num):

                question = Question.objects.create(
                    qid=f"AI-{uuid.uuid4().hex[:8]}",
                    header=q.get("header", ""),
                    question_title=q.get("question_title", ""),
                    question=q.get("question", ""),
                    option_a=q["options"].get("A", ""),
                    option_b=q["options"].get("B", ""),
                    option_c=q["options"].get("C", ""),
                    option_d=q["options"].get("D", ""),
                    correct_option=q.get("answer", "A"),
                    explanation=q.get("explanation", ""),
                    concept=concept,
                    source="NEW"
                )

                questions.append(question)

                sub_questions = []
                for sq in q.get("sub_questions", []):
                    sub_questions.append(SubQuestion(
                        parent=question,
                        concept=concept,
                        type=sq.get("type"),
                        question=sq.get("question", ""),
                        option_a=sq["options"].get("A", ""),
                        option_b=sq["options"].get("B", ""),
                        option_c=sq["options"].get("C", ""),
                        option_d=sq["options"].get("D", ""),
                        correct_option=sq.get("answer", "A")
                    ))

                if sub_questions:
                    SubQuestion.objects.bulk_create(sub_questions)

                yield f"data: {json.dumps({
                    'type': 'question',
                    'question': QuestionSerializer(question).data
                })}\n\n".encode("utf-8")

        except GeneratorExit:
            return  # client disconnected safely

        session = QuizSession.objects.create(
            user=user,
            total_questions=len(questions)
        )
        session.questions.set(questions)

        yield f"data: {json.dumps({
            'type': 'done',
            'session_id': session.id,
            'total_questions': len(questions)
        })}\n\n".encode("utf-8")



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
            q = session.questions.get(qid=ans["question_id"])
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

        session.score = correct_main / session.total_questions
        session.completed_at = timezone.now()
        session.duration_seconds = duration_seconds
        session.save()

        ProgressService.update_progress_with_session(user, session)
        return session




 