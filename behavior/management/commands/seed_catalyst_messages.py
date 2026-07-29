"""
Management command: seed_catalyst_messages

Usage:
    python manage.py seed_catalyst_messages
    python manage.py seed_catalyst_messages --clear   # wipes and re-seeds

Seeds the CatalystMessage table with the initial Daksh companion messages.
Can be re-run safely (uses update_or_create on trigger+title).
"""

from django.core.management.base import BaseCommand
from behavior.models import CatalystMessage

MESSAGES = [
    # ── Return After Break ─────────────────────────────────────────────────
    {
        "trigger": "RETURN_AFTER_BREAK",
        "title": "Explorer detected.",
        "body": "Your ship was quiet for a while. No damage detected — your knowledge is intact. The universe has been waiting. Shall we restart the engines?",
        "cta_text": "Restart Engines",
        "cta_action": "navigate:/learn",
        "weight": 10,
    },
    {
        "trigger": "RETURN_AFTER_BREAK",
        "title": "Signal restored.",
        "body": "I noticed the transmission gap. But I also noticed you came back. That decision matters more than the days you missed.",
        "cta_text": "Continue Journey",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── Repeated Quiz Failure ──────────────────────────────────────────────
    {
        "trigger": "QUIZ_FAILED_REPEAT",
        "title": "I noticed something.",
        "body": "Your brain is not weak here. This concept is missing one foundation piece. When we find it, everything else will click. Let's repair it — together.",
        "cta_text": "Repair Foundation",
        "cta_action": "navigate:/learn",
        "weight": 10,
    },
    {
        "trigger": "QUIZ_FAILED_REPEAT",
        "title": "Interesting pattern.",
        "body": "You have faced this concept multiple times. That is not failure — that is your mind asking for a different entry point. Let me show you one.",
        "cta_text": "Try Different Angle",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── Perfect Quiz ───────────────────────────────────────────────────────
    {
        "trigger": "QUIZ_PERFECT",
        "title": "Precision detected.",
        "body": "Perfect score. Your mind is operating at peak clarity on this concept. This is what mastery looks like — remember this feeling.",
        "cta_text": "Explore Next Concept",
        "cta_action": "navigate:/learn",
        "weight": 7,
    },

    # ── Concept Mastered ───────────────────────────────────────────────────
    {
        "trigger": "CONCEPT_MASTERED",
        "title": "Signal received.",
        "body": "You just conquered this concept. Your knowledge universe grew stronger. A new path has opened — and it leads somewhere worth exploring.",
        "cta_text": "Explore Next",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },
    {
        "trigger": "CONCEPT_MASTERED",
        "title": "Expansion detected.",
        "body": "One more concept fully mapped. Your universe keeps growing. I have observed: the learners who master concepts one at a time go the furthest.",
        "cta_text": "Keep Building",
        "cta_action": "navigate:/learn",
        "weight": 7,
    },

    # ── Streak Milestone ───────────────────────────────────────────────────
    {
        "trigger": "STREAK_MILESTONE",
        "title": "Consistency detected.",
        "body": "You have studied for consecutive days without stopping. Momentum is a rare force in the universe. You have it. Do not waste it.",
        "cta_text": "Keep Going",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── Identity Unlocked ──────────────────────────────────────────────────
    {
        "trigger": "IDENTITY_UNLOCKED",
        "title": "Evolution detected.",
        "body": "A new identity has been unlocked. This is not just a badge — it is a signal that your mind has changed. Your universe recognizes it.",
        "cta_text": "See Your Profile",
        "cta_action": "navigate:/profile",
        "weight": 9,
    },

    # ── Low Energy ─────────────────────────────────────────────────────────
    {
        "trigger": "LOW_ENERGY",
        "title": "Energy scan complete.",
        "body": "I detect low fuel today. Choose one small concept — not ten. One deep understanding built on low energy is worth more than ten shallow attempts.",
        "cta_text": "One Concept Today",
        "cta_action": "navigate:/learn",
        "weight": 7,
    },
    {
        "trigger": "LOW_ENERGY",
        "title": "Observation.",
        "body": "Low energy is not the enemy of learning. It is a signal to go slower and deeper. Choose your hardest concept and spend 15 minutes — nothing more.",
        "cta_text": "Start Slow",
        "cta_action": "navigate:/learn",
        "weight": 6,
    },

    # ── Momentum Falling ───────────────────────────────────────────────────
    {
        "trigger": "MOMENTUM_FALLING",
        "title": "Drift detected.",
        "body": "Your momentum has been slowing. This is normal — but it is also a signal. One strong session today resets the pattern. I will be here.",
        "cta_text": "Reset Momentum",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── Daily Target Hit ───────────────────────────────────────────────────
    {
        "trigger": "DAILY_TARGET_HIT",
        "title": "Mission complete.",
        "body": "Today's target reached. Everything beyond this point is bonus momentum. Most learners stop here. You do not have to.",
        "cta_text": "Go Beyond",
        "cta_action": "navigate:/learn",
        "weight": 5,
    },

    # ── Thriving ───────────────────────────────────────────────────────────
    {
        "trigger": "THRIVING",
        "title": "Outstanding signal.",
        "body": "Your knowledge field is expanding rapidly. You are operating at one of the highest levels I have observed. Keep this pace and you will arrive earlier than planned.",
        "cta_text": "Push Further",
        "cta_action": "navigate:/learn",
        "weight": 6,
    },

    # ── At Risk ────────────────────────────────────────────────────────────
    {
        "trigger": "AT_RISK",
        "title": "Transmission incoming.",
        "body": "Your universe has been quiet. I am detecting signal loss. Even 10 minutes today restores the connection and protects what you have already built.",
        "cta_text": "Restore Signal",
        "cta_action": "navigate:/learn",
        "weight": 9,
    },
    {
        "trigger": "AT_RISK",
        "title": "Low signal detected.",
        "body": "The knowledge you built is still there — but it needs a signal to stay alive. Come back for 10 minutes. That is all it takes today.",
        "cta_text": "10 Minutes Now",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── First Login ────────────────────────────────────────────────────────
    {
        "trigger": "FIRST_LOGIN",
        "title": "Transmission received.",
        "body": "Hello, explorer. I am Daksh. I have been waiting for someone who wants to upgrade their mind. Your journey starts now — and I will be with you for all of it.",
        "cta_text": "Begin Journey",
        "cta_action": "navigate:/learn",
        "weight": 10,
    },

    # ── Goal Set ───────────────────────────────────────────────────────────
    {
        "trigger": "GOAL_SET",
        "title": "Mission coordinates locked.",
        "body": "Your target has been set. I have computed your path. The journey ahead is real — and every day you study brings it closer. Let's begin.",
        "cta_text": "Start First Session",
        "cta_action": "navigate:/learn",
        "weight": 9,
    },

    # ── Generic Insight ────────────────────────────────────────────────────
    {
        "trigger": "GENERIC_INSIGHT",
        "title": "Observation.",
        "body": "Consistency beats intensity. One focused session every day builds more knowledge than five exhausting ones per week.",
        "cta_text": "Begin Session",
        "cta_action": "navigate:/learn",
        "weight": 1,
    },
    {
        "trigger": "GENERIC_INSIGHT",
        "title": "Pattern observed.",
        "body": "The learners who improve fastest are not the ones who study hardest — they are the ones who study most consistently. Today counts.",
        "cta_text": "Study Today",
        "cta_action": "navigate:/learn",
        "weight": 1,
    },
    {
        "trigger": "GENERIC_INSIGHT",
        "title": "Signal from the galaxy.",
        "body": "Your knowledge universe is always either growing or decaying — it never stands still. Right now, a session keeps it growing.",
        "cta_text": "Keep Growing",
        "cta_action": "navigate:/learn",
        "weight": 1,
    },
]


class Command(BaseCommand):
    help = "Seed the CatalystMessage table with Daksh companion messages."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing messages before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = CatalystMessage.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} existing messages."))

        created_count = 0
        updated_count = 0

        for msg_data in MESSAGES:
            obj, created = CatalystMessage.objects.update_or_create(
                trigger=msg_data["trigger"],
                title=msg_data["title"],
                defaults={
                    "body":       msg_data["body"],
                    "cta_text":   msg_data["cta_text"],
                    "cta_action": msg_data["cta_action"],
                    "weight":     msg_data["weight"],
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created_count} messages, updated {updated_count} messages. "
                f"Total: {CatalystMessage.objects.count()} messages in DB."
            )
        )
