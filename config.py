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

LEGACY_QUESTIONS.update(question_titles())
LEGACY_FORM_QUESTIONS = {role: list(audience_questions(role)) for role in ("speaker", "volunteer")}

BOOTCAMP_QUESTIONS = {'speaker': [{'id': 'speaker_objectives',
              'en': 'How clearly did the organizing team communicate the session objectives and expected '
                    'outcomes before the event?',
              'section': 'Session Preparation & Coordination',
              'required': True,
              'rating': True,
              'scale_labels': ['1', '', '', '', '5']},
             {'id': 'speaker_communication',
              'en': 'How satisfied were you with the communication, responsiveness, and coordination before '
                    'the session?',
              'section': 'Session Preparation & Coordination',
              'required': True,
              'rating': True,
              'scale_labels': ['1', '', '', '', '5']},
             {'id': 'speaker_duration',
              'en': 'Were the session duration and allocated time sufficient to cover the planned content?',
              'section': 'Session Preparation & Coordination',
              'required': True,
              'options': ['More than enough',
                          'Appropriate',
                          'Slightly insufficient',
                          'Significantly insufficient']},
             {'id': 'speaker_venue',
              'en': 'How would you rate the overall organization and readiness of the venue when you '
                    'arrived?',
              'section': 'Logistics & On-site Support',
              'required': True,
              'rating': True,
              'scale_labels': ['1', '', '', '', '5']},
             {'id': 'speaker_room',
              'en': 'How suitable were the room setup, seating arrangement, and physical environment for '
                    'delivering your session?',
              'section': 'Logistics & On-site Support',
              'required': True,
              'rating': True,
              'scale_labels': ['1', '', '', '', '5']},
             {'id': 'speaker_facilities',
              'en': 'How reliable were the technical facilities, including projector, microphone, internet, '
                    'and presentation setup?',
              'section': 'Logistics & On-site Support',
              'required': True,
              'rating': True,
              'scale_labels': ['1', '', '', '', '5']},
             {'id': 'speaker_support',
              'en': 'How responsive and helpful were the organizing volunteers during your session?',
              'section': 'Logistics & On-site Support',
              'required': True,
              'rating': True,
              'scale_labels': ['1', '', '', '', '5']},
             {'id': 'speaker_issues',
              'en': 'Did you encounter any logistical or technical issues? If yes, how were they handled?',
              'section': 'Logistics & On-site Support',
              'required': True,
              'type': 'paragraph'},
             {'id': 'speaker_outcomes',
              'en': 'To what extent do you believe the attendees achieved the intended learning outcomes?',
              'section': 'Learning Outcomes & Bootcamp Improvement',
              'required': True,
              'rating': True,
              'scale_labels': ['1', '', '', '', '5']},
             {'id': 'speaker_engagement_notes',
              'en': 'Which concepts or activities generated the strongest engagement or understanding?',
              'section': 'Learning Outcomes & Bootcamp Improvement',
              'required': True,
              'type': 'paragraph'},
             {'id': 'speaker_improvements',
              'en': 'What adjustments to the session format, participant preparation, or content depth would '
                    'improve future deliveries?',
              'section': 'Learning Outcomes & Bootcamp Improvement',
              'required': True,
              'type': 'paragraph'},
             {'id': 'speaker_experience',
              'en': 'How satisfied were you with your overall experience as a Bootcamp speaker?',
              'section': 'Overall Experience',
              'required': True,
              'rating': True,
              'scale_labels': ['1', '', '', '', '5']},
             {'id': 'speaker_team_notes',
              'en': 'What should the organizing team keep doing, stop doing, or start doing to improve '
                    'future sessions?',
              'section': 'Overall Experience',
              'required': True,
              'type': 'paragraph'}],
 'volunteer': [{'id': 'volunteer_outline',
                'en': 'To what extent did the speaker cover the agreed session outline and learning '
                      'objectives?',
                'section': 'Session Identification & Delivery',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_accuracy',
                'en': 'How accurate, relevant, and appropriate was the information delivered for the '
                      'attendees’ expected knowledge level?',
                'section': 'Session Identification & Delivery',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_delivery',
                'en': 'How effectively did the speaker structure the content and transition between topics?',
                'section': 'Session Identification & Delivery',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_timing',
                'en': 'Did the speaker finish the planned content within the allocated time without rushing '
                      'or unnecessary delays?',
                'section': 'Session Identification & Delivery',
                'required': True,
                'options': ['Fully', 'Mostly', 'Partially', 'No']},
               {'id': 'volunteer_speaker_notes',
                'en': 'Please share your overall feedback on the speaker, including strengths and areas for '
                      'improvement.',
                'section': 'Session Identification & Delivery',
                'required': True,
                'type': 'paragraph'},
               {'id': 'volunteer_slides',
                'en': 'How clear, readable, and visually organized were the presentation slides?',
                'section': 'Slides & Presentation Materials',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_slide_support',
                'en': 'How effectively did the slides support the speaker’s explanation rather than simply '
                      'repeat large amounts of text?',
                'section': 'Slides & Presentation Materials',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_resources',
                'en': 'How relevant and useful were the examples, demonstrations, and supporting resources '
                      'presented?',
                'section': 'Slides & Presentation Materials',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_missing',
                'en': 'Were any important topics missing, insufficiently explained, inaccurate, or '
                      'inconsistent with the agreed outline? Please specify.',
                'section': 'Slides & Presentation Materials',
                'required': True,
                'type': 'paragraph'},
               {'id': 'volunteer_professionalism',
                'en': 'How professional, punctual, prepared, and cooperative was the speaker throughout the '
                      'session?',
                'section': 'Speaker Professionalism & Attitude',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_respect',
                'en': 'How respectfully did the speaker interact with attendees?',
                'section': 'Speaker Professionalism & Attitude',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_responsiveness',
                'en': 'How open and responsive was the speaker to questions, feedback, unexpected '
                      'situations?',
                'section': 'Speaker Professionalism & Attitude',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_concerns',
                'en': 'Did you observe any concerning behavior, inappropriate comments, unprofessional '
                      'conduct, or coordination challenges requiring follow-up?',
                'section': 'Speaker Professionalism & Attitude',
                'required': True,
                'options': ['No', 'Yes']},
               {'id': 'volunteer_concern_details',
                'en': 'If yes, please describe.',
                'section': 'Speaker Professionalism & Attitude',
                'required': True,
                'type': 'paragraph'},
               {'id': 'volunteer_engagement',
                'en': 'How effectively did the speaker maintain audience attention and engagement throughout '
                      'the session?',
                'section': 'Attendee Engagement & Learning Experience',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_participation',
                'en': 'How effectively did the speaker encourage meaningful participation, questions, or '
                      'interactive activities?',
                'section': 'Attendee Engagement & Learning Experience',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_understanding',
                'en': 'Based on attendee questions, participation, and reactions, how well did attendees '
                      'appear to understand the material?',
                'section': 'Attendee Engagement & Learning Experience',
                'required': True,
                'options': ['1', '2', '3', '4', '5', 'Insufficient evidence']},
               {'id': 'volunteer_goal',
                'en': 'How well did the session support our Bootcamp goal of preparing participants to '
                      'develop realistic, meaningful NASA Space Apps solutions?',
                'section': 'Vision & Strategic Alignment',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_challenges',
                'en': 'How effectively did the session connect its content to actual hackathon challenges, '
                      'NASA data/resources, the problem-solving process, or other relevant hackathon '
                      'requirements?',
                'section': 'Vision & Strategic Alignment',
                'required': True,
                'rating': True,
                'scale_labels': ['1', '', '', '', '5']},
               {'id': 'volunteer_invitation',
                'en': 'Is there anything competition team should take into consideration before inviting '
                      'this speaker again next year?',
                'section': 'Vision & Strategic Alignment',
                'required': True,
                'type': 'paragraph'}],
 'attendee': [{'id': 'attendee_experience',
               'en': 'How would you rate your overall experience in this session?',
               'section': 'Session & Expectations',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_expectations',
               'en': 'To what extent did the session meet your expectations?',
               'section': 'Session & Expectations',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_relevance',
               'en': 'How relevant was the session to your preparation for the NASA Space Apps Challenge?',
               'section': 'Session & Expectations',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_clarity',
               'en': 'How clearly did the speaker explain the topics and concepts?',
               'section': 'Speaker Performance',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_engagement',
               'en': 'How engaging and interactive was the speaker throughout the session?',
               'section': 'Speaker Performance',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_answers',
               'en': 'How effectively did the speaker respond to participants’ questions?',
               'section': 'Speaker Performance',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_pacing',
               'en': 'How would you evaluate the speaker’s pacing and time management?',
               'section': 'Speaker Performance',
               'required': True,
               'options': ['Too fast', 'Slightly fast', 'Appropriate', 'Slightly slow', 'Too slow']},
              {'id': 'attendee_speaker_notes',
               'en': 'What did you appreciate most about the speaker, and what could they improve?',
               'section': 'Speaker Performance',
               'required': True,
               'type': 'paragraph'},
              {'id': 'attendee_content',
               'en': 'How well-organized was the session content?',
               'section': 'Content & Learning Outcomes',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_materials',
               'en': 'How helpful were the slides, examples, demonstrations, or visual materials in '
                     'understanding the content?',
               'section': 'Content & Learning Outcomes',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_practice',
               'en': 'How useful were the practical examples or activities in connecting the content to the '
                     'hackathon?',
               'section': 'Content & Learning Outcomes',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_confidence',
               'en': 'How confident do you feel about applying what you learned during the hackathon?',
               'section': 'Content & Learning Outcomes',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_takeaway',
               'en': 'What was your most valuable takeaway, and what topic do you still need more help '
                     'understanding?',
               'section': 'Content & Learning Outcomes',
               'required': True,
               'type': 'paragraph'},
              {'id': 'attendee_communication',
               'en': 'How clear was the communication about the session schedule, location, and '
                     'instructions?',
               'section': 'Logistics & Organization',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_venue',
               'en': 'How satisfied were you with the venue, seating, visibility, sound, and overall '
                     'physical environment?',
               'section': 'Logistics & Organization',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_timing',
               'en': 'How would you evaluate the session duration, start time, and overall time management?',
               'section': 'Logistics & Organization',
               'required': True,
               'rating': True,
               'scale_labels': ['1', '', '', '', '5']},
              {'id': 'attendee_volunteers',
               'en': 'How helpful and approachable were the organizing volunteers when you needed '
                     'assistance?',
               'section': 'Logistics & Organization',
               'required': True,
               'options': ['1', '2', '3', '4', '5', 'N/A']},
              {'id': 'attendee_change',
               'en': 'If you could change one thing about this session to make it more valuable for future '
                     'participants, what would it be?',
               'section': 'Final Feedback',
               'required': True,
               'type': 'paragraph'}]}

AUDIENCES['attendee'] = {'label': 'Workshop attendees', 'intro': 'Your feedback helps us improve the NASA Space Apps Cairo Bootcamp. Please evaluate the speaker, content, learning experience, and session organization.', 'question': BOOTCAMP_QUESTIONS['attendee'][0]}
for role, items in BOOTCAMP_QUESTIONS.items():
    AUDIENCES[role]['questions'] = items
SPEAKER_QUESTIONS = BOOTCAMP_QUESTIONS['speaker']
VOLUNTEER_QUESTIONS = BOOTCAMP_QUESTIONS['volunteer']
