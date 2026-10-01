'use strict';
const $ = id => document.getElementById(id);
let data = [], offset = 0, hasMore = false, busy = false, password = '';
function message(text) { $('status').textContent = text; }
function buttons() {
  $('load').disabled = busy; $('more').disabled = busy;
  $('export').disabled = busy || !password;
  document.querySelectorAll('.delete-button').forEach(button => button.disabled = busy);
}
function cell(row, value, className) {
  const td = document.createElement('td'); td.textContent = value ?? '';
  if (className) td.className = className; row.append(td); return td;
}
function draw() {
  const visible = data;
  $('count').textContent = `${visible.length} shown · ${data.length} loaded`;
  $('responses').replaceChildren();
  for (const item of visible) {
    const row = document.createElement('tr');
    const time = cell(row, new Date(item.created_at).toLocaleString());
    cell(row, item.participant_name || 'Not provided').dir = 'auto';
    cell(row, item.question_id);
    cell(row, item.rating == null ? '—' : `${item.rating} / 5`);
    const transcript = cell(row, item.transcript || (item.audio_path ? 'Transcript not available — listen to the recording.' : 'Rating only'), 'transcript'); transcript.dir = 'auto';
    const recording = cell(row, '');
    if (item.audio_url) {
      const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'none'; audio.src = item.audio_url; recording.append(audio);
    } else { recording.textContent = item.audio_path ? 'Playback unavailable. Reload or check Supabase Storage.' : 'No recording'; }
    const actions = cell(row, '');
    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'delete-button'; remove.textContent = 'Delete';
    remove.addEventListener('click', () => deleteFeedback(item)); actions.append(remove);
    $('responses').append(row);
  }
  if (!visible.length) { const row = document.createElement('tr'); const td = cell(row, 'No feedback yet.'); td.colSpan = 7; $('responses').append(row); }
  $('more').hidden = !hasMore;
}
async function load(reset = true) {
  if (busy) return; busy = true; buttons(); message('Loading feedback…');
  const candidate = reset ? $('password').value : password;
  try {
    const response = await fetch(`/api/admin/responses?offset=${reset ? 0 : offset}`, {headers: {'X-Admin-Password': candidate}});
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not load feedback.');
    password = candidate;
    try {
      const check = await fetch('/api/admin/status', {headers: {'X-Admin-Password': password}});
      if (check.ok) {
        const state = await check.json();
        $('provider-status').textContent = `Transcription: ${state.provider} / ${state.model}. ${state.key_configured ? 'Key configured.' : 'API key is missing.'} ${state.last_error || ''}`;
      }
    } catch { $('provider-status').textContent = 'Provider status unavailable.'; }
    if (reset) data = [];
    data.push(...result); offset = data.length; hasMore = result.length === 100;
    draw(); message('Feedback loaded. CSV files open in Excel and preserve Arabic text.');
  } catch (error) { message(error.message || 'Connection failed. Please try again.'); }
  finally { busy = false; buttons(); }
}
$('login').addEventListener('submit', event => { event.preventDefault(); load(); });
$('more').addEventListener('click', () => load(false));

$('export').addEventListener('click', async () => {
  if (busy) return; busy = true; buttons(); message('Preparing all matching feedback…');
  try {
    const response = await fetch('/api/admin/export?include_tests=true', {headers: {'X-Admin-Password': password}});
    if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Export failed.'); }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a'); link.href = url; link.download = 'space-apps-feedback.csv'; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000); message('CSV downloaded. Open it in Excel; use Save As to create an .xlsx workbook if needed.');
  } catch (error) { message(error.message || 'Export failed. Please try again.'); }
  finally { busy = false; buttons(); }
});

async function deleteFeedback(item) {
  if (busy || !password) return;
  const name = item.participant_name || 'this participant';
  if (!window.confirm(`Permanently delete feedback from ${name}? This removes the database entry and its audio file. This cannot be undone. Previously downloaded exports are not affected.`)) return;
  busy = true; buttons(); message('Deleting feedback and audio…');
  try {
    const response = await fetch(`/api/admin/responses/${encodeURIComponent(item.id)}`, {method: 'DELETE', headers: {'X-Admin-Password': password}});
    const result = await response.json();
    if (!response.ok || !result.deleted) throw new Error(result.detail || 'Deletion failed. Please try again.');
    data = data.filter(row => row.id !== item.id); offset = data.length;
    draw(); message('Feedback and its audio file were deleted.');
  } catch (error) { message(error.message || 'Deletion failed. Reload to check the result before retrying.'); }
  finally { busy = false; buttons(); }
}
