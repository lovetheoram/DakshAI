import json
from collections import defaultdict

def find_duplicate_concepts(json_path):
    with open(json_path, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    concept_map = defaultdict(int)

    for item in data:
        concept_map[item["concept"].strip()] += 1
        for sq in item.get("sub_questions", []):
            concept_map[sq["concept"].strip()] += 1

    duplicates = {k: v for k, v in concept_map.items() if v > 1}

    if not duplicates:
        print("✅ No duplicate concepts found")
        return

    print("❌ Duplicate concepts:")
    for k, v in duplicates.items():
        print(f"{k} → {v}")


# USAGE
find_duplicate_concepts("syllabus/jee_syllabus1.json")
# exec(open("quiz/load_jee_questions1.py").read())
# exec(open("syllabus/concept_duplicate_check.py").read())
# exec(open("syllabus/load_jee_syllabus.py").read())