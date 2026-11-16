"""BB-16 browser walkthrough (local isolated lane, synthetic example.test data, real config.urls).

Drives installed Microsoft Edge headless via Playwright. Password read from a local file, never printed.
Usage: walk.py <walk_dir> <base_url>
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

WALK = pathlib.Path(sys.argv[1])
BASE = sys.argv[2]
PW = (WALK / '.pw').read_text()
UNITS = json.loads((WALK / 'units.json').read_text())
SHOTS = WALK / 'shots'
SHOTS.mkdir(exist_ok=True)
LOG = []
UNKNOWN = '00000000-0000-4000-8000-0000000000aa'


def log(step, text):
    line = f'{len(LOG) + 1:02d}. {step}: {text}'
    LOG.append(line)
    print(line, flush=True)
    (WALK / 'walkthrough.log').write_text(chr(10).join(LOG) + chr(10), encoding='utf-8')


def shot(page, name):
    page.screenshot(path=str(SHOTS / f'{len(LOG):02d}-{name}.png'), full_page=True)


def status(page):
    return page.locator('#status').inner_text().strip()


def login(browser, email):
    ctx = browser.new_context(viewport={'width': 1280, 'height': 900})
    page = ctx.new_page()
    page.on('dialog', lambda d: d.accept())
    page.goto(f'{BASE}/login')
    page.fill('input[name=email]', email)
    page.fill('input[name=password]', PW)
    with page.expect_response(lambda r: r.url.endswith('/api/v1/auth/login')) as resp:
        page.click('form button')
    log('login', f'{email} -> HTTP {resp.value.status}')
    return page


def submit_request(page, quantity):
    page.goto(f'{BASE}/requests/new')
    page.select_option('#request-blood-group', 'A+')
    page.select_option('#request-component', 'RBC')
    page.fill('#request-quantity', str(quantity))
    page.select_option('#request-urgency', 'ROUTINE')
    with page.expect_response(lambda r: r.url.endswith('/api/v1/requests') and r.request.method == 'POST') as resp:
        page.click('#request-form button[type=submit]')
    body = resp.value.json()
    log('requester submits', f'A+ RBC x{quantity} -> HTTP {resp.value.status} {body["status"]} id={body["id"]}')
    return body['id']


def queue(page, status_value):
    page.goto(f'{BASE}/staff/requests')
    page.select_option('#queue-status', status_value)
    with page.expect_response(lambda r: '/api/v1/requests?' in r.url and f'status={status_value}' in r.url):
        page.click('#queue-filter button[type=submit]')
    page.wait_for_timeout(300)


def stock(page, label):
    page.goto(f'{BASE}/staff/inventory')
    page.wait_for_load_state('networkidle')
    text = page.locator('#stock').inner_text().strip().replace('\n', ' | ')
    log(f'stock page ({label})', text[:300])
    shot(page, f'stock-{label}')


def issue(page, request_id, unit_ids, name):
    box = page.locator(f'[id="units-{request_id}"]')
    box.fill('\n'.join(unit_ids))
    with page.expect_response(lambda r: r.url.endswith(f'/requests/{request_id}/issues')) as resp:
        page.get_by_role('button', name=f'Issue units for request {request_id}').click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(300)
    code = resp.value.status
    try:
        payload = resp.value.json()
    except Exception:
        payload = {}
    detail = payload.get('error', {}).get('code') if 'error' in payload else \
        f'{payload.get("request_status")} fulfilled={payload.get("fulfilled_quantity")}'
    log(f'staff issues {name}', f'HTTP {code} {detail}; page says: "{status(page)}"')
    shot(page, f'issue-{name}')
    return code


with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    requester = login(browser, 'bb16-walk-requester@example.test')
    main_id = submit_request(requester, 2)
    other_id = submit_request(requester, 1)

    staff = login(browser, 'bb16-walk-staff@example.test')
    stock(staff, 'before')
    queue(staff, 'SUBMITTED')
    for rid in (main_id, other_id):
        with staff.expect_response(lambda r: r.url.endswith(f'/requests/{rid}/status')) as resp:
            staff.get_by_role('button', name=f'Approve request {rid}').click()
        staff.wait_for_load_state('networkidle')
        log('staff approves', f'{rid} -> HTTP {resp.value.status}')
    queue(staff, 'APPROVED')
    row_text = staff.locator('#queue-body').inner_text().replace('\n', ' | ')
    log('approved queue', row_text[:300])
    shot(staff, 'approved-queue')

    issue(staff, main_id, [UNITS['BB16-WALK-EXPIRES-TODAY']], 'expires-today')
    issue(staff, main_id, [UNITS['BB16-WALK-QUARANTINED']], 'quarantined')
    issue(staff, main_id, [UNKNOWN], 'unknown-unit')
    issue(staff, main_id, [UNITS['BB16-WALK-GOOD-1'], UNITS['BB16-WALK-QUARANTINED']], 'mixed-good-and-quarantined')
    issue(staff, main_id, [UNITS['BB16-WALK-GOOD-1']], 'good-1-partial')

    requester.goto(f'{BASE}/requests/{main_id}')
    requester.wait_for_load_state('networkidle')
    log('requester detail (partial)', f'close button visible={requester.locator("#tracking-close").is_visible()}; '
        + requester.locator('main').inner_text().replace('\n', ' | ')[:250])
    shot(requester, 'requester-partial')

    issue(staff, other_id, [UNITS['BB16-WALK-GOOD-1']], 'reuse-good-1-on-other-request')
    queue(staff, 'APPROVED')
    issue(staff, main_id, [UNITS['BB16-WALK-GOOD-2']], 'good-2-completes')
    queue(staff, 'ISSUED')
    log('issued queue', staff.locator('#queue-body').inner_text().replace('\n', ' | ')[:300])
    shot(staff, 'issued-queue')
    stock(staff, 'after')

    requester.goto(f'{BASE}/requests/{main_id}')
    requester.wait_for_load_state('networkidle')
    requester.wait_for_timeout(500)
    log('requester detail (issued, BB-19 page)', f'close button visible={requester.locator("#tracking-close").is_visible()}; '
        f'page says: "{status(requester)}"')
    shot(requester, 'requester-issued-detail')
    # BB-19 page cannot render for a real requester (reads identity.user; real /me is flat), so the
    # owner close is sent from the same signed-in browser session over HTTP (session + CSRF).
    closed = requester.evaluate("""async id => {
        const token = (await (await fetch('/api/v1/auth/csrf', {credentials: 'same-origin'})).json()).csrf_token;
        const send = () => fetch(`/api/v1/requests/${id}/close`, {method: 'POST', credentials: 'same-origin',
            headers: {'X-CSRFToken': token}});
        const first = await send(); const a = await first.json();
        const again = await send(); const b = await again.json();
        return {first: first.status, status: a.status, updated: a.updated_at, replay: again.status,
                same_updated: a.updated_at === b.updated_at};
    }""", main_id)
    log('requester closes (HTTP from browser session)', json.dumps(closed))
    after = staff.evaluate("""async id => {
        const token = (await (await fetch('/api/v1/auth/csrf', {credentials: 'same-origin'})).json()).csrf_token;
        const r = await fetch(`/api/v1/requests/${id}/issues`, {method: 'POST', credentials: 'same-origin',
            headers: {'X-CSRFToken': token, 'Content-Type': 'application/json'}, body: JSON.stringify({unit_ids: [arguments_unit]})});
        return {status: r.status, code: (await r.json()).error?.code};
    }""".replace('arguments_unit', json.dumps(UNITS['BB16-WALK-QUARANTINED'])), main_id)
    log('staff issue after close', json.dumps(after))
    stock(staff, 'after-close')
    browser.close()

(WALK / 'walkthrough.log').write_text('\n'.join(LOG) + '\n', encoding='utf-8')
