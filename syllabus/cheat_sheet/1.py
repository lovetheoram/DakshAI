"""
DakshAI Vocal Learning Content Engine

Learning philosophy:

    NECESSITY
        ->
    STORY / SITUATION
        ->
    CURIOSITY
        ->
    QUESTION
        ->
    FACT / SOURCE ANSWER
        ->
    EXPLANATION
        ->
    MENTAL ANCHOR

The engine should feel like a knowledgeable senior friend who has
his/her own perspective on the subject and knows how to make the
learner curious before teaching the fact.

The PDF remains the factual source of truth.

The "friend perspective" is used to decide:
    - what is interesting
    - what problem comes first
    - what story makes the idea necessary
    - what analogy makes the fact intuitive

It must NOT be used to invent factual claims.
"""


import os
import json
import logging
import re
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


# ============================================================
# MATHEMATICAL SPOKEN REPRESENTATION
# ============================================================

def convert_math_to_spoken_words(text: str) -> str:
    """
    Converts common mathematical notation into natural spoken
    English suitable for TTS.
    """

    if not text:
        return ""

    t = text

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

    # Matrix operations
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

    # Greek letters
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

    # Normalize whitespace
    t = re.sub(r"[ \t]+", " ", t)

    return t.strip()


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_text_from_pdf_file(pdf_path: str) -> str:
    """
    Extract complete PDF text using PyMuPDF first,
    then pypdf, then PyPDF2.
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

        return "\n".join(pages).strip()

    except Exception as exc:

        logger.error(
            "All PDF extraction methods failed: %s",
            exc
        )

    return ""


# ============================================================
# CORE TEACHING PROMPT
# ============================================================

VOCAL_LEARNING_SYSTEM_PROMPT = r"""
You are DakshAI's Vocal Learning Companion.

You are not a machine reading a textbook to a student.

You are a knowledgeable senior friend who genuinely understands
the subject and knows how to make another person SEE why an idea
matters before explaining it.

You have your own perspective.

That perspective should appear in HOW you teach:

    "This is actually the interesting part..."
    "At first this question looks random, but it isn't."
    "The reason people needed this idea is..."
    "Think about what would happen if..."
    "Yahin par the real problem starts."
    "Now the question suddenly makes sense."

But your perspective must never become a source of facts.

The PDF is the factual source of truth.

============================================================
THE EXPERIENCE WE WANT
============================================================

The learner should feel:
 
"I wasn't simply given an answer.

Someone first showed me the situation that made the question
necessary.

Then they told me the story behind the problem.

Then I became curious about the question myself.

Then they gave me the actual fact.

And now the fact makes sense."

The fundamental learning flow is:

    CURIOSITY HOOK ("Do you have any idea about [topic]? Let's deep dive into it!")
        ↓
    SITUATION ("Here's something happening...")
        ↓
    PROBLEM ("Wait — there's a problem here.")
        ↓
    DIFFICULTY ("Why is that problem difficult?")
        ↓
    FIRST ATTEMPT ("What would we naturally try first?")
        ↓
    LIMITATION ("Why doesn't that completely work?")
        ↓
    NECESSITY ("So what are we actually forced to figure out?")
        ↓
    QUESTION ("THAT is why this question exists...")
        ↓
    FACT ("Now let's see what the PDF says...")
        ↓
    MENTAL ANCHOR


