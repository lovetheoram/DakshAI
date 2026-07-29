"""
Management command: seed_catalyst_messages

Usage:
    python manage.py seed_catalyst_messages
    python manage.py seed_catalyst_messages --clear   # wipes and re-seeds

Seeds the CatalystMessage table with the initial Daksh companion messages.
Can be re-run safely (uses update_or_create on trigger+title+tone).
"""

from django.core.management.base import BaseCommand
from behavior.models import CatalystMessage

MESSAGES = [
    # ── Return After Break ─────────────────────────────────────────────────
    {
        "trigger": "RETURN_AFTER_BREAK",
        "tone": "companion",
        "title": "Explorer detected.",
        "body": "Your ship was quiet for a while. No damage detected — your knowledge is intact. The universe has been waiting. Shall we restart the engines?",
        "cta_text": "Restart Engines",
        "cta_action": "navigate:/learn",
        "weight": 10,
    },
    {
        "trigger": "RETURN_AFTER_BREAK",
        "tone": "mentor",
        "title": "Signal restored.",
        "body": "I noticed the transmission gap. But I also noticed you came back. That decision matters more than the days you missed.",
        "cta_text": "Continue Journey",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── Repeated Quiz Failure ──────────────────────────────────────────────
    {
        "trigger": "QUIZ_FAILED_REPEAT",
        "tone": "mentor",
        "title": "I noticed something.",
        "body": "Your brain is not weak here. This concept is missing one foundation piece. When we find it, everything else will click. Let's repair it — together.",
        "cta_text": "Repair Foundation",
        "cta_action": "navigate:/learn",
        "weight": 10,
    },
    {
        "trigger": "QUIZ_FAILED_REPEAT",
        "tone": "companion",
        "title": "Interesting pattern.",
        "body": "You have faced this concept multiple times. That is not failure — that is your mind asking for a different entry point. Let me show you one.",
        "cta_text": "Try Different Angle",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── Perfect Quiz ───────────────────────────────────────────────────────
    {
        "trigger": "QUIZ_PERFECT",
        "tone": "any",
        "title": "Precision detected.",
        "body": "Perfect score. Your mind is operating at peak clarity on this concept. This is what mastery looks like — remember this feeling.",
        "cta_text": "Explore Next Concept",
        "cta_action": "navigate:/learn",
        "weight": 7,
    },

    # ── Concept Mastered ───────────────────────────────────────────────────
    {
        "trigger": "CONCEPT_MASTERED",
        "tone": "companion",
        "title": "Signal received.",
        "body": "You just conquered this concept. Your knowledge universe grew stronger. A new path has opened — and it leads somewhere worth exploring.",
        "cta_text": "Explore Next",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },
    {
        "trigger": "CONCEPT_MASTERED",
        "tone": "challenger",
        "title": "Expansion detected.",
        "body": "One more concept fully mapped. Your universe keeps growing. I have observed: the learners who master concepts one at a time go the furthest.",
        "cta_text": "Keep Building",
        "cta_action": "navigate:/learn",
        "weight": 7,
    },

    # ── Streak Milestone ───────────────────────────────────────────────────
    {
        "trigger": "STREAK_MILESTONE",
        "tone": "any",
        "title": "Consistency detected.",
        "body": "You have studied for consecutive days without stopping. Momentum is a rare force in the universe. You have it. Do not waste it.",
        "cta_text": "Keep Going",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── Identity Unlocked ──────────────────────────────────────────────────
    {
        "trigger": "IDENTITY_UNLOCKED",
        "tone": "any",
        "title": "Evolution detected.",
        "body": "A new identity has been unlocked. This is not just a badge — it is a signal that your mind has changed. Your universe recognizes it.",
        "cta_text": "See Your Profile",
        "cta_action": "navigate:/profile",
        "weight": 9,
    },

    # ── Low Energy ─────────────────────────────────────────────────────────
    {
        "trigger": "LOW_ENERGY",
        "tone": "mentor",
        "title": "Energy scan complete.",
        "body": "I detect low fuel today. Choose one small concept — not ten. One deep understanding built on low energy is worth more than ten shallow attempts.",
        "cta_text": "One Concept Today",
        "cta_action": "navigate:/learn",
        "weight": 7,
    },
    {
        "trigger": "LOW_ENERGY",
        "tone": "companion",
        "title": "Observation.",
        "body": "Low energy is not the enemy of learning. It is a signal to go slower and deeper. Choose your hardest concept and spend 15 minutes — nothing more.",
        "cta_text": "Start Slow",
        "cta_action": "navigate:/learn",
        "weight": 6,
    },

    # ── Momentum Falling ───────────────────────────────────────────────────
    {
        "trigger": "MOMENTUM_FALLING",
        "tone": "mentor",
        "title": "Drift detected.",
        "body": "Your momentum has been slowing. This is normal — but it is also a signal. One strong session today resets the pattern. I will be here.",
        "cta_text": "Reset Momentum",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── Daily Target Hit ───────────────────────────────────────────────────
    {
        "trigger": "DAILY_TARGET_HIT",
        "tone": "any",
        "title": "Mission complete.",
        "body": "Today's target reached. Everything beyond this point is bonus momentum. Most learners stop here. You do not have to.",
        "cta_text": "Go Beyond",
        "cta_action": "navigate:/learn",
        "weight": 5,
    },

    # ── Thriving ───────────────────────────────────────────────────────────
    {
        "trigger": "THRIVING",
        "tone": "challenger",
        "title": "Outstanding signal.",
        "body": "Your knowledge field is expanding rapidly. You are operating at one of the highest levels I have observed. Keep this pace and you will arrive earlier than planned.",
        "cta_text": "Push Further",
        "cta_action": "navigate:/learn",
        "weight": 6,
    },

    # ── At Risk ────────────────────────────────────────────────────────────
    {
        "trigger": "AT_RISK",
        "tone": "mentor",
        "title": "Transmission incoming.",
        "body": "Your universe has been quiet. I am detecting signal loss. Even 10 minutes today restores the connection and protects what you have already built.",
        "cta_text": "Restore Signal",
        "cta_action": "navigate:/learn",
        "weight": 9,
    },
    {
        "trigger": "AT_RISK",
        "tone": "companion",
        "title": "Low signal detected.",
        "body": "The knowledge you built is still there — but it needs a signal to stay alive. Come back for 10 minutes. That is all it takes today.",
        "cta_text": "10 Minutes Now",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── First Login ────────────────────────────────────────────────────────
    {
        "trigger": "FIRST_LOGIN",
        "tone": "companion",
        "title": "Transmission received.",
        "body": "Hello, explorer. I am Daksh. I have been waiting for someone who wants to upgrade their mind. Your journey starts now — and I will be with you for all of it.",
        "cta_text": "Begin Journey",
        "cta_action": "navigate:/learn",
        "weight": 10,
    },

    # ── Goal Set ───────────────────────────────────────────────────────────
    {
        "trigger": "GOAL_SET",
        "tone": "any",
        "title": "Mission coordinates locked.",
        "body": "Your target has been set. I have computed your path. The journey ahead is real — and every day you study brings it closer. Let's begin.",
        "cta_text": "Start First Session",
        "cta_action": "navigate:/learn",
        "weight": 9,
    },

    # ── Generic Insight ────────────────────────────────────────────────────
    {
        "trigger": "GENERIC_INSIGHT",
        "tone": "any",
        "title": "Observation.",
        "body": "Consistency beats intensity. One focused session every day builds more knowledge than five exhausting ones per week.",
        "cta_text": "Begin Session",
        "cta_action": "navigate:/learn",
        "weight": 1,
    },
    {
        "trigger": "GENERIC_INSIGHT",
        "tone": "any",
        "title": "Pattern observed.",
        "body": "The learners who improve fastest are not the ones who study hardest — they are the ones who study most consistently. Today counts.",
        "cta_text": "Study Today",
        "cta_action": "navigate:/learn",
        "weight": 1,
    },
    {
        "trigger": "GENERIC_INSIGHT",
        "tone": "any",
        "title": "Signal from the galaxy.",
        "body": "Your knowledge universe is always either growing or decaying — it never stands still. Right now, a session keeps it growing.",
        "cta_text": "Keep Growing",
        "cta_action": "navigate:/learn",
        "weight": 1,
    },

    # ══════════════════════════════════════════════════════════════════════
    # Phase 5 — OIDPI Action-Type Messages
    # ══════════════════════════════════════════════════════════════════════

    # ── CURIOSITY_PROMPT — Ask before Notes ───────────────────────────────
    {
        "trigger": "CURIOSITY_PROMPT",
        "tone": "mentor",
        "title": "Before we begin.",
        "body": "Can I ask you something before we start? Without looking — how many of these formulas do you think you already know?",
        "cta_text": "Let me check",
        "cta_action": "curiosity:assess",
        "weight": 10,
    },
    {
        "trigger": "CURIOSITY_PROMPT",
        "tone": "challenger",
        "title": "No peeking.",
        "body": "Before reading anything — let me see what you already hold. Tick what you know. Don't think too long.",
        "cta_text": "Start recall",
        "cta_action": "curiosity:assess",
        "weight": 9,
    },
    {
        "trigger": "CURIOSITY_PROMPT",
        "tone": "companion",
        "title": "Quick question.",
        "body": "Before the notes open — want to play a small game? Tick every formula you believe you know. No judgment 🙂",
        "cta_text": "Let's play",
        "cta_action": "curiosity:assess",
        "weight": 8,
    },

    # ── DIRECT_CHALLENGE — High mastery, skip reading ─────────────────────
    {
        "trigger": "DIRECT_CHALLENGE",
        "tone": "challenger",
        "title": "Skip the reading.",
        "body": "You've been here before. Your mastery says you already know this. Let me see how much you've held on to.",
        "cta_text": "Take the challenge",
        "cta_action": "navigate:quiz",
        "weight": 10,
    },
    {
        "trigger": "DIRECT_CHALLENGE",
        "tone": "companion",
        "title": "You already know this.",
        "body": "Your progress shows strong familiarity here. Want to skip reading and test yourself directly? You might surprise yourself.",
        "cta_text": "Test me",
        "cta_action": "navigate:quiz",
        "weight": 8,
    },

    # ── ENCOURAGEMENT — Fear area, low confidence ─────────────────────────
    {
        "trigger": "ENCOURAGEMENT",
        "tone": "mentor",
        "title": "I see what's happening.",
        "body": "This concept has given you trouble before. That doesn't mean your brain is weak here — it means one small foundation piece is missing. Let's find it together.",
        "cta_text": "Start slow",
        "cta_action": "navigate:/learn",
        "weight": 10,
    },
    {
        "trigger": "ENCOURAGEMENT",
        "tone": "companion",
        "title": "You've faced this before.",
        "body": "I know this concept hasn't been easy. But the fact that you're back here says something. Let's approach it from a different angle today.",
        "cta_text": "Try again",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── CELEBRATION — Milestone just hit ──────────────────────────────────
    {
        "trigger": "CELEBRATION",
        "tone": "any",
        "title": "Something just happened.",
        "body": "You crossed a threshold. This isn't just a number — it's evidence that the work is working. Take a second to notice that.",
        "cta_text": "Keep going",
        "cta_action": "navigate:/learn",
        "weight": 9,
    },
    {
        "trigger": "CELEBRATION",
        "tone": "challenger",
        "title": "Noted.",
        "body": "Good. Now don't stop. Momentum is the rarest thing in learning — you have it right now. Use it.",
        "cta_text": "Push further",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── FOCUSED_EXPLAIN — Repeated failure, stuck ─────────────────────────
    {
        "trigger": "FOCUSED_EXPLAIN",
        "tone": "mentor",
        "title": "I found the gap.",
        "body": "After watching your attempts, I think I know what's missing. It's not the formula — it's one step earlier. Let me show you where to look.",
        "cta_text": "Show me",
        "cta_action": "navigate:/learn",
        "weight": 9,
    },
    {
        "trigger": "FOCUSED_EXPLAIN",
        "tone": "companion",
        "title": "Something's off.",
        "body": "I've noticed this concept keeps resisting you. That's always a clue — not a flaw. The entry point is different for everyone. Let's find yours.",
        "cta_text": "Find my entry",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── REFLECTION_PROMPT — Long session, idle drift ──────────────────────
    {
        "trigger": "REFLECTION_PROMPT",
        "tone": "mentor",
        "title": "You've been here a while.",
        "body": "Before you move on — what's one thing you understood today that you didn't before? Just one. Naming it makes it stick.",
        "cta_text": "I've got one",
        "cta_action": "reflect:prompt",
        "weight": 8,
    },
    {
        "trigger": "REFLECTION_PROMPT",
        "tone": "companion",
        "title": "Still here?",
        "body": "You've been in this concept for a while. That's either deep focus or a drift. Either way — want a nudge toward something specific?",
        "cta_text": "Give me a nudge",
        "cta_action": "reflect:prompt",
        "weight": 7,
    },

    # ── PREDICTION_NARRATIVE — Growth page story ──────────────────────────
    {
        "trigger": "PREDICTION_NARRATIVE",
        "tone": "mentor",
        "title": "I've been watching your rhythm.",
        "body": "At your current pace, you're on a path to finish around {predicted_date}. That's {days_delta} days from your target. You can close it — the gap is real, but so is your momentum.",
        "cta_text": "Adjust my plan",
        "cta_action": "growth:adjust",
        "weight": 10,
    },
    {
        "trigger": "PREDICTION_NARRATIVE",
        "tone": "challenger",
        "title": "Here's your number.",
        "body": "{days_delta} days. That's the gap between your current pace and your target. {extra_minutes} extra minutes a day closes it. You've done harder things.",
        "cta_text": "Accelerate",
        "cta_action": "growth:adjust",
        "weight": 9,
    },
    {
        "trigger": "PREDICTION_NARRATIVE",
        "tone": "companion",
        "title": "Good news.",
        "body": "At this pace, you're tracking to finish around {predicted_date}. You're {days_delta} days {status} of your goal. Let's keep this going.",
        "cta_text": "Begin today's session",
        "cta_action": "navigate:/learn",
        "weight": 8,
    },

    # ── IDENTITY_ARRIVAL — Daily mood ritual ──────────────────────────────
    {
        "trigger": "IDENTITY_ARRIVAL",
        "tone": "companion",
        "title": "Every day I ask myself one question.",
        "body": "What kind of person am I becoming? Want to answer together?",
        "cta_text": "Yes",
        "cta_action": "identity:mood_select",
        "weight": 10,
    },
    {
        "trigger": "IDENTITY_ARRIVAL",
        "tone": "mentor",
        "title": "Before we begin today.",
        "body": "How are you arriving? Your energy shapes what kind of session this becomes. Let's name it.",
        "cta_text": "Tell Daksh",
        "cta_action": "identity:mood_select",
        "weight": 9,
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
