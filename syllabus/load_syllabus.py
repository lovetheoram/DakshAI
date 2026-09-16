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
    """Load any exam syllabus from a JSON file, including parent/child branches."""

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    exam_data = data["exam"]

    # -------------------------
    # Parent Exam
    # -------------------------
    exam_type = exam_data.get("exam_type") or exam_data.get("code") or ("pcs" if "pcs" in json_path.lower() else "jee")
    exam_code = exam_data.get("code") or exam_data["name"].upper().replace(" ", "_")

    # Look up by code first, then name
    exam = Exam.objects.filter(code__iexact=exam_code, parent_exam__isnull=True).first()
    if not exam:
        exam = Exam.objects.filter(name__iexact=exam_data["name"], parent_exam__isnull=True).first()

    if not exam:
        exam = Exam.objects.create(
            name=exam_data["name"],
            code=exam_code,
            description=exam_data.get("description", ""),
            exam_type=exam_type,
        )
    else:
        if exam_data.get("description"):
            exam.description = exam_data["description"]
        if exam_type:
            exam.exam_type = exam_type
        if exam_code:
            exam.code = exam_code
        exam.save()

    # -------------------------
    # Child Branches (if any)
    # -------------------------
    branch_map = {}
    branches_list = exam_data.get("branches", [])
    if not branches_list and exam_type == "pcs":
        branches_list = [
            {"name": "BPSC", "code": "BPSC", "description": "Bihar Public Service Commission"},
            {"name": "UPPSC", "code": "UPPSC", "description": "Uttar Pradesh Public Service Commission"},
            {"name": "WBPSC", "code": "WBPSC", "description": "West Bengal Public Service Commission"},
            {"name": "MPPSC", "code": "MPPSC", "description": "Madhya Pradesh Public Service Commission"},
            {"name": "RAS", "code": "RAS", "description": "Rajasthan Administrative Service (RPSC)"},
        ]

    for branch_info in branches_list:
        b_code = branch_info.get("code", branch_info["name"])
        child_exam, _ = Exam.objects.get_or_create(
            code__iexact=b_code,
            parent_exam=exam,
            defaults={
                "name": branch_info["name"],
                "code": b_code,
                "description": branch_info.get("description", ""),
                "exam_type": exam.exam_type,
                "parent_exam": exam,
            }
        )
        child_exam.parent_exam = exam
        child_exam.exam_type = exam.exam_type
        if branch_info.get("code"):
            child_exam.code = branch_info["code"]
        if branch_info.get("description"):
            child_exam.description = branch_info["description"]
        child_exam.save()
        branch_map[b_code.upper()] = child_exam

    # -------------------------
    # Subjects
    # -------------------------
    scope_to_branch = {
        "bihar": "BPSC",
        "uttar_pradesh": "UPPSC",
        "west_bengal": "WBPSC",
        "mppsc": "MPPSC",
        "ras": "RAS",
    }

    # Pre-fetch existing subjects/topics/subtopics for caching
    subject_cache = {(s.exam_id, s.name): s for s in Subject.objects.filter(exam__in=[exam] + list(branch_map.values()))}
    topic_cache = {(t.subject_id, t.name): t for t in Topic.objects.filter(subject__in=subject_cache.values())}
    subtopic_cache = {(st.topic_id, st.name): st for st in Subtopic.objects.filter(topic__in=topic_cache.values())}

    for s_index, subj_data in enumerate(exam_data.get("subjects", [])):
        branch_code = subj_data.get("branch", "")
        scope = subj_data.get("scope", "")

        if not branch_code and scope in scope_to_branch:
            branch_code = scope_to_branch[scope]

        if branch_code and branch_code.upper() in branch_map:
            target_exam = branch_map[branch_code.upper()]
        else:
            target_exam = exam

        s_key = (target_exam.id, subj_data["name"])
        if s_key in subject_cache:
            subject = subject_cache[s_key]
        else:
            subject = Subject.objects.create(exam=target_exam, name=subj_data["name"], order=s_index)
            subject_cache[s_key] = subject

        # -------------------------
        # Topics
        # -------------------------
        for t_index, topic_data in enumerate(subj_data.get("topics", [])):
            t_key = (subject.id, topic_data["name"])
            if t_key in topic_cache:
                topic = topic_cache[t_key]
            else:
                topic = Topic.objects.create(subject=subject, name=topic_data["name"], order=t_index)
                topic_cache[t_key] = topic

            # -------------------------
            # Subtopics
            # -------------------------
            for st_index, subtopic_data in enumerate(topic_data.get("subtopics", [])):
                st_key = (topic.id, subtopic_data["name"])
                if st_key in subtopic_cache:
                    subtopic = subtopic_cache[st_key]
                else:
                    subtopic = Subtopic.objects.create(topic=topic, name=subtopic_data["name"], order=st_index)
                    subtopic_cache[st_key] = subtopic

                # -------------------------
                # Concepts
                # -------------------------
                concepts_to_create = []
                for c_index, concept_data in enumerate(subtopic_data.get("concepts", [])):
                    if isinstance(concept_data, dict):
                        c_name = concept_data["name"]
                        c_desc = concept_data.get("description", "")
                    elif isinstance(concept_data, str):
                        c_name = concept_data
                        c_desc = f"{c_name} covering key concepts and analytical questions."
                    else:
                        continue

                    concepts_to_create.append(
                        Concept(
                            subtopic=subtopic,
                            name=c_name,
                            description=c_desc,
                            order=c_index,
                            ai_meta={}
                        )
                    )

                if concepts_to_create:
                    Concept.objects.bulk_create(concepts_to_create, ignore_conflicts=True)

    from django.core.cache import cache
    cache.clear()

    print(f"Syllabus '{exam.name}' loaded successfully!")
    return exam


# If run directly, accept path from command line or use default
if __name__ == "__main__" or "load_syllabus" not in dir():
    path = sys.argv[1] if len(sys.argv) > 1 else "syllabus/placement_syllabus.json"
    load_syllabus(path)
