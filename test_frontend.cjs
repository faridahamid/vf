'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {randomUUID} = require('node:crypto');
const source = fs.readFileSync(__dirname + '/static/app.js', 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
async function createPage(options = {}) {
  const nodes = new Map();
  const element = id => {
    if (!nodes.has(id)) nodes.set(id, {textContent:'', hidden:false, disabled:false, checked:false, value:'', children:[], append(...items){this.children.push(...items);}, handlers:{}, firstElementChild:{}, classList:{toggle(){}}, setAttribute(){}, removeAttribute(){}, load(){}, pause(){}, focus(){}, addEventListener(name, callback){this.handlers[name]=callback;}});
    return nodes.get(id);
  };
  element('record').disabled = true; element('send').disabled = true;
  element('participant-name').value = 'Test Participant';
  const ratings = [1,2,3,4,5].map(n => element('rating-' + n)); ratings.forEach((input,i)=>input.value=String(i+1));
  let now = 0, stopped = 0, requests = [];
  const track = {stop(){stopped++;}};
  class Recorder {
    static isTypeSupported(type) { return type === (options.mime || 'audio/webm;codecs=opus'); }
    constructor(stream, opts) { this.state='inactive'; this.mimeType=opts?.mimeType || 'audio/webm'; }
    start() {this.state='recording';}
    stop() {this.state='inactive';this.ondataavailable({data:new Blob(['test audio'], {type:this.mimeType})}); queueMicrotask(() => this.onstop());}
  }
  const ctx = {
    document:{hidden:false,createElement:tag=>element("created-"+nodes.size),getElementById:element,querySelector:()=>element("brand"),querySelectorAll:()=>ratings,addEventListener(){}},
    window:{confirm:()=>false,isSecureContext: options.secure !== false, MediaRecorder:Recorder, addEventListener(){}},
    navigator:{mediaDevices:{getUserMedia: async () => {if(options.denied)throw {name:'NotAllowedError'};return {getTracks:()=>[track]};}}},
    MediaRecorder:Recorder, URLSearchParams, URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},
    AbortController, setTimeout, clearTimeout, Blob, FormData, crypto:{randomUUID}, Date:{now:()=>now}, DOMException,
    location:{search:options.noToken ? '' : '?t=test-token'},
    sessionStorage:{getItem:()=>options.storedToken || '',setItem(){}},
    setInterval(){return 1;}, clearInterval(){}, queueMicrotask,
    fetch:async (url, init) => {
      if (url.startsWith('/api/config')) return {ok:true,json:async()=>({audience:options.audience,workshops:options.workshops,questions:options.questions || [{id:'q1',en:'What was valuable?'}], max_seconds:90,is_test:true})};
      if (url === '/api/transcribe') return options.transcribe ? options.transcribe() : {ok:true,json:async()=>({transcript:'Generated transcript'})};
      requests.push(init.body);
      if(options.send) return options.send(requests.length);
      return {ok:true,json:async()=>({saved:true,id:'test-id',transcript_available:true})};
    }
  };
  vm.runInNewContext(source, ctx); await tick();
  if (!options.noRating) ratings[3].handlers.change();
  return {element, requests, stopped:()=>stopped, async record(){await element('record').handlers.click();now+=2200;await element('record').handlers.click();await tick();}, click:async id=>{await element(id).handlers.click();await tick();}};
}
test('missing token and insecure context keep recording disabled', async()=>{
  for(const options of [{noToken:true},{secure:false}]){
    const page=await createPage(options);assert.equal(page.element('record').disabled,true);if(options.noToken) assert.ok(page.element('status').textContent);
  }
});
test('permission denied recovers recording control and gives instructions',async()=>{
  const page=await createPage({denied:true});await page.click('record');
  assert.equal(page.element('record').disabled,false);assert.match(page.element('status').textContent,/blocked/);assert.equal(page.requests.length,0);
});
test('recording remains local until Send; releases microphone',async()=>{
  const page=await createPage();await page.record();
  assert.equal(page.requests.length,0);assert.equal(page.stopped(),1);
  assert.equal(page.element('preview').hidden,false);assert.equal(page.element('send').disabled,false);

  await page.click('send');assert.equal(page.requests.length,1);
  assert.equal(page.requests[0].get('participant_name'),'Test Participant');
  assert.equal(page.requests[0].has('lang'),false);
  assert.equal(page.element('success').hidden,false);assert.equal(page.element('form-panel').hidden,true);
});
test('failed send retains audio and stable submission ID for retry',async()=>{
  const page=await createPage({mime:'audio/mp4',send:async n=>({ok:n>1,json:async()=>n>1?{saved:true,id:'ok',transcript_available:false}:{detail:'Temporary error'}})});
  await page.record();
  await page.click('send');assert.equal(page.element('preview').hidden,false);assert.equal(page.element('send').disabled,false);
  await page.click('send');assert.equal(page.requests[0].get('submission_id'),page.requests[1].get('submission_id'));
  assert.equal(page.requests[0].has('audio'),false);assert.equal(page.requests[0].get('feedback_text'),'Generated transcript');
});
test('discard creates a fresh recording with no upload',async()=>{
  const page=await createPage();await page.record();await page.click('redo');
  assert.equal(page.element('preview').hidden,true);assert.equal(page.element('record').disabled,false);assert.equal(page.requests.length,0);
});

