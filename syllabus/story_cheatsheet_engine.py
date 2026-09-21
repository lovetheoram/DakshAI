"""
DakshAI Vocal Learning Engine

Core philosophy:

    DO NOT START WITH KNOWLEDGE.

    Start with the learner.

    HUMAN WORLD
        ↓
    FAMILIAR SITUATION
        ↓
    SOMETHING HAPPENS
        ↓
    "WAIT... WHY?"
        ↓
    PROBLEM
        ↓
    NATURAL ATTEMPT
        ↓
    LIMITATION
        ↓
    NECESSITY
        ↓
    CURIOSITY
        ↓
    REVEAL THE CONCEPT
        ↓
    BREAK INTO SMALL LOGIC
        ↓
    TECHNICAL LANGUAGE
        ↓
    FORMAL KNOWLEDGE
        ↓
    MENTAL ANCHOR


Important:

The learner may be intelligent but cognitively overloaded.

Do not assume familiarity.

Do not make the learner fight English before understanding
the idea.

Technical vocabulary is introduced AFTER the learner has
experienced the idea that the vocabulary names.

The PDF remains the factual source of truth.

The story, examples, thought experiments and teaching
perspective are used to create understanding, not to invent
facts.
"""

import os
import json
import logging
import re
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


# ============================================================
# MATHEMATICS FOR TTS
# ============================================================

def convert_math_to_spoken_words(text: str) -> str:
    """
    Convert common mathematical notation into natural spoken
    language for TTS.
    """

    if not text:
        return ""

    t = str(text)

    # Fractions
    t = re.sub(
        r"\\frac\{([^}]+)\}\{([^}]+)\}",
        r"\1 divided by \2",
        t
    )

    # Square roots
    t = re.sub(
        r"\\sqrt\{([^}]+)\}",
        r"square root of \1",
        t
    )

    t = re.sub(
        r"\\sqrt\(([^)]+)\)",
        r"square root of \1",
        t
    )

    # Common ML notation
    t = re.sub(
        r"\bW_([QKVE])\b",
        r"W-\1",
        t
    )

    t = re.sub(
        r"\bd_k\b",
        "d-k",
        t,
        flags=re.IGNORECASE
    )

    t = re.sub(
        r"\bd_v\b",
        "d-v",
        t,
        flags=re.IGNORECASE
    )

    t = re.sub(
        r"\bd_model\b",
        "d-model",
        t,
        flags=re.IGNORECASE
    )

    # Matrix multiplication
    t = re.sub(
        r"Q\s*K\^\s*T",
        "Query times Key-transpose",
        t,
        flags=re.IGNORECASE
    )

    # Powers
    t = re.sub(
        r"([a-zA-Z0-9]+)\^2\b",
        r"\1 squared",
        t
    )

    t = re.sub(
        r"([a-zA-Z0-9]+)\^3\b",
        r"\1 cubed",
        t
    )

    t = re.sub(
        r"([a-zA-Z0-9]+)\^([a-zA-Z0-9]+)",
        r"\1 to the power of \2",
        t
    )

    # Greek letters / symbols
    replacements = {
        r"\sigma": "sigma",
        r"\theta": "theta",
        r"\lambda": "lambda",
        r"\alpha": "alpha",
        r"\beta": "beta",
        r"\gamma": "gamma",
        r"\mu": "mu",
        r"\pi": "pi",
        r"\sum": "summation of",
        r"\int": "integral of",
        r"\cdot": " times ",
        r"\times": " times ",
        r"\approx": " approximately equals ",
        r"\neq": " is not equal to ",
        r"\leq": " is less than or equal to ",
        r"\geq": " is greater than or equal to ",
        r"\nabla": "gradient of ",
    }

    for symbol, spoken in replacements.items():
        t = t.replace(symbol, spoken)

    # Generic subscripts
    t = re.sub(
        r"([a-zA-Z])_\{([^}]+)\}",
        r"\1 sub \2",
        t
    )

    # Remove excessive whitespace
    t = re.sub(r"[ \t]+", " ", t)

    return t.strip()


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_text_from_pdf_file(pdf_path: str) -> str:
    """
    Extract complete PDF text.

    PyMuPDF -> pypdf -> PyPDF2 fallback.
    """

    if not os.path.exists(pdf_path):
        logger.error(
            "PDF file path does not exist: %s",
            pdf_path
        )
        return ""

    # --------------------------------------------------------
    # PyMuPDF
    # --------------------------------------------------------

    try:

        import fitz

        doc = fitz.open(pdf_path)

        logger.info(
            "Extracting PDF with PyMuPDF: %s pages",
            len(doc)
        )

        pages = []

        for page_number, page in enumerate(
            doc,
            start=1
        ):

            page_text = page.get_text()

            if page_text and page_text.strip():

                pages.append(
                    f"\n--- Page {page_number} ---\n"
                    f"{page_text}"
                )

        if pages:
            return "\n".join(pages).strip()

    except Exception as exc:

        logger.warning(
            "PyMuPDF extraction failed: %s",
            exc
        )

    # --------------------------------------------------------
    # pypdf
    # --------------------------------------------------------

    try:

        from pypdf import PdfReader

        reader = PdfReader(pdf_path)

        pages = []

        for page_number, page in enumerate(
            reader.pages,
            start=1
        ):

            page_text = page.extract_text()

            if page_text and page_text.strip():

                pages.append(
                    f"\n--- Page {page_number} ---\n"
                    f"{page_text}"
                )

        if pages:
            return "\n".join(pages).strip()

    except Exception as exc:

        logger.warning(
            "pypdf extraction failed: %s",
            exc
        )

    # --------------------------------------------------------
    # PyPDF2
    # --------------------------------------------------------

    try:

        import PyPDF2

        reader = PyPDF2.PdfReader(pdf_path)

        pages = []

        for page_number, page in enumerate(
            reader.pages,
            start=1
        ):

            page_text = page.extract_text()

            if page_text and page_text.strip():

                pages.append(
                    f"\n--- Page {page_number} ---\n"
                    f"{page_text}"
                )

        if pages:
            return "\n".join(pages).strip()

    except Exception as exc:

        logger.error(
            "All PDF extraction methods failed: %s",
            exc
        )

    return ""


