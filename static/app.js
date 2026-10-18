'use strict';
const $ = id => document.getElementById(id);
let token = new URLSearchParams(location.search).get('t') || '';
try {
  if (token) sessionStorage.setItem('feedback-event-token', token);
  else token = sessionStorage.getItem('feedback-event-token') || '';
} catch (_) { /* The event link still works when browser storage is unavailable. */ }
const homeLink = document.querySelector('.brand');
if (token && homeLink) homeLink.href = '/?t=' + encodeURIComponent(token);
let questions = [], index = 0, recorder = null, stream = null, chunks = [];
let recording = null, playbackURL = null, timer = null, started = 0, submissionID = null;
let transcribing = false;
let speakerForm = false;
let surveyRole = 'speaker';
const speakerRatings = {};
let speakerStep = -1;
const speakerFields = [];
function ratingsComplete() { return speakerForm ? Boolean($('workshop').value) && questions.every(q => q.required === false || speakerRatings[q.id]) : Boolean(rating); }
let busy = false, requesting = false, ready = false, maxSeconds = 90, recordFailed = false, rating = 0, micReady = false, maxAudioBytes = 4_000_000;
const ratingInputs = [...document.querySelectorAll('input[name="rating"]')];
const formatTime = seconds => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
function status(message = '', error = false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
}
function sync() {
  const active = recorder?.state === 'recording';
  $('record').disabled = !ready || !micReady || busy || transcribing || Boolean(submissionID) || requesting || Boolean(recording);
  $('record').setAttribute('aria-label', active ? 'Stop recording' : 'Start recording');
  $('recorder').classList.toggle('recording', active);
  $('mic-icon').hidden = active;
  $('stop-icon').hidden = !active;
  $('participant-name').disabled = busy || Boolean(submissionID);
  ratingInputs.forEach(input => input.disabled = busy || Boolean(submissionID));
  if (speakerForm) {
    $('workshop').disabled = busy || Boolean(submissionID);
    $('step-back').disabled = busy || transcribing || requesting || active || Boolean(submissionID);
    $('step-continue').disabled = busy || Boolean(submissionID) || (speakerStep === -1
      ? !$('participant-name').value.trim() || !$('workshop').value
      : questions[speakerStep]?.required !== false && !speakerRatings[questions[speakerStep]?.id]);
    document.querySelectorAll('#speaker-questions input').forEach(input => input.disabled = busy || Boolean(submissionID));
  }
  $('redo').disabled = busy || transcribing || Boolean(submissionID);
  $('feedback-text').disabled = busy || transcribing || Boolean(submissionID);
  $('transcribe').disabled = !recording || busy || transcribing || Boolean(submissionID);
  $('transcribe').textContent = transcribing ? 'Transcribing…' : 'Create transcript';
  $('send').disabled = !ready || (speakerForm && speakerStep !== questions.length) || !ratingsComplete() || !$('participant-name').value.trim() || busy || transcribing || active || requesting || (Boolean(recording) && !$('feedback-text').value.trim());
  $('send').firstElementChild.textContent = busy ? 'Sending your feedback…' : 'Send my feedback';
}
function releaseMic() {
  clearInterval(timer);
  stream?.getTracks().forEach(track => track.stop());
  stream = null;
}
function clearRecording() {
  $('playback').pause();
  $('playback').removeAttribute('src');
  $('playback').load();
  if (playbackURL) URL.revokeObjectURL(playbackURL);
  recording = null; playbackURL = null; submissionID = null; chunks = []; recorder = null;
  $('preview').hidden = true;
  $('record-state').textContent = 'READY WHEN YOU ARE';
  $('record-label').textContent = 'Tap to start recording';
  $('timer').textContent = `00:00 / ${formatTime(maxSeconds)}`;
  sync();
}
function renderQuestion() {
  $('question').textContent = questions[index].en;
  const labels = questions[index].scale_labels || ['Poor', 'Fair', 'Good', 'Great', 'Excellent'];
  ratingInputs.forEach((input, i) => {
    const label = input.parentElement?.querySelector('small');
    if (label) label.textContent = labels[i] || '';
    input.setAttribute('aria-label', `${i + 1}${labels[i] ? ' — ' + labels[i] : ''}`);
  });
  $('progress').textContent = questions.length > 1 ? `QUESTION ${index + 1} OF ${questions.length}` : 'YOUR FEEDBACK';
}
function micError(error) {
  const messages = {
    NotAllowedError: 'Microphone access was blocked. Allow it in the browser’s site permissions and your device privacy settings, then try again.',
    NotFoundError: 'No microphone was found. Connect a microphone or check your device settings.',
    NotReadableError: 'Your microphone is unavailable. Close other apps using it and try again.',
    AbortError: 'Recording was interrupted. Please try again.',
    SecurityError: 'Your browser has disabled microphone access. Open this page directly in Chrome, Edge, or Safari.'
  };
  return messages[error.name] || 'Could not start recording. Check microphone permissions or try another browser.';
}
async function toggleRecording() {
  if (recorder?.state === 'recording') {
    recorder.stop();
    return;
  }
  if (!ready || !micReady || busy || transcribing || submissionID || requesting || recording) return;
  if (!$('participant-name').value.trim()) {
    status('Please enter your name before recording.', true);
    $('participant-name').focus(); return;
  }
  requesting = true; sync(); status('Allow microphone access when your browser asks.');
  try {
    stream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true}});
    if (document.hidden) { releaseMic(); throw new DOMException('Page hidden', 'AbortError'); }
    const mimeType = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm', 'audio/ogg;codecs=opus'].find(type => MediaRecorder.isTypeSupported(type));
    recorder = new MediaRecorder(stream, mimeType ? {mimeType} : undefined);
    chunks = []; recordFailed = false;
    recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    recorder.onerror = () => {
      recordFailed = true; releaseMic(); status('Recording was interrupted. Please record again.', true);
      if (recorder.state !== 'inactive') recorder.stop();
      sync();
    };
    recorder.onstop = () => {
      const elapsed = Math.min(maxSeconds, Math.floor((Date.now() - started) / 1000));
      releaseMic();
      const type = recorder.mimeType || chunks[0]?.type || 'audio/webm';
      recording = new Blob(chunks, {type});
      if (recordFailed || !recording.size || elapsed < 1) {
        clearRecording(); status('Please record at least one second of feedback and try again.', true); return;
      }
      if (recording.size > maxAudioBytes) {
        clearRecording(); status('That recording is too large. Please record a shorter answer.', true); return;
      }
      playbackURL = URL.createObjectURL(recording);
      $('playback').src = playbackURL;
      $('preview').hidden = false;
      $('record-state').textContent = 'RECORDING READY';
      $('record-label').textContent = 'Your recording is ready';
      $('timer').textContent = `${formatTime(elapsed)} / ${formatTime(maxSeconds)}`;
      status('Review and edit your transcript before sending.'); sync();
      if (!$('feedback-text').value.trim()) transcribeRecording();
    };
    recorder.start(250);
    started = Date.now();
    $('record-state').textContent = 'RECORDING';
    $('record-label').textContent = 'Tap to stop recording';
    status('Recording. Speak in English, Arabic, or a mix of both.');
    timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - started) / 1000);
      $('timer').textContent = `${formatTime(Math.min(elapsed, maxSeconds))} / ${formatTime(maxSeconds)}`;
      if (elapsed >= maxSeconds && recorder.state === 'recording') recorder.stop();
    }, 250);
  } catch (error) {
    releaseMic(); status(micError(error), true);
  } finally { requesting = false; sync(); }
}
async function transcribeRecording() {
  if (!recording || busy || transcribing || submissionID) return;
  if ($('feedback-text').value.trim() && !window.confirm('Replace your current text with a new transcript?')) return;
  transcribing = true; sync(); status('Transcribing your recording. Nothing has been saved to feedback yet.');
  const form = new FormData(); form.append('token', token);
  const extension = recording.type.includes('mp4') ? 'mp4' : recording.type.includes('ogg') ? 'ogg' : 'webm';
  form.append('audio', recording, `recording.${extension}`);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 100000);
  try {
    const response = await fetch('/api/transcribe', {method:'POST', body:form, signal:controller.signal});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Transcription failed.');
    $('feedback-text').value = result.transcript || '';
    status(result.transcript ? 'Review and edit the text below. Send saves only your final text and rating.' : 'No speech was detected. Retry, type your feedback, or discard the recording.');
  } catch (error) {
    status('Transcription could not finish. Your recording is still here. Retry, type your feedback, or discard it to send only your rating.', true);
  } finally { clearTimeout(timeout); transcribing = false; sync(); $('feedback-text').focus(); }
}
async function sendRecording() {
  if (!ready || (speakerForm && speakerStep !== questions.length) || !ratingsComplete() || busy || transcribing || requesting || recorder?.state === 'recording' || !$('participant-name').value.trim() || (recording && !$('feedback-text').value.trim())) return;
  submissionID ||= crypto.randomUUID();
  busy = true; $('playback').pause(); sync(); status('Saving your feedback…');
  const form = new FormData();
  for (const [key, value] of Object.entries({token, question_id: speakerForm ? surveyRole + '_form' : questions[index].id, submission_id: submissionID, participant_name: $('participant-name').value.trim(), rating, feedback_text: $('feedback-text').value.trim(), consent: 'true'})) form.append(key, value);
  if (speakerForm) {
    form.set('rating', String(speakerRatings[surveyRole === 'speaker' ? 'speaker_experience' : 'volunteer_delivery']));
    form.append('workshop', $('workshop').value);
    form.append('ratings', JSON.stringify(Object.fromEntries(questions.map(q => [q.id, speakerRatings[q.id] ?? null]))));
  }
  try {
    const response = await fetch('/api/answer', {method: 'POST', body: form});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not send your recording. Please try again.');
    if (!result.saved) throw new Error('The server did not confirm your submission. Please try again.');
    $('form-panel').hidden = true; $('success').hidden = false;
    $('receipt').textContent = `Reference: ${result.id}`;
    $('next').hidden = speakerForm || index + 1 >= questions.length;
    $('success-heading').textContent = !speakerForm && index + 1 < questions.length ? 'Rating received.' : 'Thank you for your feedback.';
    $('success-message').textContent = !speakerForm && index + 1 < questions.length
      ? `Your answer is saved. Continue to question ${index + 2} of ${questions.length}.`
      : 'Your feedback is safely with the organizing team.';
    status(); $('feedback-text').value = '';
    clearRecording(); $('success').focus();
  } catch (error) {
    status(`${error.message || 'Connection lost.'} Your feedback is still here. Please retry sending.`, true);
  } finally { busy = false; sync(); }
}
$('record').addEventListener('click', toggleRecording);
$('redo').addEventListener('click', () => { clearRecording(); status(); $('record').focus(); });
$('transcribe').addEventListener('click', transcribeRecording);
$('feedback-text').addEventListener('input', sync);
$('send').addEventListener('click', sendRecording);
$('participant-name').addEventListener('input', sync);
ratingInputs.forEach(input => input.addEventListener('change', () => { rating = Number(input.value); sync(); }));
$('next').addEventListener('click', () => {
  index++; $('feedback-text').value = ''; rating = 0; ratingInputs.forEach(input => input.checked = false); clearRecording(); renderQuestion(); $('success').hidden = true; $('form-panel').hidden = false; status(); $('question').focus();
});
document.addEventListener('visibilitychange', () => {
  if (document.hidden && recorder?.state === 'recording') recorder.stop();
});
window.addEventListener('beforeunload', event => {
  if ((speakerForm && Object.keys(speakerRatings).length && !$('form-panel').hidden) || recording || busy || transcribing || $('feedback-text').value.trim() || recorder?.state === 'recording') { event.preventDefault(); event.returnValue = ''; }
});
window.addEventListener('pagehide', releaseMic);
(async () => {
  try {
    const response = await fetch('/api/config?t=' + encodeURIComponent(token));
    if (!response.ok) throw new Error('Could not load the question. Refresh the page to try again.');
    const result = await response.json();
    if (!result.questions?.length) throw new Error('No feedback questions are available yet. Please contact the organizer.');
    $('provider-name').textContent = result.transcription_provider || 'the selected transcription provider';
    $('gemini-notice').hidden = !result.gemini_test_notice;
    $('audience-heading').textContent = (result.audience_label || 'Participants').toUpperCase() + ' · FEEDBACK';
    $('intro').textContent = result.intro || $('intro').textContent;
    questions = result.questions; maxSeconds = result.max_seconds || 90;
    maxAudioBytes = result.max_audio_bytes || 4_000_000;
    surveyRole = result.audience;
    speakerForm = ['speaker', 'volunteer'].includes(surveyRole);
    if (speakerForm) {
      renderSpeakerForm(result.workshops || []);
      if (surveyRole === 'volunteer') {
        $('feedback-text').placeholder = 'Share other observations, excessive self-promotion, or suggestions for improvement…';
      }
    }
    else renderQuestion();
    if (!token) throw new Error('This link is missing the event code. Please use the full feedback link or QR code from the organizer.');
    micReady = Boolean(window.isSecureContext && navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
    ready = true; sync();
    if (!micReady) status('Recording is unavailable in this browser. You can still send your rating. To record, use the HTTPS site or localhost in a supported browser.');
  } catch (error) { status(error.message, true); }
})();

function renderSpeakerForm(workshops) {
  $('speaker-fields').hidden = false;
  $('single-rating').hidden = true;
  $('question').hidden = true;
  $('speaker-navigation').hidden = false;
  for (const name of workshops) {
    const option = document.createElement('option'); option.value = name; option.textContent = name; $('workshop').append(option);
  }
  $('workshop').addEventListener('change', sync);
  for (const [i, question] of questions.entries()) {
    const field = document.createElement('fieldset'); field.className = 'rating-field survey-question';
    const legend = document.createElement('legend');
    if (question.section) {
      const section = document.createElement('span'); section.className = 'question-section'; section.textContent = question.section; legend.append(section);
    }
    const title = document.createElement('span'); title.className = 'question-title'; title.textContent = question.en; legend.append(title);
    field.append(legend);
    const choices = document.createElement('div'); choices.className = question.options ? 'survey-choices' : 'rating-options';
    for (const score of question.options || [1, 2, 3, 4, 5]) {
      const label = document.createElement('label');
      const input = document.createElement('input'); input.type = 'radio'; input.name = question.id; input.value = score; input.required = question.required !== false;
      input.setAttribute('aria-label', `${score}${question.scale_labels?.[score - 1] ? ' — ' + question.scale_labels[score - 1] : ''}`);
      input.addEventListener('change', () => {
        speakerRatings[question.id] = score;
        speakerStep = i + 1; renderSpeakerStep(true);
      });
      const span = document.createElement('span'); const number = document.createElement('b'); number.textContent = score;
      const caption = document.createElement('small'); caption.textContent = question.scale_labels?.[score - 1] || '';
      span.append(number, caption); label.append(input, span); choices.append(label);
    }
    field.append(choices); $('speaker-questions').append(field); speakerFields.push(field);
    legend.tabIndex = -1;
  }
  $('step-skip').addEventListener('click', () => {
    const question = questions[speakerStep];
    if (question?.required !== false || busy || submissionID) return;
    speakerRatings[question.id] = null;
    for (const label of speakerFields[speakerStep].children[1].children) label.children[0].checked = false;
    speakerStep++; renderSpeakerStep(true);
  });
  $('step-back').addEventListener('click', () => {
    if (speakerStep >= 0) { speakerStep--; renderSpeakerStep(true); }
  });
  $('step-continue').addEventListener('click', () => {
    if ($('step-continue').disabled) return;
    if (speakerStep < questions.length) { speakerStep++; renderSpeakerStep(true); }
  });
  renderSpeakerStep();
}

function renderSpeakerStep(focus = false) {
  const finalStep = speakerStep === questions.length;
  speakerFields.forEach((field, i) => { field.hidden = i !== speakerStep; });
  $('final-feedback').hidden = !finalStep;
  $('step-back').hidden = speakerStep < 0;
  $('step-skip').hidden = questions[speakerStep]?.required !== false;
  $('step-skip').disabled = busy || Boolean(submissionID);
  $('step-continue').hidden = finalStep;
  $('step-continue').textContent = speakerStep < 0 ? 'Start ratings →' : 'Continue →';
  $('progress').textContent = speakerStep < 0 ? (surveyRole === 'volunteer' ? 'YOUR SESSION EVALUATION' : 'YOUR SPEAKER FEEDBACK')
    : finalStep ? 'RATINGS COMPLETE · OPTIONAL FEEDBACK' : `QUESTION ${speakerStep + 1} OF ${questions.length}`;
  status(); sync();
  if (focus) {
    if (finalStep) $('feedback-text').focus();
    else if (speakerStep >= 0) speakerFields[speakerStep].children[0].focus();
    else $('participant-name').focus();
  }
}
