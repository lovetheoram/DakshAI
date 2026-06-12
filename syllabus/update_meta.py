import json
from quiz.models import Concept


# ------------------------------
# CONFIG — edit manually
# ------------------------------
LOAD_CONFIG = [
    {
        "concept_name": "Hydrogen bonding",
        "json_path": "syllabus/meta_data/Hydrogen bonding.json"
    },
    {
        "concept_name": "Molecular orbital theory",
        "json_path": "syllabus/meta_data/Molecular orbital theory.json"
    },
    {
        "concept_name": "Valence bond theory",
        "json_path": "syllabus/meta_data/Valence bond theory.json"
    },
]
# ------------------------------


def update_ai_meta(concept_name, json_path):
    try:
        concept = Concept.objects.get(name=concept_name)
    except Concept.DoesNotExist:
        print(f"❌ Concept not found: {concept_name}")
        return

    try:
        with open(json_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading {json_path}: {e}")
        return

    concept.ai_meta = data
    concept.save()

    print(f"✅ Updated: {concept_name}")


print("🚀 Starting AI meta update...\n")

for entry in LOAD_CONFIG:
    update_ai_meta(
        concept_name=entry["concept_name"],
        json_path=entry["json_path"]
    )

print("\n🎯 Done.")
