// Execute actual registration page JS; controlled DOM/API, not a browser or real backend.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
function element(){return {textContent:'',children:[],disabled:false,events:{},addEventListener(n,f){this.events[n]=f;},replaceChildren(){this.children=[];},appendChild(x){this.children.push(x);}};}
function setup(){
 const form=element(),errors=element(),button=element();let reset=0;form.querySelector=()=>button;form.reset=()=>reset++;
 const calls=[],status=[];
 const document={querySelector:id=>id==='#registration-form'?form:errors,createElement:()=>element()};
 const code=readFileSync('frontend/static/js/pages/registration.js','utf8').replace(/^\s*import[^;]+;\s*/,'');
 vm.runInNewContext(code,{document,apiFetch:(...args)=>new Promise((resolve,reject)=>calls.push({args,resolve,reject})),showStatus:m=>status.push(m),FormData:class{*[Symbol.iterator](){yield ['email','synthetic@example.test'];yield ['password','Synthetic-Password-123'];}}});
 return {errors,button,calls,status,get reset(){return reset;},submit:()=>form.events.submit({preventDefault(){}})};
}
test('registration prevents duplicate submissions, resets only on success and reenables button',async()=>{
 const h=setup();const a=h.submit();await h.submit();assert.equal(h.calls.length,1);assert.equal(h.button.disabled,true);
 h.calls[0].resolve({});await a;assert.equal(h.reset,1);assert.equal(h.button.disabled,false);assert.match(h.status.at(-1),/Account created/);
});
test('registration renders approved field errors as literal text and ignores unknown field names',async()=>{
 const h=setup();const p=h.submit();h.calls[0].reject(Object.assign(new Error('Request validation failed.'),{fields:{email:['<img src=x onerror=alert(1)>'],role:['SECRET'],password:['At least 12 characters.']}}));await p;
 assert.equal(h.reset,0);assert.equal(h.errors.children.length,2);assert.equal(h.errors.children[0].textContent,'Email: <img src=x onerror=alert(1)>');assert.equal(h.button.disabled,false);
});
test('registration can be retried after a server failure',async()=>{
 const h=setup();const p=h.submit();h.calls[0].reject(new Error('Unavailable'));await p;const q=h.submit();assert.equal(h.calls.length,2);h.calls[1].resolve({});await q;assert.equal(h.reset,1);
});
