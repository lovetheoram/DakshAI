"""
Generic syllabus loader — works with any exam type.

Usage (from Django shell):
    from syllabus.load_syllabus import load_syllabus
    load_syllabus("syllabus/jee_syllabus1.json")
    load_syllabus("syllabus/neet_syllabus.json")
    load_syllabus("syllabus/class6_syllabus.json")

Expected JSON format:
{
    "exam": {
        "name": "JEE",
        "description": "Joint Entrance Examination",
        "exam_type": "jee",
        "subjects": [
            {
                "name": "Physics",
                "topics": [
                    {
                        "name": "Mechanics",
                        "subtopics": [
                            {
                                "name": "Kinematics",
                                "concepts": [
                                    {
                                        "name": "Projectile Motion",
                                        "description": "...",
                                        "estimated_time": "...",
                                        "resources": "..."
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
}
"""

import json
import sys
from django.db import transaction
from syllabus.models import Exam, Subject, Topic, Subtopic, Concept


@transaction.atomic
def load_syllabus(json_path):
    """Load any exam syllabus from a JSON file."""

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    exam_data = data["exam"]

    # -------------------------
    # Exam
    # -------------------------
    exam, created = Exam.objects.get_or_create(
        name=exam_data["name"],
        defaults={
            "description": exam_data.get("description", ""),
        }
    )

    # Update fields if exam already existed
    if not created:
        if exam_data.get("description"):
            exam.description = exam_data["description"]
        exam.save()

    # -------------------------
    # Subjects
    # -------------------------
    for s_index, subj_data in enumerate(exam_data.get("subjects", [])):
        subject, _ = Subject.objects.get_or_create(
            exam=exam,
            name=subj_data["name"],
            defaults={
                "order": s_index
            }
        )

        # -------------------------
        # Topics
        # -------------------------
        for t_index, topic_data in enumerate(subj_data.get("topics", [])):
            topic, _ = Topic.objects.get_or_create(
                subject=subject,
                name=topic_data["name"],
                defaults={
                    "order": t_index
                }
            )

            # -------------------------
            # Subtopics
            # -------------------------
            for st_index, subtopic_data in enumerate(topic_data.get("subtopics", [])):
                subtopic, _ = Subtopic.objects.get_or_create(
                    topic=topic,
                    name=subtopic_data["name"],
                    defaults={
                        "order": st_index
                    }
                )

                # -------------------------
                # Concepts
                # -------------------------
                for c_index, concept_data in enumerate(subtopic_data.get("concepts", [])):

                    ai_meta = {
                        "estimated_time": concept_data.get("estimated_time"),
                        "resources": concept_data.get("resources"),
                    }

                    Concept.objects.get_or_create(
                        subtopic=subtopic,
                        name=concept_data["name"],
                        defaults={
                            "description": concept_data.get("description", ""),
                            "order": c_index,
                            "ai_meta": ai_meta,
                        }
                    )

    print(f"Syllabus '{exam.name}' loaded successfully!")
    return exam


# If run directly, accept path from command line or use default
if __name__ == "__main__" or "load_syllabus" not in dir():
    path = sys.argv[1] if len(sys.argv) > 1 else "syllabus/placement_syllabus.json"
    load_syllabus(path)
