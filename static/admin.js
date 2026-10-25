'use strict';
const $ = id => document.getElementById(id);
let reportState = null, reportBusy = false;
let data = [], offset = 0, hasMore = false, busy = false, password = '';
function adminHeaders(value) { return {'X-Admin-Password': encodeURIComponent(value), 'X-Admin-Password-Encoding': 'percent-utf8'}; }
function message(text) { $('status').textContent = text; }
function buttons() {
  $('report-status').disabled = !password || busy || reportBusy;
  $('report-generate').disabled = !password || busy || reportBusy || !reportState?.can_generate || Boolean(reportState?.saved && !reportState.changed);
  $('report-download').disabled = !password || busy || reportBusy || !reportState?.saved;
  $('audience-filter').disabled = busy;
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
    cell(row, item.ptype || 'participant');
    cell(row, item.question_id === 'attendee_form' ? 'Workshop attendee feedback' : item.question_id === 'speaker_form' ? 'Speaker feedback form' : item.question_id === 'volunteer_form' ? 'Volunteer session evaluation' : item.question_id);
    cell(row, item.workshop || '—');
    const labels = {speaker_experience:'Overall experience', speaker_support:'Organizer support', speaker_communication:'Communication', speaker_session_reception:'Session reception', speaker_future_engagement:'Likelihood to return'};
    cell(row, Object.entries(item.scores || {}).map(([id, value]) => `${item.score_labels?.[id] || labels[id] || id}: ${value == null ? 'Skipped' : typeof value === 'number' ? value + '/5' : value}`).join(' · ') || '—');
    cell(row, item.average_rating != null ? `${Number(item.average_rating).toFixed(1)} / 5 (average)` : item.rating == null ? '—' : `${item.rating} / 5 (single)`);
    const transcript = cell(row, item.transcript || (item.audio_path ? 'Transcript not available — listen to the recording.' : 'Rating only'), 'transcript'); transcript.dir = 'auto';
    const recording = cell(row, '');
    if (item.audio_url) {
      const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'none'; audio.src = item.audio_url; recording.append(audio);
    } else { recording.textContent = item.audio_path ? 'Playback unavailable. Reload or check Supabase Storage.' : 'No audio stored'; }
    const actions = cell(row, '');
    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'delete-button'; remove.textContent = 'Delete';
    remove.addEventListener('click', () => deleteFeedback(item)); actions.append(remove);
    $('responses').append(row);
  }
  if (!visible.length) { const row = document.createElement('tr'); const td = cell(row, 'No feedback yet.'); td.colSpan = 10; $('responses').append(row); }
  $('more').hidden = !hasMore;
}
async function load(reset = true) {
  if (busy) return; busy = true; buttons(); message('Loading feedback…');
  const candidate = reset ? $('password').value : password;
  try {
    const response = await fetch(`/api/admin/responses?offset=${reset ? 0 : offset}&audience=${encodeURIComponent($('audience-filter').value)}`, {headers: adminHeaders(candidate)});
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Could not load feedback.');
    password = candidate;
    await refreshReport();
    try {
      const linksResponse = await fetch('/api/admin/links', {headers: adminHeaders(password)});
      if (linksResponse.ok) {
        const links = await linksResponse.json(); $('links-list').replaceChildren();
        for (const item of links) {
          const label = document.createElement('label'); label.textContent = item.label;
          const input = document.createElement('input'); input.type = 'text'; input.readOnly = true;
          input.value = new URL(item.path, location.origin).href;
          input.addEventListener('click', () => input.select()); label.append(input); $('links-list').append(label);
        }
        $('audience-links').hidden = false;
      }
    } catch { /* Feedback remains accessible if link loading fails. */ }

    if (reset) data = [];
    data.push(...result); offset = data.length; hasMore = result.length === 100;
    draw(); message('Feedback loaded. CSV files open in Excel and preserve Arabic text.');
  } catch (error) { message(error.message || 'Connection failed. Please try again.'); }
  finally { busy = false; buttons(); }
}
$('login').addEventListener('submit', event => { event.preventDefault(); load(); });
$('audience-filter').addEventListener('change', () => { data = []; offset = 0; hasMore = false; draw(); if (password) load(); });
$('more').addEventListener('click', () => load(false));

$('export').addEventListener('click', async () => {
  if (busy) return; busy = true; buttons(); message('Preparing all matching feedback…');
  try {
    const response = await fetch('/api/admin/export?audience=' + encodeURIComponent($('audience-filter').value), {headers: adminHeaders(password)});
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
    const response = await fetch(`/api/admin/responses/${encodeURIComponent(item.id)}`, {method: 'DELETE', headers: adminHeaders(password)});
    const result = await response.json();
    if (!response.ok || !result.deleted) throw new Error(result.detail || 'Deletion failed. Please try again.');
    data = data.filter(row => row.id !== item.id); offset = data.length;
    draw(); await refreshReport(); message(item.audio_path ? 'Feedback and its audio file were deleted.' : 'Feedback was deleted.');
  } catch (error) { message(error.message || 'Deletion failed. Reload to check the result before retrying.'); }
  finally { busy = false; buttons(); }
}


async function refreshReport() {
  try {
    const response = await fetch('/api/admin/report', {headers: adminHeaders(password)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Report status unavailable.');
    reportState = result;
    const saved = result.saved;
    $('report-info').textContent = saved
      ? (result.changed ? 'New feedback is available. You can generate an updated report.' : 'Your report is ready to download.')
      : (result.can_generate ? 'Ready to generate your report.' : 'Collect feedback to generate a report.');
  } catch (error) { reportState = null; $('report-info').textContent = error.message; }
  buttons();
}
$('report-status').addEventListener('click', async () => {
  if (reportBusy || !password) return;
  reportBusy = true; buttons(); await refreshReport(); reportBusy = false; buttons();
});
$('report-generate').addEventListener('click', async () => {
  if (reportBusy || !reportState?.can_generate || !password) return;
  if (!window.confirm('Generate an analysis report for all audiences?')) return;
  reportBusy = true; buttons(); $('report-info').textContent = 'Generating and saving the report. Keep this page open. Do not start another analysis.';
  try {
    const body = new FormData(); body.append('snapshot', reportState.snapshot); body.append('confirm_ai', 'true');
    const response = await fetch('/api/admin/report', {method:'POST', headers:adminHeaders(password), body});
    const result = await response.json();
    if (!response.ok || !result.saved) throw new Error(result.detail || 'Report generation failed.');
    await refreshReport();
  } catch (error) { $('report-info').textContent = error.message + ' Check report status before taking any further action.'; }
  finally { reportBusy = false; buttons(); }
});
$('report-download').addEventListener('click', async () => {
  if (reportBusy || !password) return;
  reportBusy = true; buttons();
  try {
    const response = await fetch('/api/admin/report/download', {headers: adminHeaders(password)});
    if (!response.ok) { const result = await response.json(); throw new Error(result.detail || 'Download failed.'); }
    const url = URL.createObjectURL(await response.blob());
    const a = document.createElement('a'); a.href = url; a.download = 'nasa-cairo-audience-analysis.pdf'; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { $('report-info').textContent = error.message; }
  finally { reportBusy = false; buttons(); }
});
