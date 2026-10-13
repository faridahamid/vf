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

AUDIENCES = {
    "participant": {"label": "Participants", "intro": "You made the experience. Now help shape what comes next. Rate your experience and, if you like, share a moment, an idea, or something we can do better.", "question": QUESTIONS[0]},
    "speaker": {"label": "Speakers", "intro": "Your ideas sparked new perspectives. Help us make the stage even better. Share your experience of preparing, presenting, and connecting with our community.", "question": {"id": "speaker_experience", "en": "How was your experience as a speaker at NASA Space Apps Cairo?", "rating": True}},
    "volunteer": {"label": "Volunteers", "intro": "Your energy kept the event moving. Help us support the next volunteer team. Tell us about coordination, your responsibilities, and the support you received.", "question": {"id": "volunteer_experience", "en": "How was your experience volunteering at NASA Space Apps Cairo?", "rating": True}},
    "mentor": {"label": "Mentors", "intro": "Your guidance helped teams turn ideas into possibilities. Help us improve the mentoring experience. Share what worked, what was challenging, and how we can better support you.", "question": {"id": "mentor_experience", "en": "How was your experience mentoring teams at NASA Space Apps Cairo?", "rating": True}},
    "judge": {"label": "Judges", "intro": "Your perspective helped recognize promising ideas. Help us improve the judging experience. Tell us about the criteria, presentations, and organization of the evaluation process.", "question": {"id": "judge_experience", "en": "How was your experience judging projects at NASA Space Apps Cairo?", "rating": True}},
}
