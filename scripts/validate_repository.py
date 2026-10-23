"""Validate source/story/contract wiring. Does not certify business acceptance."""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys
import yaml
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[1]
errors = []
def check(condition, message):
    if not condition:
        errors.append(message)

stories = json.loads((ROOT / 'docs/planning/stories.json').read_text())
expected = [f'BB-{i:02d}' for i in range(1, 13)]
check([s['id'] for s in stories] == expected, 'Story index must contain exactly BB-01..BB-12.')
prompts = sorted(p.stem for p in (ROOT / 'docs/ai-prompts').glob('BB-*.md'))
has_private_prompts = (ROOT / 'docs/ai-prompts').exists()
if has_private_prompts:
    check(prompts == expected, 'Workpack must contain exactly 12 prompts.')
api = yaml.safe_load((ROOT / 'docs/api/openapi.yaml').read_text())
for name in ['openapi.yaml', 'notifications.openapi.yaml']:
    validate_spec(yaml.safe_load((ROOT / 'docs/api' / name).read_text()))
check(len(api['paths']) == 11, 'Unexpected API path count; update approved contract and validator together.')
operation_ids = []
for path, methods in api['paths'].items():
    check(not path.endswith('/'), f'Trailing slash in {path}')
    for method, operation in methods.items():
        operation_ids.append(operation['operationId'])
        for story_id in operation['x-stories']:
            check(story_id in expected, f'Out-of-scope story in {path}: {story_id}')
        if operation['x-implementation-status'] == 'stub':
            check('501' in operation['responses'], f'Unfinished endpoint lacks honest 501 contract: {path}')
        if method == 'post':
            check(any(p.get('name') == 'X-CSRFToken' for p in operation.get('parameters', [])), f'Missing explicit CSRF contract: {path}')
check(len(operation_ids) == len(set(operation_ids)), 'Operation IDs must be unique.')
if has_private_prompts:
    for story in stories:
        text = (ROOT / 'docs/ai-prompts' / (story['id'] + '.md')).read_text()
        check(story['title'] in text, f'Prompt title mismatch: {story["id"]}')
        check(story['Acceptance criteria'] in text, f'Source criteria changed: {story["id"]}')
        check(story['User story'] in text, f'Source user-story wording changed: {story["id"]}')
        check(story['owner'] in text, f'Missing member branch: {story["id"]}')
        check('Completion report' in text, f'Missing handoff: {story["id"]}')
        member_text = (ROOT / 'docs/team' / (story['owner'] + '.md')).read_text()
        check(f'../ai-prompts/{story["id"]}.md' in member_text, f'Member prompt link missing: {story["id"]}')
for folder in ['backend', 'scripts']:
    for path in (ROOT / folder).rglob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
# Validate actual relative Markdown links, not bare code-path suggestions.
for path in ROOT.rglob('*.md'):
    if any(part in {'.venv', 'node_modules', '.git'} for part in path.parts):
        continue
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
        if '://' in target or target.startswith(('#', 'mailto:')):
            continue
        relative = target.split('#')[0]
        if relative:
            check((path.parent / relative).exists(), f'Broken link in {path.relative_to(ROOT)}: {target}')
manifest = json.loads((ROOT / 'docs/sources/manifest.json').read_text())
pdf = ROOT / 'docs/sources' / manifest['baseline_pdf']['filename']
check(hashlib.sha256(pdf.read_bytes()).hexdigest() == manifest['baseline_pdf']['sha256'], 'Supplied baseline PDF checksum changed.')
workflow = yaml.load((ROOT / '.github/workflows/starter-checks.yml').read_text(), Loader=yaml.BaseLoader)
check(list(workflow.get('on', {}).keys()) == ['workflow_dispatch'], 'CI must remain manual until tool approval.')
check(not (ROOT / '.env').exists() or (ROOT / '.gitignore').read_text().find('.env') >= 0, 'Local secrets must be ignored.')
if errors:
    print('\n'.join('FAIL: ' + message for message in errors))
    raise SystemExit(1)
print('PASS: story index, optional private workpack, two OpenAPI specs, Python syntax, links, baseline checksum and manual CI wiring. Business acceptance is not certified.')
