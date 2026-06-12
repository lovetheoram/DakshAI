# import json
# from django.db import transaction
# from syllabus.models import Exam, Subject, Topic, Subtopic, Concept


# @transaction.atomic
# def load_jee_syllabus():
#     with open("syllabus/jee_syllabus.json", "r", encoding="utf-8") as f:
#         data = json.load(f)

#     exam_data = data["exam"]

#     # Create Exam
#     exam, _ = Exam.objects.get_or_create(
#         name=exam_data["name"]
#     )

#     for s_index, subj_data in enumerate(exam_data.get("subjects", [])):
#         subject, _ = Subject.objects.get_or_create(
#             exam=exam,
#             name=subj_data["name"],
#             defaults={
#                 "weightage": subj_data.get("weightage", 1.0),
#                 "order": subj_data.get("order", s_index),
#             }
#         )

#         for t_index, topic_data in enumerate(subj_data.get("topics", [])):
#             topic, _ = Topic.objects.get_or_create(
#                 subject=subject,
#                 name=topic_data["name"],
#                 defaults={
#                     "weightage": topic_data.get("weightage", 1.0),
#                     "order": topic_data.get("order", t_index),
#                 }
#             )

#             for st_index, subtopic_data in enumerate(topic_data.get("subtopics", [])):
#                 subtopic, _ = Subtopic.objects.get_or_create(
#                     topic=topic,
#                     name=subtopic_data["name"],
#                     defaults={
#                         "weightage": subtopic_data.get("weightage", 1.0),
#                         "order": subtopic_data.get("order", st_index),
#                     }
#                 )

#                 for c_index, concept_data in enumerate(subtopic_data.get("concepts", [])):

#                     # All non-model fields go safely inside ai_meta
#                     ai_meta = {
#                         "estimated_time": concept_data.get("estimated_time"),
#                         "resources": concept_data.get("resources"),
#                     }

#                     Concept.objects.get_or_create(
#                         subtopic=subtopic,
#                         name=concept_data["name"],
#                         defaults={
#                             "description": concept_data.get("description", ""),
#                             "weightage": concept_data.get("weightage", 1.0),
#                             "order": concept_data.get("order", c_index),
#                             "ai_meta": ai_meta
#                         }
#                     )

#     print("✅ JEE syllabus loaded successfully!")


# # Call the function
# load_jee_syllabus()



import json
from django.db import transaction
from syllabus.models import Exam, Subject, Topic, Subtopic, Concept


@transaction.atomic
def load_jee_syllabus():
    with open("syllabus/jee_syllabus1.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    exam_data = data["exam"]

    # -------------------------
    # Exam
    # -------------------------
    exam, _ = Exam.objects.get_or_create(
        name=exam_data["name"]
    )

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

    print("✅ JEE syllabus loaded successfully!")


# Run manually or via Django shell
load_jee_syllabus()
