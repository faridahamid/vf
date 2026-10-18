'use strict';
const test=require('node:test'), assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function page(confirm=true){
 const nodes=new Map(),requests=[];
 const el=id=>{if(!nodes.has(id))nodes.set(id,{disabled:false,textContent:'',value:'',handlers:{},addEventListener(k,fn){this.handlers[k]=fn;}});return nodes.get(id);};
 const state={snapshot:'snapshot',responses:12,can_generate:true,saved:null,changed:false,estimated_max_usd:.04};
 const ctx=vm.createContext({document:{getElementById:el,querySelectorAll:()=>[]},window:{confirm:()=>confirm},FormData,
  fetch:async(url,init)=>{requests.push({url,init});return {ok:true,json:async()=>init.method==='POST'?{saved:true}:state};}});
 vm.runInContext(fs.readFileSync(__dirname+'/static/admin.js','utf8'),ctx);
 return {el,requests,ctx,state,async load(){await vm.runInContext('password="test";refreshReport()',ctx);}};
}
test('report status never calls paid generation',async()=>{const p=page();await p.load();assert.equal(p.requests.length,1);assert.equal(p.requests[0].init.method,undefined);assert.equal(p.el('report-generate').disabled,false);});
test('cancelled confirmation never calls generation',async()=>{const p=page(false);await p.load();await p.el('report-generate').handlers.click();assert.equal(p.requests.length,1);});
test('confirmed generation makes one POST and saved unchanged reports disable generation',async()=>{const p=page();await p.load();await p.el('report-generate').handlers.click();assert.equal(p.requests.filter(r=>r.init.method==='POST').length,1);p.state.saved={generated_at:'2026-10-18',pages:5,responses:12,usage:{estimated_usd:.01}};await p.load();assert.equal(p.el('report-generate').disabled,true);assert.equal(p.el('report-download').disabled,false);});
