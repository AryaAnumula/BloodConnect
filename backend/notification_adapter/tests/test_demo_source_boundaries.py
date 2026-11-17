import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from django.core.management.base import CommandError
from notification_adapter.demo import source_records


class DemoSourceBoundaryTests(TestCase):
    def test_valid_and_invalid_metadata_hash_duplicate_and_missing_source(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'data.json'
            data = {'metadata': {'demo_only': True, 'dataset_version': 'bloodconnect-synthetic-v1'},
                    'tables': {k: [{'id': k}] for k in ('accounts', 'donors', 'screenings', 'appointments', 'slots', 'camps')}}

            def save(payload, checksum=None):
                raw = json.dumps(payload).encode()
                path.write_bytes(raw)
                (root / 'manifest.json').write_text(json.dumps({'files': {'data.json': checksum or hashlib.sha256(raw).hexdigest()}}))

            save(data)
            self.assertEqual(source_records(path)[1]['accounts']['accounts']['id'], 'accounts')
            for mutate in ('checksum', 'demo_only', 'version', 'duplicate', 'missing'):
                changed = json.loads(json.dumps(data))
                if mutate == 'demo_only': changed['metadata']['demo_only'] = False
                if mutate == 'version': changed['metadata']['dataset_version'] = 'old'
                if mutate == 'duplicate': changed['tables']['accounts'].append({'id': 'accounts'})
                if mutate == 'missing': del changed['tables']['donors']
                save(changed, 'wrong' if mutate == 'checksum' else None)
                with self.subTest(mutate=mutate), self.assertRaises(CommandError):
                    source_records(path)
            path.unlink()
            with self.assertRaises(CommandError): source_records(path)

    def test_oversized_payload_is_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'oversized.json'
            path.write_bytes(b'x' * (16 * 1024 * 1024 + 1))
            with self.assertRaises(CommandError): source_records(path)
