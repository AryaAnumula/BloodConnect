"""Create local secrets without printing them. Never overwrites .env."""
from pathlib import Path
import os
import secrets
root = Path(__file__).resolve().parents[1]
path = root / '.env'
if path.exists():
    raise SystemExit('.env already exists; inspect it locally rather than overwriting it.')
text = (root / '.env.example').read_text()
text = text.replace('CHANGE_ME_GENERATE_A_LONG_RANDOM_VALUE', secrets.token_urlsafe(60))
text = text.replace('CHANGE_ME_GENERATE_A_RANDOM_VALUE', 'PLACEHOLDER_REPLACE_EACH')
while 'PLACEHOLDER_REPLACE_EACH' in text:
    text = text.replace('PLACEHOLDER_REPLACE_EACH', secrets.token_urlsafe(32), 1)
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write(text)
print('Created local .env with generated values. No values were printed. Do not commit it.')
