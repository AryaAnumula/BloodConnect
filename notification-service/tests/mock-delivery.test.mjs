import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,readdirSync,readFileSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
import {createNotificationServer} from '../src/server.mjs';
const token='synthetic-test-only-token-with-32-characters';
const event=()=>({event_id:randomUUID(),recipient_id:randomUUID(),type:'APPOINTMENT_REMINDER',record_id:randomUUID(),due_at:new Date().toISOString(),channels:['IN_APP','EMAIL_MOCK']});
async function serve(dir,run){const server=createNotificationServer({token,mockEnabled:true,receiptDir:dir});await new Promise(r=>server.listen(0,'127.0.0.1',r));try{await run(`http://127.0.0.1:${server.address().port}`);}finally{await new Promise(r=>server.close(r));}}
async function post(base,body,authorized=true){return fetch(base+'/internal/notifications',{method:'POST',headers:{'content-type':'application/json',...(authorized?{Authorization:`Bearer ${token}`}:{})},body:JSON.stringify(body)});}
test('persistent mock receipt survives service restart and rejects conflicting replay',async()=>{const dir=mkdtempSync(join(tmpdir(),'bb22-'));try{const body=event();let receipt;await serve(dir,async b=>{const r=await post(b,body);assert.equal(r.status,202);receipt=await r.json();assert.equal(receipt.delivery_mode,'mock');assert.equal(readdirSync(dir).length,1);assert.ok(!readFileSync(join(dir,readdirSync(dir)[0]),'utf8').includes(token));});await serve(dir,async b=>{assert.deepEqual(await (await post(b,body)).json(),receipt);assert.equal((await post(b,{...body,recipient_id:randomUUID()})).status,409);});}finally{rmSync(dir,{recursive:true,force:true});}});
test('mock rejects unauthorized, unknown fields, invalid channels, oversized input',async()=>{const dir=mkdtempSync(join(tmpdir(),'bb22-'));try{await serve(dir,async b=>{assert.equal((await post(b,event(),false)).status,401);assert.equal((await post(b,{...event(),health:'private'})).status,400);assert.equal((await post(b,{...event(),channels:['SMS_REAL']})).status,400);assert.equal((await post(b,{...event(),extra:'x'.repeat(20000)})).status,413);assert.equal(readdirSync(dir).length,0);});}finally{rmSync(dir,{recursive:true,force:true});}});

test('corrupt receipt store returns redacted 503, never fabricated success',async()=>{const dir=mkdtempSync(join(tmpdir(),'bb22-'));try{const body=event();writeFileSync(join(dir,body.event_id+'.json'),'{broken');await serve(dir,async b=>{const response=await post(b,body);assert.equal(response.status,503);assert.ok(!(await response.text()).includes(dir));});}finally{rmSync(dir,{recursive:true,force:true});}});
