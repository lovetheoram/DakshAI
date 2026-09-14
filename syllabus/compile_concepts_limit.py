import os
import sys
import django

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nimides.settings")
django.setup()

from django.db import transaction
from syllabus.models import Subtopic, Concept, PYQ
from quiz.models import Question


@transaction.atomic
def compile_and_limit_concepts(max_concepts_per_subtopic=6):
    print(f"[AUDIT] Compiling concepts (Max {max_concepts_per_subtopic} concepts per subtopic)...")
    subtopics = Subtopic.objects.prefetch_related("concepts").all()

    modified_count = 0
    merged_concepts_count = 0

    for st in subtopics:
        concepts = list(st.concepts.all().order_by("order", "id"))
        if len(concepts) > max_concepts_per_subtopic:
            print(f"[CONSOLIDATING] Subtopic '{st.topic.subject.name} -> {st.name}' has {len(concepts)} concepts. Merging down to {max_concepts_per_subtopic}...")
            
            # Keep top (max_concepts_per_subtopic - 1) primary concepts
            keep_concepts = concepts[:max_concepts_per_subtopic - 1]
            overflow_concepts = concepts[max_concepts_per_subtopic - 1:]

            # Consolidation concept
            target_concept = keep_concepts[-1]
            
            # Merge overflow concepts into target_concept
            for overflow in overflow_concepts:
                if overflow.id == target_concept.id:
                    continue
                
                # Re-assign PYQs to target_concept
                PYQ.objects.filter(concept=overflow).update(concept=target_concept)
                
                # Re-assign Quiz Questions to target_concept
                Question.objects.filter(concept=overflow).update(concept=target_concept)
                
                # Merge description
                if overflow.description and overflow.name not in target_concept.name:
                    target_concept.description += f"\n\n- Key Focus ({overflow.name}): {overflow.description}"
                
                # Delete overflow concept
                overflow.delete()
                merged_concepts_count += 1

            target_concept.save()
            modified_count += 1

    print(f"[SUCCESS] Concept Compilation Complete!")
    print(f"[STATS] Merged {merged_concepts_count} overflow concepts across {modified_count} subtopics.")
    print(f"[LIMIT ENFORCED] Every subtopic now has AT MOST {max_concepts_per_subtopic} concepts.")


compile_and_limit_concepts(max_concepts_per_subtopic=6)
