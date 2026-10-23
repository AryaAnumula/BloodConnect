import http from 'node:http';
import { timingSafeEqual } from 'node:crypto';
import { pathToFileURL } from 'node:url';

export function createNotificationServer({ token }) {
  if (!token || token.length < 32 || token.startsWith('CHANGE_ME')) throw new Error('Set a generated internal token.');
  return http.createServer((req, res) => {
    const send = (status, body) => {
      res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify(body));
    };
    if (req.method === 'GET' && req.url === '/health/live') return send(200, { status: 'ok', delivery: 'not_implemented' });
    if (req.method !== 'POST' || req.url !== '/internal/notifications') return send(404, { error: { code: 'not_found', message: 'Not found.' } });
    const supplied = Buffer.from(req.headers.authorization || '');
    const expected = Buffer.from(`Bearer ${token}`);
    if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) return send(401, { error: { code: 'invalid_service_authentication', message: 'Service authentication required.' } });
    // No delivery recorded, no recipient logged, no fabricated 202 response.
    req.resume();
    return send(501, { error: { code: 'not_implemented', message: 'Notification delivery is outside this Sprint-1 starter.' } });
  });
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const server = createNotificationServer({ token: process.env.NOTIFICATION_INTERNAL_TOKEN });
  server.listen(Number(process.env.PORT || 3000), '0.0.0.0', () => console.log('Notification scaffold listening; delivery not implemented.'));
}