test('name is required before recording or sending', async()=>{
  const page=await createPage();page.element('participant-name').value='   ';
  await page.click('record');assert.match(page.element('status').textContent,/enter your name/);
  assert.equal(page.element('preview').src,undefined);assert.equal(page.requests.length,0);
  page.element('participant-name').value='Test Name';await page.record();
  page.element('participant-name').value='';page.element('participant-name').handlers.input();
  assert.equal(page.element('send').disabled,true);await page.click('send');assert.equal(page.requests.length,0);
});

test('rating alone submits without microphone or audio',async()=>{
  const page=await createPage({secure:false});
  assert.equal(page.element('send').disabled,false);await page.click('send');
  assert.equal(page.requests[0].get('rating'),'4');assert.equal(page.requests[0].has('audio'),false);assert.equal(page.stopped(),0);
});
test('missing rating cannot submit',async()=>{
  const page=await createPage({noRating:true});
  await page.click('send');assert.equal(page.requests.length,0);assert.equal(page.element('send').disabled,true);
});
test('discarding optional voice allows rating-only submission',async()=>{
  const page=await createPage();await page.record();await page.click('redo');
  await page.click('send');
  assert.equal(page.requests[0].has('audio'),false);
});

test('event code survives home navigation without a URL token',async()=>{
  const page=await createPage({noToken:true,storedToken:'remembered-event'});
  assert.equal(page.element('record').disabled,false);
  assert.equal(page.element('brand').href,'/?t=remembered-event');
  await page.click('send');assert.equal(page.requests[0].get('token'),'remembered-event');
});

test('edited transcript is submitted without audio and cleared on success',async()=>{
 const page=await createPage();await page.record();
 assert.equal(page.element('feedback-text').value,'Generated transcript');
 page.element('feedback-text').value='Corrected Arabic and English';await page.click('send');
 assert.equal(page.requests[0].get('feedback_text'),'Corrected Arabic and English');
 assert.equal(page.requests[0].has('audio'),false);
 assert.equal(page.element('feedback-text').value,'');
});
test('failed transcription allows typing and preserves local playback',async()=>{
 const page=await createPage({transcribe:async()=>({ok:false,json:async()=>({detail:'Failure'})})});await page.record();
 assert.equal(page.element('preview').hidden,false);assert.equal(page.element('send').disabled,true);
 page.element('feedback-text').value='Typed answer';page.element('feedback-text').handlers.input();
 await page.click('send');assert.equal(page.requests[0].get('feedback_text'),'Typed answer');
});

test('transcription in flight blocks editing and sending',async()=>{
 let finish;const response=new Promise(resolve=>finish=resolve);
 const page=await createPage({transcribe:()=>response});await page.record();
 assert.equal(page.element('feedback-text').disabled,true);assert.equal(page.element('send').disabled,true);
 await page.click('send');assert.equal(page.requests.length,0);
 finish({ok:true,json:async()=>({transcript:'Ready to review'})});await tick();
 assert.equal(page.element('feedback-text').disabled,false);
 assert.equal(page.element('feedback-text').value,'Ready to review');
});
test('recording preserves existing typed text and replacement can be declined',async()=>{
 const page=await createPage();page.element('feedback-text').value='My original answer';await page.record();
 assert.equal(page.element('feedback-text').value,'My original answer');
 await page.click('transcribe');assert.equal(page.element('feedback-text').value,'My original answer');
});