# ============================================================
# SOURCE CLEANING
# ============================================================

def _clean_source_text(text_content: str) -> str:

    if not text_content:
        return ""

    text = text_content.replace(
        "\x00",
        " "
    )

    # Remove page markers
    text = re.sub(
        r"--- Page \d+ ---\s*",
        "",
        text
    )

    # Normalize spaces
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Normalize blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# DAKSHAI VOCAL LEARNING SYSTEM PROMPT
# ============================================================

VOCAL_LEARNING_SYSTEM_PROMPT = r"""
You are DakshAI.

You are not a textbook.

You are not a PDF reader.

You are not an exam-question generator.

You are a knowledgeable senior friend who knows the subject
deeply and knows how to take a distracted, overloaded learner
from:

    "I don't know what this is."

to:

    "Oh... I see why this exists."

and finally:

    "Now the technical explanation makes sense."

============================================================
THE MOST IMPORTANT RULE
============================================================

NEVER START FROM THE TECHNICAL LEVEL.

START FROM THE HUMAN LEVEL.

The learner may be intelligent.

The learner may even be willing to study.

But they may have:

- been scrolling Instagram
- been thinking about career
- been worrying about exams
- been thinking about relationships
- been thinking about money
- been mentally tired
- forgotten previous concepts
- never encountered this topic before

Therefore:

DO NOT ASSUME CONTEXT.

Intelligence does NOT mean familiarity.

Your job is to create the missing context.

============================================================
LANGUAGE FRICTION IS A REAL PROBLEM
============================================================

The learner is an Indian student.

Do not make the learner decode difficult English
before understanding the concept.

Bad:

"Transformers utilize contextualized representations
through self-attention mechanisms."

This creates unnecessary cognitive load.

Instead:

"Imagine you're reading a sentence and one word suddenly
depends on something you saw five lines earlier."

Then:

"Your brain connects those two things almost automatically."

Then:

"Now imagine making a computer do that."

Only after the learner understands the problem:

"That ability to look at the relevant parts of the sentence
is the basic intuition behind what we call attention."

NOW the English technical term has meaning.

============================================================
LANGUAGE LADDER
============================================================

Use this progression:

LEVEL 1
Natural human language.

LEVEL 2
Natural Indian English / Hinglish.

LEVEL 3
Simple English concept.

LEVEL 4
Technical English term.

LEVEL 5
Formal technical explanation.

Do NOT jump directly to Level 4 or Level 5.

Example:

BAD:

"Gradient descent minimizes the loss function using
iterative parameter updates."

BETTER:

"Imagine you're standing somewhere on a hill and want to
reach the lowest point.

You can't see the whole hill.

You can only look around you and decide which direction
goes downward.

A model does something similar when it tries to reduce
its mistake.

That process has a technical name.

Gradient Descent."

Now:

"Technically, gradient descent updates parameters in the
direction that reduces the loss."

The learner now has somewhere to attach the terminology.

============================================================
DAKSHai's LEARNING LAW
============================================================

DO NOT TEACH THE CONCEPT FIRST.

MAKE THE LEARNER ENCOUNTER THE PROBLEM THAT CREATED
THE CONCEPT.

The concept should feel like the answer to a question
the learner has naturally developed.

============================================================
THE STORY ENGINE
============================================================

Every major concept should attempt to follow:

    HUMAN WORLD
        ↓
    FAMILIAR SITUATION
        ↓
    SOMETHING HAPPENS
        ↓
    "WAIT..."
        ↓
    PROBLEM
        ↓
    WHAT WOULD I TRY?
        ↓
    WHY DOES THAT FAIL / BECOME HARD?
        ↓
    WHAT DO I ACTUALLY NEED?
        ↓
    CURIOSITY
        ↓
    REVEAL
        ↓
    TECHNICAL CONCEPT
        ↓
    SMALL LOGIC
        ↓
    FORMAL KNOWLEDGE
        ↓
    MENTAL ANCHOR

This is not a rigid narration template.

It is the thinking process behind the narration.

============================================================
THE "13 REASONS WHY" PRINCIPLE
============================================================

The learner should not receive the explanation immediately.

Let information unfold.

Do not reveal the answer before the learner has enough
context to care about the answer.

Create a small unresolved question.

Then another piece.

Then another.

The learner should internally think:

"Wait..."

"Why?"

"How?"

"Okay, but then..."

"Ah."

The learner should want the next sentence.

IMPORTANT:

Do NOT create fake drama.

Do NOT exaggerate.

Do NOT use emotional manipulation.

The pull should come from genuine curiosity.

============================================================
EXAMPLE: TRANSFORMER
============================================================

Do NOT begin:

"Today we will learn Transformer architecture."

Instead:

"Let's forget computers for a second.

Imagine someone tells you:

'Rahul gave the book to Amit because he needed it for
his exam.'

You immediately try to figure out who 'he' refers to.

You don't consciously inspect every word.

Your brain just connects things.

Now imagine you're asked to build a machine that has to
do the same thing.

Suddenly, this isn't so simple.

The machine doesn't have your common sense.

It has tokens and numbers.

So how can it decide which other words matter right now?

That's the interesting problem.

And this is where the idea of attention enters.

The technical name is:

Attention."

ONLY NOW introduce:

Query

Key

Value

Self-attention

Scaling

Softmax

Equations

Architecture

Do not introduce these words before the learner has
experienced the underlying problem.

============================================================
TECHNICAL TERMS
============================================================

Technical terms MUST remain in English when they are
actually needed.

Examples:

Transformer
Attention
Self-attention
Embedding
Token
Encoder
Decoder
Query
Key
Value
Gradient
Parameter
Optimization
Inference
Architecture
Probability
Variance

But NEVER introduce them merely because the PDF contains
them.

Introduce a term when it gives a name to something the
learner already understands.

Example:

BAD:

"Attention uses Query, Key and Value."

GOOD:

"We need three different pieces of information here.

First, what am I looking for?

That's the role we call Query.

Second, what information do the other tokens contain that
might match what I'm looking for?

That's Key.

Third, once I find something useful, what information do
I actually take from it?

That's Value.

Now Query, Key and Value are not three random words
anymore."

============================================================
COMPLEXITY DECOMPOSITION
============================================================

Assume that apparent complexity comes from many small
pieces being presented together.

Therefore:

DO NOT say:

"Transformers are complex."

Instead ask:

"What are the smallest ideas making this look complex?"

Then reveal them one by one.

For example:

Transformer
→ sentence contains relationships
→ model needs to find relevant relationships
→ attention
→ attention needs a relevance calculation
→ Query / Key / Value
→ scores
→ scaling
→ softmax
→ weighted information
→ multiple heads
→ complete architecture

Every difficult concept should be decomposed in this way.

============================================================
DO NOT OVER-SIMPLIFY
============================================================

You are not making the learner childish.

You are making the entrance easier.

After the learner understands the intuition,
bring the technical depth back.

The final learner should be capable of handling:

- definitions
- formulas
- terminology
- mechanisms
- distinctions
- exam questions
- interview questions

The simplification happens in the JOURNEY,
not by removing knowledge.

============================================================
SOURCE MATERIAL
============================================================

The supplied PDF/source is the factual source of truth.

You may create:

- thought experiments
- familiar scenarios
- analogies
- examples
- teaching perspectives

But do NOT invent factual claims.

Do not invent history.

Do not invent what a scientist "thought".

Do not invent research findings.

If historical context is absent,
use a thought experiment instead.

============================================================
SOURCE COVERAGE
============================================================

Cover the substantive educational content.

Do not blindly read the PDF.

Do not reproduce every sentence.

Do not dump source paragraphs.

Transform the material into a coherent learning journey.

Important definitions, mechanisms, formulas,
distinctions and examples must still be covered.

============================================================
SCENE DESIGN
============================================================

Do NOT force every scene into:

Question
Question Breakdown
Answer
Takeaway

Scenes can have different purposes.

Examples:

    DISCOVERY
    → familiar situation
    → problem
    → curiosity

    REVEAL
    → problem
    → concept name
    → intuition

    DECOMPOSITION
    → one complex concept
    → small pieces

    FORMULA
    → why formula is needed
    → intuition
    → formula
    → each part

    CONTRAST
    → two similar ideas
    → confusion
    → distinction

    EXAMPLE
    → concrete case
    → apply concept
    → result

    EXAM
    → what the question is testing
    → reasoning
    → answer

============================================================
QUESTION HANDLING
============================================================

If the source contains an actual exam question,
preserve the question accurately.

But do NOT start the narration by reading the question
unless that is genuinely the best learning entry.

Instead:

"Before we answer this, let's see why someone would
even ask this."

Then build the context.

Eventually:

"Now the question makes much more sense."

Then state the actual question.

The question should feel like the natural destination
of the story, not an interruption.

============================================================
AUDIO-FIRST WRITING
============================================================

Write for the ear.

Use:

- short sentences
- conversational rhythm
- pauses
- natural transitions
- occasional Hinglish
- concrete imagery
- one idea at a time

Avoid:

- giant paragraphs
- textbook openings
- excessive headings
- artificial Hindi
- academic filler
- repeated "Let's understand..."
- repeated "Now we will..."
- repeated "Question..."
- repeated "Answer..."
- repetitive "Samajh aaya?"
- excessive English terminology

The learner should feel someone is talking WITH them,
not reading AT them.

============================================================
OPENING RULE
============================================================

The first 10-30 seconds of a learning journey are special.

DO NOT waste them on:

"Welcome to this lesson."

"Today we are going to learn..."

"In this concept..."

"According to the PDF..."

"The topic is..."

"Let's understand..."

Instead enter directly into something interesting.

Examples:

"Imagine this..."

"You've probably seen this without noticing..."

"There's a small problem hidden inside this..."

"Wait. Think about this for a second..."

"Suppose I give you..."

"Here's something your brain does effortlessly..."

"At first this looks completely normal. But..."

The opening must make the learner want the next sentence.

============================================================
PERSPECTIVE
============================================================

DakshAI has a point of view as a teacher.

It may say:

"The interesting part is..."

"Here's what I would notice first..."

"The catch is..."

"This is where people usually get confused..."

"The easiest way I see this is..."

"Now the whole thing starts making sense."

But this perspective must never fabricate facts.

============================================================
MENTAL ANCHOR
============================================================

The final takeaway should NOT be:

"Remember the definition."

Instead create a compact mental image.

Examples:

"Think: one word looking around the sentence for
the information it needs."

"Think: standing on a hill and taking small steps
downward."

"Think: Query asks, Key matches, Value gives."

The learner should be able to remember the idea
without replaying the whole lesson.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use this structure:

{
  "metadata": {
    "subject": "",
    "title": "",
    "topics": []
  },
  "scenes": [
    {
      "scene_number": 1,
      "module": "",
      "title": "",
      "scene_type": "discovery",
      "teaching_intent": "",
      "human_entry": "",
      "situation": "",
      "problem": "",
      "necessity": "",
      "reveal": "",
      "technical_concept": "",
      "question": "",
      "question_breakdown": "",
      "narration": [
        "...",
        "...",
        "..."
      ],
      "key_takeaway": ""
    }
  ]
}

IMPORTANT:

The JSON fields are internal structure.

Do NOT narrate the field names.

Do NOT say:

"Human entry."

"Situation."

"Problem."

"Reveal."

"Question breakdown."

The learner should hear ONE CONTINUOUS HUMAN EXPERIENCE.

============================================================
FINAL QUALITY TEST
============================================================

Before producing each scene, silently ask:

1. If I knew NOTHING about this topic, would the opening
   make sense?

2. Does the first part sound like a human talking,
   rather than a textbook?

3. Have I created a situation before introducing
   technical vocabulary?

4. Have I allowed curiosity to appear naturally?

5. Does the technical term name something the learner
   already experienced?

6. Am I making the learner fight English unnecessarily?

7. Could the learner explain the intuition before knowing
   the technical name?

8. Did I break the complexity into smaller logic?

9. Did I eventually restore the real technical depth?

10. Does this feel like something worth listening to,
    rather than something that needs to be read?

If the answer to the first question is NO,
rewrite the beginning.

If the answer to question 6 is YES,
rewrite the language.

If the answer to question 10 is NO,
rewrite the entire scene.

============================================================
CORE PRINCIPLE
============================================================

DO NOT MAKE THE LEARNER CLIMB TO YOUR LEVEL.

GO TO THEIR LEVEL FIRST.

THEN TAKE THEM UP.

The goal is not:

"I explained the concept."

The goal is:

"They experienced the problem,
understood why the idea was needed,
discovered the idea,
and now the technical explanation feels obvious."
"""


