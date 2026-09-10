"""
DakshAI Stage 5: Database Ingestion Loader for State PCS & Ghatnachakra PYQs
-------------------------------------------------------------------------
Loads structured JSON (dakshai_pcs_history.json) into Django database models:
Exam (pcs) -> Subject -> Topic -> Subtopic -> Concept -> PYQ

Usage (from Django root or script):
    python syllabus/load_pcs_syllabus.py
"""

import os
import sys
import json
import django

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from django.db import transaction

# Setup Django environment if run as standalone script
if __name__ == "__main__":
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nimides.settings")
    django.setup()
from syllabus.models import Exam, Subject, Topic, Subtopic, Concept, PYQ


@transaction.atomic
def load_pcs_syllabus(json_path=None):
    master_data = []

    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            master_data = data if isinstance(data, list) else [data]
    else:
        master_json = os.path.join(os.path.dirname(__file__), "dakshai_pcs_history.json")
        if os.path.exists(master_json):
            with open(master_json, "r", encoding="utf-8") as f:
                master_data = json.load(f)
        else:
            chunks_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scratch", "pcs_chunks"))
            if os.path.exists(chunks_dir):
                chunk_files = sorted([os.path.join(chunks_dir, f) for f in os.listdir(chunks_dir) if f.endswith(".json")])
                for cf in chunk_files:
                    with open(cf, "r", encoding="utf-8") as f:
                        c_data = json.load(f)
                        master_data.append(c_data)

    if not master_data:
        raise FileNotFoundError("No syllabus JSON data or chunk files found to load.")

    print("📥 Loading State PCS Exam syllabus & PYQs into Django database...")

    # 1. Create or retrieve Exam
    exam, created = Exam.objects.get_or_create(
        name="State PCS",
        defaults={
            "exam_type": "pcs",
            "description": "State Public Service Commission examinations (BPSC, UPPCS, MPPSC, etc.)"
        }
    )
    if not created and exam.exam_type != "pcs":
        exam.exam_type = "pcs"
        exam.save()

    # 2. Subject: Indian History
    subject, _ = Subject.objects.get_or_create(
        exam=exam,
        name="Indian History",
        defaults={"order": 0}
    )

    # 3. Topic: Ancient History
    topic, _ = Topic.objects.get_or_create(
        subject=subject,
        name="Ancient History",
        defaults={"order": 0}
    )

    total_concepts = 0
    total_pyqs = 0

    # Process chapters
    for sub_idx, chapter in enumerate(master_data):
        chapter_name = chapter.get("chapter_name", f"Chapter {sub_idx + 1}")
        
        # Subtopic (Chapter)
        subtopic, _ = Subtopic.objects.get_or_create(
            topic=topic,
            name=chapter_name,
            defaults={"order": sub_idx}
        )

        for c_idx, concept_data in enumerate(chapter.get("concepts", [])):
            c_name = concept_data.get("concept_name", chapter_name)
            c_desc = concept_data.get("concept_description", "")

            ai_meta = {
                "start_page": chapter.get("start_page"),
                "end_page": chapter.get("end_page"),
                "extracted_source": "Ghatnachakra Indian History 2025"
            }

            concept, _ = Concept.objects.get_or_create(
                subtopic=subtopic,
                name=c_name,
                defaults={
                    "description": c_desc,
                    "order": c_idx,
                    "ai_meta": ai_meta
                }
            )

            # Update description if empty
            if not concept.description and c_desc:
                concept.description = c_desc
                concept.save()

            total_concepts += 1

            # PYQs
            for p_idx, pyq_data in enumerate(concept_data.get("pyqs", [])):
                q_text = pyq_data.get("question_text", "").strip()
                if not q_text:
                    continue

                content_hash = pyq_data.get("content_hash")
                
                # Check for existing PYQ by content_hash or exact question
                existing_pyq = PYQ.objects.filter(content_hash=content_hash).first() if content_hash else None
                if not existing_pyq:
                    existing_pyq = PYQ.objects.filter(concept=concept, question_text=q_text).first()

                pyq_kwargs = {
                    "question_text": q_text,
                    "options": pyq_data.get("options", []),
                    "correct_answer": pyq_data.get("correct_answer", ""),
                    "explanation": pyq_data.get("explanation", ""),
                    "exam_source": pyq_data.get("exam_source", "State PCS"),
                    "exam_year": pyq_data.get("exam_year"),
                    "source_book": pyq_data.get("source_book", "Ghatnachakra Indian History 2025"),
                    "source_page": pyq_data.get("source_page"),
                    "source_question_number": pyq_data.get("source_question_number", ""),
                    "experiential_summary": pyq_data.get("experiential_summary", {}),
                    "extraction_confidence": pyq_data.get("extraction_confidence", 1.0),
                    "needs_review": pyq_data.get("needs_review", False),
                    "content_hash": content_hash,
                    "order": p_idx,
                }

                if existing_pyq:
                    for k, v in pyq_kwargs.items():
                        setattr(existing_pyq, k, v)
                    existing_pyq.save()
                else:
                    PYQ.objects.create(concept=concept, **pyq_kwargs)

                total_pyqs += 1

    print(f"✨ Successfully loaded State PCS Syllabus: {total_concepts} Concepts and {total_pyqs} PYQs!")
    return exam


if __name__ == "__main__":
    load_pcs_syllabus()
