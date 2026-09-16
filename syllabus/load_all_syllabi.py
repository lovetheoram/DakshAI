# syllabus/load_all_syllabi.py
"""
Script to load all 4 complete syllabus trees (NEET, State PCS, JEE Main, Placement Preparation).
Can be run via: python manage.py shell -c "from syllabus.load_all_syllabi import load_all; load_all()"
"""

import os
import sys
import django

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nimides.settings")
    django.setup()

from django.db import transaction
from syllabus.load_syllabus import load_syllabus
from syllabus.models import Exam

def load_all():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    syllabus_dir = os.path.join(base_dir, "syllabus_list")
    files = [
        ("neet", os.path.join(syllabus_dir, "neet_syllabus_complete.json")),
        ("pcs", os.path.join(syllabus_dir, "pcs_syllabus_complete.json")),
        ("jee", os.path.join(syllabus_dir, "jee_syllabus.json")),
        ("placement", os.path.join(syllabus_dir, "placement_syllabus.json")),
    ]

    for exam_type, file_path in files:
        if os.path.exists(file_path):
            exam = load_syllabus(file_path)
            if exam:
                exam.exam_type = exam_type
                exam.save()
                print(f"Set exam_type='{exam_type}' for '{exam.name}'")

    print("All complete syllabi loaded successfully!")

if __name__ == "__main__":
    load_all()
