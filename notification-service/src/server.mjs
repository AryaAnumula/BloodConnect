import http from 'node:http';
import { timingSafeEqual, createHash, randomUUID } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { mkdirSync, existsSync, readFileSync, openSync, writeFileSync, fsyncSync, closeSync, renameSync, unlinkSync } from 'node:fs';
import path from 'node:path';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const channels = new Set(['IN_APP', 'EMAIL_MOCK', 'SMS_MOCK']);
const types = new Set(['NEAR_EXPIRY', 'LOW_STOCK', 'APPOINTMENT_REMINDER', 'APPOINTMENT_CANCELLED']);
function normalize(event) {
  const keys = ['event_id','recipient_id','type','record_id','due_at','channels'];
  if (!event || typeof event !== 'object' || Array.isArray(event) || Object.keys(event).sort().join() !== [...keys].sort().join()) throw new Error('invalid');
  if (![event.event_id,event.recipient_id,event.record_id].every(x => typeof x === 'string' && uuid.test(x))) throw new Error('invalid');
  if (!types.has(event.type) || typeof event.due_at !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(event.due_at) || !Number.isFinite(Date.parse(event.due_at))) throw new Error('invalid');
  if (!Array.isArray(event.channels) || !event.channels.length || event.channels.length > 3 || new Set(event.channels).size !== event.channels.length || !event.channels.every(c => channels.has(c))) throw new Error('invalid');
  return { event_id:event.event_id.toLowerCase(), recipient_id:event.recipient_id.toLowerCase(), type:event.type, record_id:event.record_id.toLowerCase(), due_at:new Date(event.due_at).toISOString(), channels:[...event.channels].sort() };
}
function recordReceipt(dir, event) {
  const fingerprint=createHash('sha256').update(JSON.stringify(event)).digest('hex');
  const destination=path.join(dir,event.event_id+'.json');
  if (existsSync(destination)) {
    const old=JSON.parse(readFileSync(destination,'utf8'));
    if (old.fingerprint!==fingerprint) return { conflict:true };
    if (!old.receipt || old.receipt.event_id!==event.event_id || old.receipt.delivery_mode!=='mock' || !Array.isArray(old.receipt.receipts) || old.receipt.receipts.length!==event.channels.length || old.receipt.receipts.some((r,i)=>!r || r.channel!==event.channels[i] || r.status!=='DELIVERED')) throw new Error('invalid receipt store');
    return { receipt:old.receipt };
  }
  const receipt={event_id:event.event_id,delivery_mode:'mock',receipts:event.channels.map(channel=>({channel,status:'DELIVERED'}))};
  const temporary=path.join(dir,`.${event.event_id}.${randomUUID()}.tmp`);
  let fd;
  try {
    fd=openSync(temporary,'wx',0o600);
    writeFileSync(fd,JSON.stringify({fingerprint,receipt}),'utf8');fsyncSync(fd);closeSync(fd);fd=undefined;
    // One Node process, synchronous writes: no interleaving between existence check and rename.
    renameSync(temporary,destination);
    try { const directory=openSync(dir,'r');try { fsyncSync(directory); } finally { closeSync(directory); } } catch { /* Windows lacks directory fsync; no production/power-loss guarantee. */ }
    return { receipt };
  } finally {
    if (fd!==undefined) closeSync(fd);
    if (existsSync(temporary)) unlinkSync(temporary);
  }
}
export function createNotificationServer({ token, mockEnabled=false, receiptDir=null }) {
  if (!token || token.length < 32 || token.startsWith('CHANGE_ME')) throw new Error('Set a generated internal token.');
  if (mockEnabled && !receiptDir) throw new Error('Configure a persistent mock receipt directory.');
  if (mockEnabled) mkdirSync(receiptDir,{recursive:true,mode:0o700});
  return http.createServer((req,res)=>{
    const send=(status,body)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(body));};
    const error=(status,code,message)=>send(status,{error:{code,message}});
    if (req.method==='GET' && req.url==='/health/live') return send(200,{status:'ok',delivery:mockEnabled?'mock':'not_implemented'});
    if (req.method!=='POST' || req.url!=='/internal/notifications') return error(404,'not_found','Not found.');
    const supplied=Buffer.from(req.headers.authorization||'');const expected=Buffer.from(`Bearer ${token}`);
    if (supplied.length!==expected.length || !timingSafeEqual(supplied,expected)) { req.resume();return error(401,'invalid_service_authentication','Service authentication required.'); }
    if (!mockEnabled) { req.resume();return error(501,'not_implemented','Mock delivery is not enabled.'); }
    if ((req.headers['content-type']||'').split(';')[0].trim()!=='application/json') { req.resume();return error(400,'invalid_event','JSON event required.'); }
    let size=0;const chunks=[];let rejected=false;
    req.on('data',chunk=>{size+=chunk.length;if(size>16384){if(!rejected){rejected=true;error(413,'event_too_large','Event is too large.');}}else if(!rejected)chunks.push(chunk);});
    req.on('end',()=>{
      if(rejected)return;
      let event;
      try { event=normalize(JSON.parse(Buffer.concat(chunks).toString('utf8'))); } catch { return error(400,'invalid_event','Invalid notification event.'); }
      try { const stored=recordReceipt(receiptDir,event);if(stored.conflict)return error(409,'event_conflict','Event ID has a different payload.');return send(202,stored.receipt); }
      catch { return error(503,'receipt_store_unavailable','Mock receipt storage is unavailable.'); }
    });
    req.on('error',()=>{if(!res.headersSent)error(400,'invalid_event','Request failed.');});
  });
}
if (process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  const enabled=process.env.NOTIFICATION_MOCK_ENABLED==='1';
  const server=createNotificationServer({token:process.env.NOTIFICATION_INTERNAL_TOKEN,mockEnabled:enabled,receiptDir:process.env.NOTIFICATION_MOCK_RECEIPT_DIR||null});
  server.listen(Number(process.env.PORT||3000),'0.0.0.0',()=>console.log(enabled?'Notification service listening in MOCK mode; no real carriers.':'Notification service listening; mock delivery disabled.'));
}
