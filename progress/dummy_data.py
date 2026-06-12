import random
from datetime import timedelta
from django.utils import timezone
from progress.models import ConceptProgress, SubtopicProgress, Concept, Subtopic, User

# pick the user for whom you want to populate
user = User.objects.get(username="sunny")  # replace with actual username

# set 20 days ago
last_practice_date = timezone.now() - timedelta(days=20)

# iterate over all concepts
for concept in Concept.objects.all():
    cp, created = ConceptProgress.objects.get_or_create(user=user, concept=concept)
    
    # assign random scores
    cp.exam_readiness = round(random.uniform(0.4, 1.0), 2)         # example 0.4 to 1.0
    cp.chapter_understanding = round(random.uniform(0.4, 1.0), 2)
    cp.last_practiced = last_practice_date
    cp.save()

# iterate over all subtopics
for subtopic in Subtopic.objects.all():
    sp, created = SubtopicProgress.objects.get_or_create(user=user, subtopic=subtopic)
    
    # efficiency could be average of all concepts under this subtopic
    concepts = Concept.objects.filter(subtopic=subtopic)
    if concepts.exists():
        exam_avg = sum(ConceptProgress.objects.get(user=user, concept=c).exam_readiness for c in concepts) / len(concepts)
        chapter_avg = sum(ConceptProgress.objects.get(user=user, concept=c).chapter_understanding for c in concepts) / len(concepts)
        sp.raw_efficiency = round((exam_avg + chapter_avg)/2, 2)
        sp.efficiency = sp.raw_efficiency
    else:
        sp.raw_efficiency = sp.efficiency = 0.0

    sp.save()

print("All concepts and subtopics populated with random values.")