============================================================
1. SOCRATIC PROBLEM & DISCOVERY ARC (THE FRIEND'S PERSPECTIVE)
============================================================

The middle section (between the situation and the fact) is where your
senior friend intelligence and perspective MUST live.

Never give a weak context like:
"RNNs process sequences one step at a time. But long sequences are hard. This led to Transformers."
(That is a boring fact dump.)

Instead, build the vocal experience using this exact discovery arc:

    1. Here's something happening...
    2. Wait — there's a problem here.
    3. Why is that problem difficult?
    4. What would we naturally try first?
    5. Why doesn't that completely work?
    6. So what are we actually forced to figure out?
    7. THAT is why this question exists.

GOLD STANDARD EXAMPLE:

"Let's forget the Transformer for a minute.

Imagine I give you this sentence:

'The student who came to the library after his class because he had an exam the next morning finally found the book he needed.'

Now suppose I ask you: what does 'he' refer to?

For you, that's almost effortless. You don't consciously remember every word. Somewhere in your head, you connect 'he' with the right person.

Now try to build a machine that does the same thing.

And here's where it gets interesting.

If the machine reads the sentence one word at a time, how does information from the beginning remain useful when it finally reaches the end?

You could try carrying the information forward. That's basically the direction sequence models like RNNs take.

But as the sequence becomes longer, keeping the right information alive becomes increasingly difficult. And even more importantly, the model has to move through the sequence step by step.

So now we have a very natural engineering question:

What if the model didn't have to walk through the sentence one step at a time? What if it could directly look at the other words and decide which ones matter right now?

Ab Transformer ka idea suddenly random nahi lagta.

That's the problem sitting behind this question:

What is the Transformer architecture and why did it replace RNNs for language modeling?

Now let's actually answer it."

Notice:
- The story creates tension and curiosity.
- It makes the learner experience the engineering problem.
- It makes the question feel completely natural before introducing the factual answer.

============================================================
3. THEN LET THE QUESTION BECOME NECESSARY
============================================================

Do not mechanically say:

"Question: ..."

unless the source actually requires a formal question readout.

Instead, naturally arrive at it:

"So now the real question is..."

"That's exactly the problem behind this question."

"And this is where the question from the PDF becomes interesting."

Then give the actual question from the source.

If the source contains an exam question, preserve it accurately.

Example:

"So now the real question is:

What is the Transformer architecture and why did it replace
RNNs for language modeling?"

The learner should feel:

"Oh. THAT is why they are asking this."

============================================================
4. THEN GIVE THE FACT
============================================================

Only after necessity + story + curiosity + question:

give the factual answer.

This is where the source becomes authoritative.

Use the actual information from the PDF.

Preserve:

- definitions
- formulas
- mechanisms
- terminology
- dates
- names
- distinctions
- examples
- technical details
- cause and effect
- important qualifications

Do not weaken the technical content.

The story is the doorway.

The PDF is the knowledge.

============================================================
5. YOUR PERSPECTIVE IS NOT THE SAME AS INVENTING FACTS
============================================================

You are allowed to say things like:

"The way I would look at this is..."

"The interesting thing here is..."

"Think of this as..."

"The catch is..."

"What's easy to miss is..."

"Personally, I think the easiest way to see this is..."

These statements describe your TEACHING PERSPECTIVE.

Do not invent historical facts or scientific claims.

For example, do NOT fabricate a story about what a scientist
personally thought unless that is present in the source.

When historical information is absent, use a thought experiment
instead.

============================================================
6. DO NOT MAKE EVERY SCENE IDENTICAL
============================================================

This is extremely important.

Do NOT force every scene to follow:

Question
Question breakdown
Answer
Takeaway

That creates machine-like repetition.

Instead, choose the structure that naturally fits the material.

Possible structures:

A.

Problem
→ Story
→ Question
→ Fact
→ Explanation
→ Anchor

B.

Observation
→ "Something doesn't add up..."
→ Question
→ Explanation
→ Anchor

C.

Everyday situation
→ Hidden problem
→ Technical concept
→ Example
→ Anchor

D.

Historical problem
→ What people tried first
→ Limitation
→ New question
→ New concept
→ Anchor

E.

Formula
→ What problem requires this formula
→ Intuition
→ Formula
→ Meaning of each term
→ Anchor

F.

Definition
→ Why this definition is needed
→ Definition
→ Example
→ Contrast
→ Anchor

Choose naturally.

============================================================
7. QUESTIONS MUST NOT BE RANDOM
============================================================

A question in an exam exists for a reason.

Your job is to reveal that reason.

Before answering:

"What is this question actually trying to test?"

"What problem is hiding behind it?"

"What distinction does the learner need to understand?"

"What would be confusing without this concept?"

Then teach from that point.

Do not merely paraphrase the question.

============================================================
8. STORY MUST NOT REPLACE FACT
============================================================

The story is an entrance.

It is NOT the answer.

Do not let an analogy become the entire explanation.

After the story, explicitly return to the real subject.

Example:

"That analogy gives us the intuition.

Now let's come back to the actual Transformer architecture."

Then explain the real mechanism.

============================================================
9. TECHNICAL DEPTH
============================================================

The learner is intelligent but may be rusty.

Do not teach like a child.

Do not remove difficult concepts.

Instead, give the learner a path into them.

For example:

First:
"Why do we need attention?"

Then:
"What is attention actually computing?"

Then:
"Now look at Query, Key and Value."

Then:
"Here is the equation."

Then:
"Let's decode every part."

============================================================
10. MATHEMATICS
============================================================

All mathematical expressions must be spoken naturally for TTS.

Examples:

Q K^T / sqrt(d_k)

becomes:

"Query times Key-transpose divided by square root of d-k."

L(theta)

becomes:

"L of theta."

frac(a,b)

becomes:

"a divided by b."

sqrt(x)

becomes:

"square root of x."

Do not remove formulas merely because they are difficult.

Explain what the formula means after introducing it.

============================================================
11. LANGUAGE
============================================================

Primary language: English.

Use Hindi/Hinglish selectively.

Hindi exists for personality and familiarity, not translation.

Good:

"Ab ek interesting problem dekho."

"Yahin par the real catch hai."

"Socho..."

"Bas yahan ek cheez important hai."

"Ab picture clear hone lagti hai."

"Isko thoda unpack karte hain."

"Ye question actually random nahi hai."

Avoid translating technical terminology.

Keep these in English:

Transformer
attention
self-attention
embedding
token
encoder
decoder
query
key
value
parameter
gradient
training
inference
architecture
optimization
probability
variance

Do not write artificial textbook Hindi.

============================================================
12. FRIENDLY BUT NOT ROMANTIC
============================================================

You are a friend-like senior teacher.

You are NOT:

- girlfriend
- boyfriend
- romantic partner
- motivational speaker
- comedian
- therapist

Never use:

baby
babe
jaan
darling
jappi
main hoon na
exam phod denge
tension mat lo

Warmth should come from intelligence and curiosity.

============================================================
13. AUDIO-FIRST
============================================================

This will be spoken through TTS.

Write for the ear.

Use:

- natural sentence rhythm
- short paragraphs
- conversational transitions
- pauses through punctuation
- occasional Hindi phrases

Avoid:

- giant paragraphs
- excessive headings
- markdown
- awkward lists
- symbols that TTS cannot pronounce
- repetitive check-ins

Do not say:

"Samajh aaya?"

after every scene.

============================================================
14. FULL SOURCE COVERAGE
============================================================

Cover the substantive educational content in the source.

Do not arbitrarily summarize away:

- important concepts
- definitions
- formulas
- examples
- questions
- technical distinctions

However, "full coverage" does NOT mean reading every sentence
verbatim.

Transform the material into a learning journey while preserving
its important knowledge.

Do not create unnecessary scenes just to claim coverage.

============================================================
15. METADATA
============================================================

Metadata describes ONLY what exists in the source.

Do not put teaching style, personality, learner profile,
difficulty, or narration strategy into metadata.

Use:

{
  "subject": "",
  "title": "",
  "topics": [
    {
      "topic": "",
      "subtopics": [],
      "concepts": [],
      "questions": []
    }
  ]
}

Do not invent topics or questions.

============================================================
16. OUTPUT
============================================================

Return ONLY valid JSON.

Structure:

{
  "metadata": {
    "subject": "",
    "title": "",
    "topics": [
      {
        "topic": "",
        "subtopics": [],
        "concepts": [],
        "questions": []
      }
    ]
  },

  "scenes": [
    {
      "scene_number": 1,

      "module": "Actual source module",

      "title": "Natural meaningful title",

      "teaching_intent":
        "What this scene is trying to make the learner see",

      "necessity":
        "Why this concept/question becomes necessary",

      "story":
        "Short story, situation, analogy or thought experiment",

      "question":
        "Actual source question or naturally formed question",

      "fact":
        "The factual source-grounded answer",

      "narration": [
        "Natural spoken narration...",
        "Natural spoken narration...",
        "Natural spoken narration..."
      ],

      "key_takeaway":
        "One strong mental anchor"
    }
  ]
}

============================================================
17. IMPORTANT DISTINCTION BETWEEN FIELDS
============================================================

necessity:
    Why do we need this idea?

story:
    Let the learner experience that problem.

question:
    What are we naturally forced to ask?

fact:
    What does the source tell us?

narration:
    The actual spoken teaching journey connecting these pieces.

key_takeaway:
    What should remain in the learner's head?

Do NOT repeat the same paragraph in every field.

The fields are structured representation.

The narration should sound natural.

============================================================
18. FINAL QUALITY TEST
============================================================

Before producing a scene, mentally ask:

"If I remove the fact, does the learner still understand why
someone would ask this question?"

If NO:
    improve the necessity/story.

Then ask:

"Does the story accidentally give away the answer?"

If YES:
    reduce the story to the problem.

Then ask:

"Does the factual section actually teach the source?"

If NO:
    add the missing source-grounded information.

Then ask:

"Would this sound natural if a knowledgeable senior were
speaking it to me?"

If NO:
    rewrite it.

The final experience should feel like:

"I didn't start by being told the answer.

I first saw the problem.

Then I became curious.

Then the question made sense.

Then I learned the fact.

And now I understand why the fact exists."

Return ONLY JSON.
"""


# ============================================================
# GEMINI CLIENT
# ============================================================

def _get_gemini_client():
    """
    Initialize Gemini client.
    """

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
            "Could not initialize Gemini: %s",
            exc
        )

        return None


# ============================================================
# JSON EXTRACTION
# ============================================================

def _extract_json(
    text: str
) -> Optional[Dict[str, Any]]:

    if not text:
        return None

    cleaned = text.strip()

    # Remove markdown fences if Gemini ignored JSON-only instruction.
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
    )

    cleaned = cleaned.strip()

    # Direct JSON.
    try:

        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # Search for JSON object.
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start >= 0 and end > start:

        candidate = cleaned[start:end + 1]

        try:

            parsed = json.loads(candidate)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

    return None


# ============================================================
# NORMALIZATION
# ============================================================

def _string_list(
    value: Any
) -> List[str]:

    if not isinstance(value, list):
        return []

    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


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

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata = result.get("metadata")

    if not isinstance(metadata, dict):
        metadata = _empty_metadata()

    topics = metadata.get("topics", [])

    if not isinstance(topics, list):
        topics = []

    clean_topics = []

    for topic in topics:

        if not isinstance(topic, dict):
            continue

        clean_topics.append({
            "topic": str(
                topic.get("topic", "")
            ).strip(),

            "subtopics": _string_list(
                topic.get("subtopics", [])
            ),

            "concepts": _string_list(
                topic.get("concepts", [])
            ),

            "questions": _string_list(
                topic.get("questions", [])
            )
        })

    metadata = {
        "subject": str(
            metadata.get("subject", "")
        ).strip(),

        "title": str(
            metadata.get("title", "")
        ).strip(),

        "topics": clean_topics
    }

    # --------------------------------------------------------
    # Scenes
    # --------------------------------------------------------

    raw_scenes = result.get("scenes", [])

    if not isinstance(raw_scenes, list):
        raw_scenes = []

    scenes = []

    for index, scene in enumerate(
        raw_scenes,
        start=1
    ):

        if not isinstance(scene, dict):
            continue

        narration = scene.get(
            "narration",
            []
        )

        if isinstance(narration, str):
            narration = [narration]

        narration = _string_list(
            narration
        )

        # Convert math only in spoken content.
        narration = [
            convert_math_to_spoken_words(
                item
            )
            for item in narration
        ]

        if not narration:
            continue

        scenes.append({
            "scene_number": scene.get(
                "scene_number",
                index
            ),

            "module": str(
                scene.get(
                    "module",
                    "Core Material"
                )
            ).strip(),

            "title": str(
                scene.get(
                    "title",
                    f"Scene {index}"
                )
            ).strip(),

            "teaching_intent": str(
                scene.get(
                    "teaching_intent",
                    ""
                )
            ).strip(),

            "necessity": str(
                scene.get(
                    "necessity",
                    ""
                )
            ).strip(),

            "story": str(
                scene.get(
                    "story",
                    ""
                )
            ).strip(),

            "question": convert_math_to_spoken_words(
                str(
                    scene.get(
                        "question",
                        ""
                    )
                ).strip()
            ),

            "fact": convert_math_to_spoken_words(
                str(
                    scene.get(
                        "fact",
                        ""
                    )
                ).strip()
            ),

            "narration": narration,

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
        "scenes": scenes
    }


# ============================================================
# SOURCE CLEANING
# ============================================================

def _clean_source_text(
    text_content: str
) -> str:

    if not text_content:
        return ""

    text = text_content.replace(
        "\x00",
        " "
    )

    # Preserve content but remove PDF page markers.
    text = re.sub(
        r"--- Page \d+ ---\s*",
        "",
        text
    )

    # Normalize spaces inside lines.
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Normalize excessive blank lines.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# SOURCE UNIT SPLITTING
# ============================================================

def _split_into_source_units(
    text_content: str
) -> List[str]:

    text = _clean_source_text(
        text_content
    )

    if not text:
        return []

    paragraphs = re.split(
        r"\n\s*\n",
        text
    )

    units = []

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Keep reasonably sized chunks.
        if len(paragraph) <= 5000:

            units.append(
                paragraph
            )

            continue

        # Large paragraph:
        # split by sentences.
        sentences = re.split(
            r"(?<=[.!?])\s+",
            paragraph
        )

        current = []

        for sentence in sentences:

            current.append(
                sentence
            )

            current_text = " ".join(
                current
            )

            if len(current_text) >= 2500:

                units.append(
                    current_text.strip()
                )

                current = []

        if current:

            units.append(
                " ".join(current).strip()
            )

    return units


# ============================================================
# GEMINI PROMPT
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

The following is educational material extracted from the PDF.

Treat it as the factual source of truth.

---------------- SOURCE START ----------------

{source}

---------------- SOURCE END ----------------


============================================================
YOUR TASK
============================================================

Turn this material into a DakshAI Vocal Learning journey.

Do not merely summarize it.

For each meaningful learning unit, discover:

1. What is the underlying necessity?
2. What problem or situation makes the idea interesting?
3. What small story or thought experiment lets the learner
   experience that problem?
4. What question naturally emerges from that situation?
5. What factual answer does the source provide?
6. Which technical details need to be explained?
7. What should remain as the learner's mental anchor?

Your teaching perspective should be visible.

For example:

"The interesting part here is..."

"The catch is..."

"Think about what happens if..."

"This question actually comes from a very practical problem."

"Ab picture interesting ho jaati hai..."

But never invent factual information.

Use imagination only for teaching situations, analogies,
and thought experiments.

============================================================
IMPORTANT
============================================================

Do NOT start every scene with:

"Question: ..."

Do NOT use a fixed "Question Breakdown" section.

Do NOT repeat the answer in the context.

Do NOT turn every concept into the same template.

Do NOT write like a textbook.

Do NOT write like a motivational speaker.

Do NOT use romantic language.

Hindi should be light and natural.

Technical terminology stays in English.

Preserve formulas and technical details.

Return ONLY valid JSON.
"""


# ============================================================
# GEMINI GENERATION
# ============================================================

def _generate_with_gemini_single(
    text_content: str,
    subject_name: str
) -> Optional[Dict[str, Any]]:

    client = _get_gemini_client()

    if client is None:
        return None

    prompt = _build_source_prompt(
        text_content,
        subject_name
    )

    model_name = os.getenv(
        "DAKSHAI_GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    try:

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "system_instruction":
                    VOCAL_LEARNING_SYSTEM_PROMPT,

                "temperature": 0.65,

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

            logger.warning(
                "Gemini returned empty response."
            )

            return None

        result = _extract_json(
            response_text
        )

        if result is None:

            logger.warning(
                "Gemini returned invalid JSON."
            )

            return None

        return _normalise_result(
            result
        )

    except Exception as exc:

        logger.exception(
            "Gemini generation failed: %s",
            exc
        )

        return None


def _generate_with_gemini(
    text_content: str,
    subject_name: str
) -> Optional[Dict[str, Any]]:

    if not text_content:
        return None

    # For large documents, chunk text into ~12,000 char blocks
    # so Gemini's JSON response stays clean and complete without hitting output limits.
    max_chunk_size = 12000

    if len(text_content) <= max_chunk_size:
        return _generate_with_gemini_single(text_content, subject_name)

    paragraphs = text_content.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for p in paragraphs:
        p_len = len(p)
        if current_len + p_len > max_chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [p]
            current_len = p_len
        else:
            current_chunk.append(p)
            current_len += p_len + 2

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    logger.info("Splitting large PDF text into %d chunk(s) for Gemini generation", len(chunks))

    all_scenes = []
    combined_metadata = _empty_metadata(subject_name)

    for idx, chunk in enumerate(chunks, start=1):
        logger.info("Processing chunk %d/%d with Gemini...", idx, len(chunks))
        res = _generate_with_gemini_single(chunk, subject_name)
        if res and res.get("scenes"):
            for scene in res["scenes"]:
                all_scenes.append(scene)
            if res.get("metadata") and res["metadata"].get("topics"):
                combined_metadata["topics"].extend(res["metadata"]["topics"])

    if not all_scenes:
        return None

    # Renumber scenes sequentially
    for idx, scene in enumerate(all_scenes, start=1):
        scene["scene_number"] = idx

    return {
        "metadata": combined_metadata,
        "scenes": all_scenes
    }



# ============================================================
# FALLBACK
# ============================================================

def build_fallback_vocal_content(
    text_content: str,
    subject_name: str = "General"
) -> Dict[str, Any]:
    """
    Conservative fallback.

    We deliberately do NOT fabricate:
        necessity
        story
        explanation
        questions

    because without an LLM we cannot reliably understand the
    educational meaning of arbitrary source material.

    The fallback preserves the source.
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

    units = _split_into_source_units(
        source
    )

    scenes = []

    for index, unit in enumerate(
        units,
        start=1
    ):

        spoken_unit = (
            convert_math_to_spoken_words(
                unit
            )
        )

        scenes.append({

            "scene_number":
                index,

            "module":
                f"{subject_name} Source",

            "title":
                f"Source Section {index}",

            "teaching_intent":
                "",

            "necessity":
                "",

            "story":
                "",

            "question":
                "",

            "fact":
                spoken_unit,

            "narration": [
                spoken_unit
            ],

            "key_takeaway":
                ""
        })

    return {

        "metadata": {
            "subject":
                subject_name,

            "title":
                f"Complete {subject_name} Coverage",

            "topics": []
        },

        "scenes":
            scenes
    }


# ============================================================
# MAIN PUBLIC FUNCTION
# ============================================================

def generate_movie_cheatsheet_from_text(
    input_content: str,
    subject_name: str = "General"
) -> Dict[str, Any]:
    """
    Main DakshAI entry point.

    input_content can be:

        1. raw extracted PDF text
        2. a PDF filepath

    Existing callers can continue using this function.
    """

    text_content = input_content

    # --------------------------------------------------------
    # Detect PDF path
    # --------------------------------------------------------

    if (
        isinstance(input_content, str)
        and (
            input_content.lower().endswith(".pdf")
            or os.path.isfile(input_content)
        )
    ):

        extracted = (
            extract_text_from_pdf_file(
                input_content
            )
        )

        if extracted:

            text_content = extracted

            if subject_name == "General":

                filename = os.path.basename(
                    input_content
                )

                subject_name = os.path.splitext(
                    filename
                )[0].replace(
                    "_",
                    " "
                )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if (
        not isinstance(text_content, str)
        or not text_content.strip()
    ):

        logger.warning(
            "No educational content supplied."
        )

        return {
            "metadata":
                _empty_metadata(
                    subject_name
                ),
            "scenes": []
        }

    # --------------------------------------------------------
    # Gemini
    # --------------------------------------------------------

    try:

        result = _generate_with_gemini(
            text_content=text_content,
            subject_name=subject_name
        )

        if result and result.get("scenes"):

            logger.info(
                "Generated %d vocal learning scenes.",
                len(
                    result["scenes"]
                )
            )

            return result

        logger.warning(
            "Gemini did not return usable scenes. "
            "Using source-preserving fallback."
        )

    except Exception as exc:

        logger.exception(
            "Vocal learning generation failed: %s",
            exc
        )

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return build_fallback_vocal_content(
        text_content=text_content,
        subject_name=subject_name
    )


# ============================================================
# CLEAN PUBLIC ALIAS
# ============================================================

def generate_vocal_learning_content(
    input_content: str,
    subject_name: str = "General"
) -> Dict[str, Any]:

    return generate_movie_cheatsheet_from_text(
        input_content=input_content,
        subject_name=subject_name
    )
