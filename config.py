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


# Rating questions transcribed from the supplied speaker Google Form.
SPEAKER_QUESTIONS = [
    {"id": "speaker_experience", "en": "How would you rate your overall experience as a speaker?", "rating": True, "scale_labels": ["Very Poor", "", "", "", "Excellent"]},
    {"id": "speaker_support", "en": "How would you rate the support you received from the organizing team before and during the event?", "rating": True, "scale_labels": ["", "", "", "", ""]},
    {"id": "speaker_communication", "en": "How clear were the guidelines and communication provided before the event?", "rating": True, "scale_labels": ["", "", "", "", ""]},
    {"id": "speaker_session_reception", "en": "How well do you feel your session was received by participants?", "rating": True, "scale_labels": ["Not at all", "", "", "", "Extremely well"]},
    {"id": "speaker_future_engagement", "en": "How likely are you to join NASA Space Apps Cairo again as a speaker or mentor?", "rating": True, "scale_labels": ["Not likely", "", "", "", "Definitely"]},
]
AUDIENCES["speaker"]["questions"] = SPEAKER_QUESTIONS


def audience_questions(role):
    audience = AUDIENCES[role]
    return audience.get("questions", [audience["question"]])


def question_titles():
    # Include retired questions so historical exports retain their wording.
    titles = {**LEGACY_QUESTIONS, **{a["question"]["id"]: a["question"]["en"] for a in AUDIENCES.values()}}
    titles.update({q["id"]: q["en"] for role in AUDIENCES for q in audience_questions(role)})
    return titles

WORKSHOPS = ['AI and Machine Learning', 'AI Tools in Hackathon', 'Critical Thinking', 'Data Integration & API', 'Data Visualization and analysis', 'Game & Simulation Design', 'GIS remote sensing', 'Global Winner Story', 'NASA Data', 'Show it Clearly', 'Storytelling', 'UI/UX', 'Video Editing', 'Web as tool']


# Volunteer observations transcribed from the organizer's screenshots.
VOLUNTEER_QUESTIONS = [
    {"id": "volunteer_engagement", "en": "The speaker kept the audience engaged (no side talks, participants attentive).", "section": "Audience engagement"},
    {"id": "volunteer_participation", "en": "The speaker answered questions clearly and encouraged participation.", "section": "Audience engagement"},
    {"id": "volunteer_agenda", "en": "The session aligned with the proposed agenda.", "section": "Alignment", "required": False},
    {"id": "volunteer_subjects", "en": "The session covered the planned subjects effectively.", "section": "Alignment", "options": ["Yes", "No"]},
    {"id": "volunteer_technical_level", "en": "The content was technically appropriate (easy to follow, basic when needed).", "section": "Alignment"},
    {"id": "volunteer_challenge_application", "en": "The speaker explained how to use the solution in the challenges.", "section": "Alignment", "options": ["Yes", "No"]},
    {"id": "volunteer_communication", "en": "The speaker was easy to communicate with.", "section": "Communication"},
    {"id": "volunteer_cooperation", "en": "The speaker was reachable and cooperative throughout the process.", "section": "Communication"},
    {"id": "volunteer_time_management", "en": "The speaker managed time effectively throughout the session.", "section": "General performance"},
    {"id": "volunteer_session_flow", "en": "The beginning and end of the session were managed well.", "section": "General performance"},
    {"id": "volunteer_audience_questions", "en": "The speaker handled audience questions effectively.", "section": "General performance"},
    {"id": "volunteer_delivery", "en": "The overall delivery of the session was professional and effective.", "section": "General performance"},
    {"id": "volunteer_recommendation", "en": "Based on your experience, would you recommend welcoming this speaker again next year?", "section": "General performance", "options": ["Yes", "No", "Maybe"]},
    {"id": "volunteer_self_promotion", "en": "Does the speaker market themselves too much?", "section": "Additional feedback", "options": ["Yes", "No"]},
]
for question in VOLUNTEER_QUESTIONS:
    question.setdefault("required", True)
    question["rating"] = "options" not in question
    if question["rating"]:
        question["scale_labels"] = ["Strongly Disagree", "", "", "", "Strongly Agree"]
AUDIENCES["volunteer"]["questions"] = VOLUNTEER_QUESTIONS
AUDIENCES["volunteer"]["intro"] = "Share your observations of the session you supported. Choose the workshop, rate the delivery, and help us improve future sessions."
