import os

QUESTIONS = [
    {"id": "experience", "en": "How was your experience at NASA Space Apps Cairo?", "rating": True},
]
# Keep old responses and already-open participant pages compatible during deployment.
LEGACY_QUESTIONS = {"q1": "What was the most valuable part of the event for you?"}

VOCAB = "NASA Space Apps Cairo, hackathon, mentor, workshop, judges, IEEE Young Professionals Egypt, One Spark Infinite Impact"
PROMPT = (
    "Transcribe faithfully in the original language, without translating. "
    "The speaker may use English, Egyptian Arabic, or switch between both. "
    "حافظ على الكلام بالمصري والإنجليزي زي ما اتقال، من غير ترجمة. "
    "Event vocabulary: " + VOCAB
)
MODEL = os.getenv("TRANSCRIBE_MODEL", "gpt-4o-transcribe")

PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "openai").strip().lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