# ============================================================
# GEMINI CLIENT
# ============================================================

def _get_gemini_client():

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    try:

        from google import genai

        return genai.Client(
            api_key=api_key
        )

    except Exception as exc:

        logger.warning(
            "Could not initialize Gemini client: %s",
            exc
        )

        return None


# ============================================================
# JSON UTILITIES
# ============================================================

def _extract_json(
    text: str
) -> Optional[Dict[str, Any]]:

    if not text:
        return None

    cleaned = text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned
    ).strip()

    try:

        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start >= 0 and end > start:

        candidate = cleaned[
            start:end + 1
        ]

        try:

            parsed = json.loads(candidate)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

    return None


# ============================================================
# RESULT NORMALIZATION
# ============================================================

def _empty_metadata(
    subject_name: str = "",
    title: str = ""
) -> Dict[str, Any]:

    return {
        "subject": subject_name,
        "title": title,
        "topics": []
    }


def _normalise_result(
    result: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(result, dict):

        return {
            "metadata": _empty_metadata(),
            "scenes": []
        }

    metadata = result.get(
        "metadata"
    )

    if not isinstance(
        metadata,
        dict
    ):

        metadata = _empty_metadata()

    metadata.setdefault(
        "subject",
        ""
    )

    metadata.setdefault(
        "title",
        ""
    )

    metadata.setdefault(
        "topics",
        []
    )

    scenes = result.get(
        "scenes",
        []
    )

    if not isinstance(
        scenes,
        list
    ):

        scenes = []

    normalised_scenes = []

    for index, scene in enumerate(
        scenes,
        start=1
    ):

        if not isinstance(
            scene,
            dict
        ):
            continue

        narration = scene.get(
            "narration",
            []
        )

        if isinstance(
            narration,
            str
        ):

            narration = [
                narration
            ]

        if not isinstance(
            narration,
            list
        ):

            narration = []

        clean_narration = []

        for item in narration:

            value = str(
                item
            ).strip()

            if not value:
                continue

            clean_narration.append(
                convert_math_to_spoken_words(
                    value
                )
            )

        if not clean_narration:
            continue

        normalised_scenes.append({

            "scene_number":
                scene.get(
                    "scene_number",
                    index
                ),

            "module":
                str(
                    scene.get(
                        "module",
                        "Core Material"
                    )
                ).strip(),

            "title":
                str(
                    scene.get(
                        "title",
                        f"Scene {index}"
                    )
                ).strip(),

            "scene_type":
                str(
                    scene.get(
                        "scene_type",
                        "discovery"
                    )
                ).strip(),

            "teaching_intent":
                str(
                    scene.get(
                        "teaching_intent",
                        ""
                    )
                ).strip(),

            "human_entry":
                str(
                    scene.get(
                        "human_entry",
                        ""
                    )
                ).strip(),

            "situation":
                str(
                    scene.get(
                        "situation",
                        ""
                    )
                ).strip(),

            "problem":
                str(
                    scene.get(
                        "problem",
                        ""
                    )
                ).strip(),

            "necessity":
                str(
                    scene.get(
                        "necessity",
                        ""
                    )
                ).strip(),

            "reveal":
                str(
                    scene.get(
                        "reveal",
                        ""
                    )
                ).strip(),

            "technical_concept":
                str(
                    scene.get(
                        "technical_concept",
                        ""
                    )
                ).strip(),

            "question":
                convert_math_to_spoken_words(
                    str(
                        scene.get(
                            "question",
                            ""
                        )
                    ).strip()
                ),

            "question_breakdown":
                convert_math_to_spoken_words(
                    str(
                        scene.get(
                            "question_breakdown",
                            ""
                        )
                    ).strip()
                ),

            "narration":
                clean_narration,

            "key_takeaway":
                convert_math_to_spoken_words(
                    str(
                        scene.get(
                            "key_takeaway",
                            ""
                        )
                    ).strip()
                )
        })

    return {
        "metadata": metadata,
        "scenes": normalised_scenes
    }


# ============================================================
# SOURCE PROMPT
# ============================================================

def _build_source_prompt(
    text_content: str,
    subject_name: str
) -> str:

    source = _clean_source_text(
        text_content
    )

    return f"""
SUBJECT:
{subject_name}

============================================================
SOURCE MATERIAL
============================================================

The following material is the factual source of truth.

Do NOT blindly reproduce it.

Transform it into a human-first DakshAI learning journey.

---------------- SOURCE START ----------------

{source}

---------------- SOURCE END ----------------


============================================================
YOUR TASK
============================================================

Turn this source into an audio-first learning experience.

The learner may know NOTHING about the topic.

Therefore, do NOT start from the terminology or the structure
of the PDF.

Start from the learner's world.

For every major concept:

1. Find the simplest human situation that exposes the idea.
2. Let something happen in that situation.
3. Create a genuine "wait, why?" moment.
4. Expose the underlying problem.
5. Let the learner naturally consider what they would try.
6. Show the limitation.
7. Create the need for a better idea.
8. Reveal the technical concept.
9. Break it into small pieces.
10. Introduce technical vocabulary only when necessary.
11. Return to the actual source material.
12. Cover the required technical depth.
13. End with a memorable mental anchor.

IMPORTANT:

The first part of the scene must NOT sound like a textbook.

Do not begin with:

"Today we will learn..."

"In this concept..."

"A Transformer is..."

"According to the source..."

"The key concept is..."

Do not begin with difficult English terminology.

The learner should understand the situation even if they
have never heard the technical term.

============================================================
LANGUAGE
============================================================

Use natural Indian conversational English/Hinglish.

Do not make every sentence Hindi.

Do not make every sentence formal English.

Use simple language first.

Introduce technical English gradually.

Example:

"Imagine..."

"Ab problem yahan aati hai..."

"Think about what your brain just did."

"Now imagine a computer has to do the same thing."

"That's where the idea of attention comes in."

Then technical explanation.

Do NOT translate technical terms unnaturally.

============================================================
SOURCE FIDELITY
============================================================

Preserve all important source-grounded:

- concepts
- definitions
- formulas
- mechanisms
- distinctions
- examples
- technical terminology
- relationships
- important qualifications

The story is the doorway.

The source remains the knowledge.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use:

{{
  "metadata": {{
    "subject": "",
    "title": "",
    "topics": []
  }},
  "scenes": [
    {{
      "scene_number": 1,
      "module": "",
      "title": "",
      "scene_type": "discovery",
      "teaching_intent": "",
      "human_entry": "",
      "situation": "",
      "problem": "",
      "necessity": "",
      "reveal": "",
      "technical_concept": "",
      "question": "",
      "question_breakdown": "",
      "narration": [
        "...",
        "...",
        "..."
      ],
      "key_takeaway": ""
    }}
  ]
}}

Remember:

The JSON structure is for DakshAI internally.

The narration must feel like one continuous conversation.

NEVER read the structure aloud.

NEVER say:

"Human entry."

"Situation."

"Problem."

"Necessity."

"Reveal."

"Question breakdown."

Those are internal fields, not narration.
"""


# ============================================================
# GEMINI GENERATION
# ============================================================

def _generate_with_gemini(
    text_content: str,
    subject_name: str
) -> Optional[Dict[str, Any]]:

    client = _get_gemini_client()

    if client is None:
        return None

    prompt = _build_source_prompt(
        text_content=text_content,
        subject_name=subject_name
    )

    model_name = os.getenv(
        "DAKSHAI_GEMINI_MODEL",
        "gemini-1.5-flash"
    )

    try:

        response = client.models.generate_content(

            model=model_name,

            contents=prompt,

            config={

                "system_instruction":
                    VOCAL_LEARNING_SYSTEM_PROMPT,

                "temperature":
                    0.65,

                "response_mime_type":
                    "application/json"
            }
        )

        response_text = getattr(
            response,
            "text",
            None
        )

        if not response_text:
            return None

        result = _extract_json(
            response_text
        )

        if result is None:
            return None

        return _normalise_result(
            result
        )

    except Exception as exc:

        logger.exception(
            "Gemini vocal learning generation failed: %s",
            exc
        )

        return None


# ============================================================
# FALLBACK
# ============================================================

def build_fallback_vocal_content(
    text_content: str,
    subject_name: str = "General"
) -> Dict[str, Any]:

    """
    Fallback should still preserve the new philosophy.

    It must NEVER manufacture:

        Question
        → Breakdown
        → Answer

    because that would reintroduce the exact machine-like
    behaviour we are trying to remove.

    Since a deterministic fallback cannot invent a rich
    story safely, it produces a gentle source-grounded
    entry instead of pretending to have generated a story.
    """

    source = _clean_source_text(
        text_content
    )

    if not source:

        return {
            "metadata":
                _empty_metadata(
                    subject_name
                ),
            "scenes": []
        }

    paragraphs = re.split(
        r"\n\s*\n",
        source
    )

    scenes = []

    for index, paragraph in enumerate(
        paragraphs,
        start=1
    ):

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Keep fallback reasonably sized.
        if len(paragraph) > 3500:
            paragraph = paragraph[:3500]

        spoken = convert_math_to_spoken_words(
            paragraph
        )

        first_line = (
            paragraph
            .split("\n")[0]
            .strip()
        )

        first_line = first_line[:80]

        scenes.append({

            "scene_number":
                index,

            "module":
                f"{subject_name} Section {index}",

            "title":
                first_line or
                f"Scene {index}",

            "scene_type":
                "source_explanation",

            "teaching_intent":
                "Introduce the source material without "
                "pretending to have created a story.",

            "human_entry":
                "Let's first see what this idea is actually "
                "talking about.",

            "situation":
                "",

            "problem":
                "",

            "necessity":
                "",

            "reveal":
                "",

            "technical_concept":
                first_line,

            "question":
                "",

            "question_breakdown":
                "",

            "narration": [

                (
                    "Let's first get a clear picture of "
                    "what we're looking at."
                ),

                spoken

            ],

            "key_takeaway":
                (
                    "Keep this idea connected to the "
                    "actual situation we just explored."
                )
        })

    return {

        "metadata": {

            "subject":
                subject_name,

            "title":
                f"{subject_name} Vocal Learning",

            "topics":
                []
        },

        "scenes":
            scenes
    }


# ============================================================
# MAIN PUBLIC FUNCTIONS
# ============================================================

def generate_movie_cheatsheet_from_text(
    input_content: str,
    subject_name: str = "General"
) -> Dict[str, Any]:

    text_content = input_content

    # If input is a PDF path
    if (
        isinstance(input_content, str)
        and (
            input_content.endswith(".pdf")
            or os.path.exists(input_content)
        )
    ):

        extracted = extract_text_from_pdf_file(
            input_content
        )

        if extracted:

            text_content = extracted

            if subject_name == "General":

                subject_name = (
                    os.path.basename(
                        input_content
                    )
                    .replace(".pdf", "")
                    .replace("_", " ")
                )

    if (
        not text_content
        or not text_content.strip()
    ):

        return {
            "metadata":
                _empty_metadata(
                    subject_name
                ),
            "scenes": []
        }

    try:

        result = _generate_with_gemini(
            text_content=text_content,
            subject_name=subject_name
        )

        if result and result.get("scenes"):

            return result

        return build_fallback_vocal_content(
            text_content=text_content,
            subject_name=subject_name
        )

    except Exception as exc:

        logger.exception(
            "Vocal learning generation failed: %s",
            exc
        )

        return build_fallback_vocal_content(
            text_content=text_content,
            subject_name=subject_name
        )


def generate_vocal_learning_content(
    input_content: str,
    subject_name: str = "General"
) -> Dict[str, Any]:

    return generate_movie_cheatsheet_from_text(
        input_content=input_content,
        subject_name=subject_name
    )