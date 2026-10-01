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
let busy = false, requesting = false, ready = false, maxSeconds = 90, recordFailed = false, rating = 0, micReady = false, maxAudioBytes = 4_000_000;
const ratingInputs = [...document.querySelectorAll('input[name="rating"]')];
const formatTime = seconds => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
function status(message = '', error = false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
}
function sync() {
  const active = recorder?.state === 'recording';
  $('record').disabled = !ready || !micReady || busy || requesting || Boolean(recording);
  $('record').setAttribute('aria-label', active ? 'Stop recording' : 'Start recording');
  $('recorder').classList.toggle('recording', active);
  $('mic-icon').hidden = active;
  $('stop-icon').hidden = !active;
  $('participant-name').disabled = busy || Boolean(submissionID);
  ratingInputs.forEach(input => input.disabled = busy || Boolean(submissionID));
  $('redo').disabled = busy || Boolean(submissionID);
  $('send').disabled = !ready || !rating || !$('participant-name').value.trim() || busy || active || requesting;
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
  recording = null; playbackURL = null; submissionID = null;
  $('preview').hidden = true;
  $('record-state').textContent = 'READY WHEN YOU ARE';
  $('record-label').textContent = 'Tap to start recording';
  $('timer').textContent = `00:00 / ${formatTime(maxSeconds)}`;
  sync();
}
function renderQuestion() {
  $('question').textContent = questions[index].en;
  $('progress').textContent = questions.length > 1 ? `QUESTION ${index + 1} OF ${questions.length}` : 'PARTICIPANT FEEDBACK';
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
  if (busy || requesting || recording) return;
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
      $('record-label').textContent = 'Your voice, ready to send';
      $('timer').textContent = `${formatTime(elapsed)} / ${formatTime(maxSeconds)}`;
      status('Listen to your recording, then send it when you’re happy.'); sync();
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
async function sendRecording() {
  if (!ready || !rating || busy || requesting || recorder?.state === 'recording' || !$('participant-name').value.trim()) return;
  const includeAudio = Boolean(recording);
  submissionID ||= crypto.randomUUID();
  busy = true; $('playback').pause(); sync(); status(includeAudio ? 'Uploading and transcribing your feedback. Keep this page open.' : 'Saving your feedback…');
  const form = new FormData();
  const extension = recording?.type.includes('mp4') ? 'mp4' : recording?.type.includes('ogg') ? 'ogg' : 'webm';
  for (const [key, value] of Object.entries({token, question_id: questions[index].id, submission_id: submissionID, participant_name: $('participant-name').value.trim(), rating, consent: 'true'})) form.append(key, value);
  if (includeAudio) form.append('audio', recording, `recording.${extension}`);
  try {
    const response = await fetch('/api/answer', {method: 'POST', body: form});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not send your recording. Please try again.');
    if (!result.saved) throw new Error('The server did not confirm your submission. Please try again.');
    $('form-panel').hidden = true; $('success').hidden = false;
    $('receipt').textContent = `Reference: ${result.id}`;
    $('next').hidden = index + 1 >= questions.length;
    status(includeAudio && !result.transcript_available ? 'Your feedback and audio are saved. A transcript is not available yet; the organizing team can listen to your recording.' : '');
    clearRecording(); $('success').focus();
  } catch (error) {
    status(`${error.message || 'Connection lost.'} Your feedback is still here. Please retry sending.`, true);
  } finally { busy = false; sync(); }
}
$('record').addEventListener('click', toggleRecording);
$('redo').addEventListener('click', () => { clearRecording(); status(); $('record').focus(); });
$('send').addEventListener('click', sendRecording);
$('participant-name').addEventListener('input', sync);
ratingInputs.forEach(input => input.addEventListener('change', () => { rating = Number(input.value); sync(); }));
$('next').addEventListener('click', () => {
  index++; rating = 0; ratingInputs.forEach(input => input.checked = false); clearRecording(); renderQuestion(); $('success').hidden = true; $('form-panel').hidden = false; status(); $('record').focus();
});
document.addEventListener('visibilitychange', () => {
  if (document.hidden && recorder?.state === 'recording') recorder.stop();
});
window.addEventListener('beforeunload', event => {
  if (recording || busy || recorder?.state === 'recording') { event.preventDefault(); event.returnValue = ''; }
});
window.addEventListener('pagehide', releaseMic);
(async () => {
  try {
    const response = await fetch('/api/config');
    if (!response.ok) throw new Error('Could not load the question. Refresh the page to try again.');
    const result = await response.json();
    if (!result.questions?.length) throw new Error('No feedback questions are available yet. Please contact the organizer.');
    $('provider-name').textContent = result.transcription_provider || 'the selected transcription provider';
    $('gemini-notice').hidden = !result.gemini_test_notice;
    questions = result.questions; maxSeconds = result.max_seconds || 90;
    maxAudioBytes = result.max_audio_bytes || 4_000_000; renderQuestion();
    if (!token) throw new Error('This link is missing the event code. Please use the full feedback link or QR code from the organizer.');
    micReady = Boolean(window.isSecureContext && navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
    ready = true; sync();
    if (!micReady) status('Recording is unavailable in this browser. You can still send your rating. To record, use the HTTPS site or localhost in a supported browser.');
  } catch (error) { status(error.message, true); }
})();
