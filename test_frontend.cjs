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
    if (!nodes.has(id)) nodes.set(id, {textContent:'', hidden:false, disabled:false, checked:false, value:'', handlers:{}, firstElementChild:{}, classList:{toggle(){}}, setAttribute(){}, removeAttribute(){}, load(){}, pause(){}, focus(){}, addEventListener(name, callback){this.handlers[name]=callback;}});
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
    document:{hidden:false,getElementById:element,querySelector:()=>element("brand"),querySelectorAll:()=>ratings,addEventListener(){}},
    window:{isSecureContext: options.secure !== false, MediaRecorder:Recorder, addEventListener(){}},
    navigator:{mediaDevices:{getUserMedia: async () => {if(options.denied)throw {name:'NotAllowedError'};return {getTracks:()=>[track]};}}},
    MediaRecorder:Recorder, URLSearchParams, URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},
    Blob, FormData, crypto:{randomUUID}, Date:{now:()=>now}, DOMException,
    location:{search:options.noToken ? '' : '?t=test-token'},
    sessionStorage:{getItem:()=>options.storedToken || '',setItem(){}},
    setInterval(){return 1;}, clearInterval(){}, queueMicrotask,
    fetch:async (url, init) => {
      if (url === '/api/config') return {ok:true,json:async()=>({questions:[{id:'q1',en:'What was valuable?'}], max_seconds:90,is_test:true})};
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
  assert.equal(page.requests[0].get('audio').type,'audio/mp4');assert.match(page.element('status').textContent,/audio are saved/);
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
