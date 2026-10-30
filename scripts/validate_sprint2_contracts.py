"""Validate proposed Sprint2 design structure; not implementation/approval evidence."""
from pathlib import Path
import json,re,yaml
from openapi_spec_validator import validate_spec
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'docs/sprint2'
stories=json.loads((base/'stories.json').read_text(encoding='utf-8'))
assert [s['id'] for s in stories]==[f'BB-{n:02d}' for n in range(13,25)]
known={s['id'] for s in stories};covered=set();ids=set()
for name in ['openapi.proposed.yaml','notifications.proposed.yaml']:
 spec=yaml.safe_load((base/name).read_text(encoding='utf-8'));validate_spec(spec)
 for path,methods in spec['paths'].items():
  assert not path.endswith('/')
  for method,op in methods.items():
   assert op['operationId'] not in ids;ids.add(op['operationId'])
   assert op.get('x-owner');assert op['x-implementation-status'] in {'not_implemented','implemented'}
   assert set(op['x-stories'])<=known;covered.update(op['x-stories'])
   if name=='openapi.proposed.yaml' and method in {'post','patch','delete'}:
    assert any(p['name']=='X-CSRFToken' for p in op.get('parameters',[]))
assert covered==known,(covered,known)
dec=json.loads((ROOT/'config/sprint2-decisions.json').read_text(encoding='utf-8'))
for d in dec['decisions']:
 assert d['status'] in {'PROPOSED','APPROVED','REJECTED','SUPERSEDED'}
 if d['status']=='APPROVED':assert all(d.get(k) for k in ['approved_by','approved_at','evidence'])
for p in base.rglob('*.md'):
 for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
  if '://' not in target and not target.startswith('#'):
   assert (p.parent/target.split('#')[0]).exists(),(p,target)
print('PASS:12 adopted Sprint2 story records, public/internal OpenAPI, unique operations, CSRF, decision shapes and local links. PROPOSED is not approved or implemented.')