test('multiple ratings save distinct questions, reset the rating, and finish on the last answer',async()=>{
 const page=await createPage({questions:[{id:'speaker_experience',en:'Overall?'},{id:'speaker_support',en:'Support?'}]});
 await page.click('send');
 assert.equal(page.requests[0].get('question_id'),'speaker_experience');
 assert.equal(page.element('next').hidden,false);
 assert.match(page.element('success-message').textContent,/question 2 of 2/);
 await page.click('next');
 assert.equal(page.element('question').textContent,'Support?');
 assert.equal(page.element('send').disabled,true);
 page.element('rating-5').handlers.change();
 await page.click('send');
 assert.equal(page.requests[1].get('question_id'),'speaker_support');
 assert.notEqual(page.requests[0].get('submission_id'),page.requests[1].get('submission_id'));
 assert.equal(page.element('next').hidden,true);
});


test('speaker submits the workshop and all five ratings in one request',async()=>{
 const questions=['experience','support','communication','session_reception','future_engagement'].map(id=>({id:'speaker_'+id,en:id,scale_labels:['Low','','','','High']}));
 const page=await createPage({audience:'speaker',workshops:['Video Editing'],questions});
 assert.equal(page.element('single-rating').hidden,true);
 assert.equal(page.element('speaker-fields').hidden,false);
 assert.equal(page.element('speaker-questions').children.length,5);
 await page.click('send');assert.equal(page.requests.length,0);
 page.element('workshop').value='Video Editing';page.element('workshop').handlers.change();
 assert.equal(page.element('final-feedback').hidden,true);
 await page.click('step-continue');
 assert.equal(page.element('speaker-questions').children[0].hidden,false);
 assert.equal(page.element('speaker-questions').children[1].hidden,true);
 for(const field of page.element('speaker-questions').children){
   field.children[1].children[3].children[0].handlers.change();
 }
 assert.equal(page.requests.length,0);
 assert.equal(page.element('final-feedback').hidden,false);
 page.element('feedback-text').value='Keep my draft';
 await page.click('step-back');
 assert.equal(page.element('final-feedback').hidden,true);
 assert.equal(page.element('speaker-questions').children[4].hidden,false);
 await page.click('step-continue');
 assert.equal(page.element('feedback-text').value,'Keep my draft');
 assert.equal(page.element('send').disabled,false);
 await page.click('send');
 assert.equal(page.requests.length,1);
 assert.equal(page.requests[0].get('workshop'),'Video Editing');
 assert.equal(page.requests[0].get('question_id'),'speaker_form');
 assert.equal(Object.keys(JSON.parse(page.requests[0].get('ratings'))).length,5);
 assert.equal(page.element('next').hidden,true);
});


test('volunteer wizard supports choices, optional skipping, back navigation and one submission',async()=>{
 const questions=[
  {id:'volunteer_agenda',en:'Agenda?',required:false,scale_labels:['Strongly Disagree','','','','Strongly Agree']},
  {id:'volunteer_recommendation',en:'Return?',options:['Yes','No','Maybe']},
  {id:'volunteer_delivery',en:'Delivery?',scale_labels:['Strongly Disagree','','','','Strongly Agree']}
 ];
 const page=await createPage({audience:'volunteer',workshops:['NASA Data'],questions});
 page.element('workshop').value='NASA Data';page.element('workshop').handlers.change();
 await page.click('step-continue');assert.equal(page.element('step-skip').hidden,false);
 await page.click('step-skip');
 const fields=page.element('speaker-questions').children;
 assert.equal(fields[1].hidden,false);
 assert.equal(fields[1].children[1].children.length,3);
 fields[1].children[1].children[2].children[0].handlers.change();
 fields[2].children[1].children[4].children[0].handlers.change();
 assert.equal(page.requests.length,0);assert.equal(page.element('final-feedback').hidden,false);
 await page.click('step-back');await page.click('step-continue');
 await page.click('send');assert.equal(page.requests.length,1);
 const scores=JSON.parse(page.requests[0].get('ratings'));
 assert.equal(scores.volunteer_agenda,null);assert.equal(scores.volunteer_recommendation,'Maybe');
 assert.equal(scores.volunteer_delivery,5);assert.equal(page.requests[0].get('question_id'),'volunteer_form');
 assert.equal(page.requests[0].get('rating'),'5');
});
