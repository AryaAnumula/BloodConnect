// Independent executed-code review. Mock DOM/API, not a real backend or browser.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
const ROOT=process.env.BLOODCONNECT_REVIEW_REPO || process.cwd();
if(!ROOT)throw new Error('Set BLOODCONNECT_REVIEW_REPO to an isolated repo checkout.');
const A='00000000-0000-4000-8000-000000000001';
const B='00000000-0000-4000-8000-000000000002';
function element(){return {hidden:true,disabled:false,textContent:'',children:[],events:{},
 addEventListener(name,fn){this.events[name]=fn;},
 appendChild(child){this.children.push(child);},replaceChildren(...children){this.children=children;}};}
function setup(kind){
 const nodes=new Map();const calls=[];let values=kind==='eligibility'?{donor_id:A}:{blood_group:'O+',location:'Bengaluru',eligibility_status:'',page_size:'20'};
 const document={querySelector(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);},createElement(){return element();}};
 const status={value:''};
 const apiFetch=path=>new Promise((resolve,reject)=>calls.push({path,resolve,reject}));
 const code=readFileSync(join(ROOT,`frontend/static/js/pages/${kind}.js`),'utf8').replace(/^\s*import\s+\{[^}]+\}\s+from\s+['"][^'"]+['"];\s*/,'');
 vm.runInNewContext(code,{document,apiFetch,showStatus:message=>status.value=message,FormData:class{constructor(){this.data={...values};}get(name){return this.data[name]??null;}},URLSearchParams,console});
 const form=document.querySelector(kind==='eligibility'?'#eligibility-form':'#donor-search-form');
 return {nodes,calls,status,set(next){values={...values,...next};},submit(){return form.events.submit({preventDefault(){}});},next(){document.querySelector('#next-page').events.click();}};
}
const result=donor=>({id:donor,donor_id:donor,status:'ELIGIBLE',reason_codes:[],reasons:[],assessed_at:'2026-01-01T00:00:00Z',rules_version:'synthetic-only',is_stale:false});
const page=location=>({count:40,page:1,page_size:20,results:[{id:A,blood_group:'O+',location,eligibility_status:'NOT_SCREENED'}]});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('BB09 newest search survives a slow older success',async()=>{
 const h=setup('search');h.submit();h.set({location:'Hyderabad'});h.submit();
 h.calls[1].resolve(page('Hyderabad'));await tick();h.calls[0].resolve(page('Bengaluru'));await tick();
 const location=h.nodes.get('#donor-results-body').children[0].children[2].textContent;
 assert.equal(location,'Hyderabad');
});
test('BB09 newest search survives a slow older error',async()=>{
 const h=setup('search');h.submit();h.set({location:'Hyderabad'});h.submit();
 h.calls[1].resolve(page('Hyderabad'));await tick();h.calls[0].reject(Object.assign(new Error('Synthetic old denial'),{status:403}));await tick();
 assert.equal(h.status.value,'Search completed.');
});
test('BB09 filter edit plus Next must retain applied query or restart page1',async()=>{
 const h=setup('search');h.submit();h.calls[0].resolve(page('Bengaluru'));await tick();
 h.set({location:'Hyderabad'});h.next();await tick();
 if(h.calls.length===1){assert.ok(h.nodes.get('#next-page').disabled);return;}
 const q=new URL(h.calls[1].path,'http://synthetic.test').searchParams;
 assert.ok((q.get('location')==='Bengaluru'&&q.get('page')==='2')||(q.get('location')==='Hyderabad'&&q.get('page')==='1'),`Wrong pagination: ${q}`);
 h.calls[1].resolve({...page(q.get('location')),page:Number(q.get('page'))});await tick();
});

test('BB09 latest error is not replaced by old success',async()=>{
 const h=setup('search');h.submit();h.set({location:'Hyderabad'});h.submit();
 h.calls[1].reject(Object.assign(new Error('new denial'),{status:403}));await tick();
 h.calls[0].resolve(page('Bengaluru'));await tick();
 assert.equal(h.nodes.get('#donor-results').hidden,true);assert.match(h.status.value,/Access denied/);
});
test('BB09 invalid submission supersedes an older request',async()=>{
 const h=setup('search');h.submit();h.set({location:'x'.repeat(121)});h.submit();
 h.calls[0].resolve(page('Bengaluru'));await tick();assert.equal(h.calls.length,1);
 assert.match(h.status.value,/120/);assert.equal(h.nodes.get('#donor-results').hidden,true);
});
test('BB09 new submit resets edited filters to page one',async()=>{
 const h=setup('search');h.submit();h.calls[0].resolve(page('Bengaluru'));await tick();
 h.set({location:'Hyderabad',page_size:'10'});h.submit();
 const q=new URL(h.calls[1].path,'http://synthetic.test').searchParams;
 assert.equal(q.get('page'),'1');assert.equal(q.get('location'),'Hyderabad');assert.equal(q.get('page_size'),'10');
 h.calls[1].resolve({...page('Hyderabad'),page_size:10});await tick();
});
test('BB09 combines filters and safely encodes plus signs',async()=>{
 const h=setup('search');h.set({eligibility_status:'NOT_SCREENED',location:'  Bengaluru  '});h.submit();
 const path=h.calls[0].path;assert.match(path,/blood_group=O%2B/);
 const q=new URL(path,'http://synthetic.test').searchParams;
 assert.equal(q.get('location'),'Bengaluru');assert.equal(q.get('eligibility_status'),'NOT_SCREENED');
 h.calls[0].resolve(page('Bengaluru'));await tick();
});
for(const values of [{blood_group:'XX'},{eligibility_status:'UNKNOWN'},{page_size:'0'},{page_size:'101'},{page_size:'2.5'},{page_size:''}]) {
 test(`BB09 invalid filter blocked: ${JSON.stringify(values)}`,async()=>{
  const h=setup('search');h.set(values);h.submit();await tick();assert.equal(h.calls.length,0);assert.equal(h.nodes.get('#donor-results').hidden,true);
 });
}
test('BB09 empty result has explicit empty state',async()=>{
 const h=setup('search');h.submit();h.calls[0].resolve({count:0,page:1,page_size:20,results:[]});await tick();
 assert.equal(h.nodes.get('#result-count').textContent,'No matching donors.');assert.equal(h.nodes.get('#next-page').disabled,true);assert.equal(h.nodes.get('#previous-page').disabled,true);
});
test('BB09 renders hostile-looking text literally in a text cell',async()=>{
 const h=setup('search');h.submit();h.calls[0].resolve(page('<img src=x onerror=alert(1)>'));await tick();
 assert.equal(h.nodes.get('#donor-results-body').children[0].children[2].textContent,'<img src=x onerror=alert(1)>');
});
for(const status of [400,403,501,503])test(`BB09 API ${status} clears results`,async()=>{
 const h=setup('search');h.submit();h.calls[0].reject(Object.assign(new Error('synthetic failure'),{status}));await tick();
 assert.equal(h.nodes.get('#donor-results').hidden,true);assert.notEqual(h.status.value,'Search completed.');
});
test('BB09 malformed summary is not displayed',async()=>{
 const h=setup('search');h.submit();const data=page('Bengaluru');data.results[0].eligibility_status='INVENTED';h.calls[0].resolve(data);await tick();
 assert.equal(h.nodes.get('#donor-results').hidden,true);assert.match(h.status.value,/invalid donor summary/);
});
