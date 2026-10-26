import importlib.util
from pathlib import Path
from datetime import datetime, timezone
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/measure_availability.py'
spec = importlib.util.spec_from_file_location('availability', path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class AvailabilityFixture:
    def protocol(self, **overrides):
        p = dict(protocol_id='SYNTHETIC_UNIT_TEST_ONLY', environment_name='SYNTHETIC_LOOPBACK_NOT_ACCEPTANCE', source_revision='1'*40, approval_reference='SYNTHETIC_TEST_NOT_APPROVAL', approved_by='SYNTHETIC_TEST_NOT_TEAM_APPROVAL', approved_at='2026-01-01T00:00:00Z', start='2026-01-02T00:00:00Z', end='2026-01-02T00:00:20Z', interval_seconds=10, timeout_seconds=2, maintenance=[])
        p.update(overrides); return p
    def samples(self, second_ready=True):
        return [dict(scheduled_at=f'2026-01-02T00:00:{s:02d}Z', observed_at=f'2026-01-02T00:00:{s:02d}Z', ready=ready, http_status=200 if ready else 503) for s,ready in [(0,True),(10,second_ready)]]
    def report(self, p=None, rows=None, now='2026-01-02T00:00:30Z'):
        return m.summarize(p or self.protocol(), self.samples() if rows is None else rows, now=m.timestamp(now))

class AvailabilityTests(AvailabilityFixture, unittest.TestCase):
    def test_complete_synthetic_window_is_not_story_completion(self):
        r=self.report(); self.assertTrue(r['sampled_threshold_met']); self.assertFalse(r['story_complete'])
    def test_outage_is_not_uptime(self):
        self.assertEqual(self.report(rows=self.samples(False))['sampled_availability_percent'],50)
    def test_missing_samples_stay_unknown(self):
        r=self.report(rows=self.samples()[:1]); self.assertEqual(r['unknown_seconds'],10); self.assertFalse(r['sampled_threshold_met'])
    def test_future_window_does_not_pass(self):
        r=self.report(rows=self.samples()[:1],now='2026-01-02T00:00:05Z'); self.assertFalse(r['window_elapsed']); self.assertFalse(r['sampled_threshold_met'])
    def test_overlapping_maintenance_is_not_double_counted(self):
        p=self.protocol(maintenance=[dict(start='2026-01-02T00:00:00Z',end='2026-01-02T00:00:07Z'),dict(start='2026-01-02T00:00:05Z',end='2026-01-02T00:00:10Z')])
        r=self.report(p=p); self.assertEqual(r['eligible_seconds'],10)
    def test_all_maintenance_has_no_false_percentage(self):
        p=self.protocol(maintenance=[dict(start='2026-01-02T00:00:00Z',end='2026-01-02T00:00:20Z')])
        r=self.report(p=p); self.assertIsNone(r['sampled_availability_percent']); self.assertFalse(r['sampled_threshold_met'])
    def test_unapproved_protocol_never_passes(self):
        self.assertFalse(self.report(p=self.protocol(approved_by=None,approved_at=None))['sampled_threshold_met'])
    def test_naive_timestamp_is_rejected(self):
        with self.assertRaises(ValueError): m.timestamp('2026-01-01T00:00:00')
    def test_duplicate_observation_is_rejected(self):
        with self.assertRaises(ValueError): self.report(rows=self.samples()+self.samples()[:1])
    def test_misplaced_or_future_observations_are_rejected(self):
        for value in ['2026-01-02T00:00:04Z','2026-01-03T00:00:00Z']:
            rows=self.samples();rows[0]['observed_at']=value
            with self.assertRaises(ValueError): self.report(rows=rows)
    def test_bad_interval_is_rejected(self):
        for value in [0, True, -1]:
            with self.assertRaises(ValueError): self.report(p=self.protocol(interval_seconds=value))


class ProbeIntegrationTests(unittest.TestCase):
    def test_real_loopback_readiness_and_failure_responses(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from threading import Thread
        import json
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                status = 503 if self.path == '/unready' else 200
                payload = b'not-json' if self.path == '/malformed' else json.dumps({'status':'ready', 'checks':{'database':'ok'}}).encode()
                if self.path == '/redirect':
                    self.send_response(302); self.send_header('Location', '/ready'); self.end_headers(); return
                self.send_response(status); self.end_headers(); self.wfile.write(payload)
            def log_message(self, *args):
                pass
        server = HTTPServer(('127.0.0.1', 0), Handler)
        worker = Thread(target=server.serve_forever, daemon=True); worker.start()
        try:
            base = 'http://127.0.0.1:' + str(server.server_port)
            self.assertEqual(m.probe(base + '/ready', 1), (True, 200))
            self.assertEqual(m.probe(base + '/unready', 1), (False, 503))
            self.assertEqual(m.probe(base + '/malformed', 1), (False, 0))
            self.assertEqual(m.probe(base + '/redirect', 1), (False, 302))
        finally:
            server.shutdown(); worker.join(); server.server_close()




class EvidenceSafetyTests(AvailabilityFixture, unittest.TestCase):
    """Provenance, locking, CLI and evidence-integrity checks."""
    def test_no_approval_or_deployment_metadata_means_no_pass(self):
        for key in ['protocol_id', 'environment_name', 'source_revision', 'approved_by', 'approved_at', 'approval_reference']:
            with self.subTest(key=key):
                self.assertFalse(self.report(p=self.protocol(**{key:None}))['sampled_threshold_met'])

    def test_approval_after_window_start_is_not_preapproval(self):
        self.assertFalse(self.report(p=self.protocol(approved_at='2026-01-02T00:00:01Z'))['protocol_approval_claimed'])

    def test_environment_revision_and_fingerprint_are_reported(self):
        report = self.report()
        self.assertEqual(report['source_revision'], '1'*40)
        self.assertEqual(report['environment_name'], 'SYNTHETIC_LOOPBACK_NOT_ACCEPTANCE')
        self.assertEqual(report['protocol_sha256'], m.fingerprint(self.protocol()))
        self.assertEqual(report['coverage_percent'],100)

    def test_partial_last_bucket_is_weighted(self):
        p=self.protocol(end='2026-01-02T00:00:25Z')
        rows=self.samples()+[dict(scheduled_at='2026-01-02T00:00:20Z',observed_at='2026-01-02T00:00:20Z',ready=False,http_status=503)]
        r=self.report(p=p,rows=rows)
        self.assertEqual(r['eligible_seconds'],25)
        self.assertEqual(r['sampled_availability_percent'],80)

    def test_bad_http_status_cannot_be_ready(self):
        for status in ['200', 0, 503, True]:
            rows=self.samples();rows[0]['http_status']=status
            with self.assertRaises(ValueError):self.report(rows=rows)

    def test_unknown_coverage_reduces_percentage(self):
        r=self.report(rows=self.samples()[:1])
        self.assertEqual(r['coverage_percent'],50)
        self.assertEqual(r['sampled_availability_percent'],50)

    def test_ready_url_rejects_credentials_queries_and_wrong_path(self):
        for url in ['http://user:secret@localhost/api/v1/health/ready','http://localhost/api/v1/health/ready?token=x','http://localhost/api/v1/health/live','file:///api/v1/health/ready','http:///api/v1/health/ready','http://localhost:bad/api/v1/health/ready']:
            with self.assertRaises(ValueError):m.validate_url(url)
        self.assertEqual(m.validate_url('http://localhost:8000/api/v1/health/ready'),'http://localhost:8000/api/v1/health/ready')

    def test_bound_evidence_cannot_switch_protocol_or_target(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);p=self.protocol();url='http://localhost:8000/api/v1/health/ready'
            first=m.bind_evidence(out,p,url)
            self.assertEqual(m.bind_evidence(out,p,url),first)
            for protocol,target in [(self.protocol(environment_name='different'),url),(p,'http://127.0.0.1:9000/api/v1/health/ready')]:
                with self.assertRaises(ValueError):m.bind_evidence(out,protocol,target)

    def test_orphan_observations_are_not_adopted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);(out/'observations.jsonl').write_text('')
            with self.assertRaises(ValueError):m.bind_evidence(out,self.protocol(),'http://localhost:8000/api/v1/health/ready')

    def test_second_writer_cannot_take_existing_lock(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            with m.evidence_lock(out):
                with self.assertRaises(ValueError):
                    with m.evidence_lock(out):pass
            self.assertFalse((out/'collector.lock').exists())

    def test_malformed_jsonl_does_not_silently_disappear(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'observations.jsonl';path.write_text('{incomplete')
            with self.assertRaises(json.JSONDecodeError):m.read_observations(path)

    def test_cli_dry_run_does_not_create_evidence_or_claim_completion(self):
        import tempfile,json,subprocess,sys
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'evidence'
            example=path.parents[1]/'config/availability.protocol.example.json'
            result=subprocess.run([sys.executable,str(path),'--protocol',str(example),'--output',str(out),'--dry-run'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout)
            self.assertFalse(data['approval_claimed']);self.assertFalse(data['story_complete'])
            self.assertFalse(out.exists())

    def test_cli_unapproved_collection_is_rejected(self):
        import tempfile,subprocess,sys
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'evidence'
            example=path.parents[1]/'config/availability.protocol.example.json'
            result=subprocess.run([sys.executable,str(path),'--protocol',str(example),'--output',str(out)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertFalse(out.exists())

    def test_cli_limit_cannot_report_full_acceptance(self):
        from argparse import Namespace
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        import tempfile,json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/'protocol.json';p.write_text(json.dumps(self.protocol()))
            args=Namespace(protocol=p,url='http://localhost:8000/api/v1/health/ready',output=root/'evidence',dry_run=False,summarize_only=False,max_samples=1)
            def synthetic_collect(protocol,url,filename,rows,limit):
                rows.extend(self.samples())
                filename.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            with patch.object(m,'utc_now',return_value=m.timestamp('2026-01-02T00:00:30Z')), patch.object(m,'collect',side_effect=synthetic_collect),redirect_stdout(StringIO()):
                self.assertEqual(m.run(args),0)
            report=json.loads((args.output/'report.json').read_text())
            self.assertFalse(report['sampled_threshold_met']);self.assertTrue(report['limited_run'])
            self.assertFalse(report['story_complete'])
            args.max_samples=None;args.summarize_only=True
            with patch.object(m,'utc_now',return_value=m.timestamp('2026-01-02T00:00:30Z')), redirect_stdout(StringIO()):
                self.assertEqual(m.run(args),0)
            report=json.loads((args.output/'report.json').read_text())
            self.assertFalse(report['sampled_threshold_met'])
            self.assertTrue(report['tooling_or_interrupted_history'])


    def test_missing_past_samples_are_not_recreated_on_resume(self):
        from unittest.mock import patch
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            rows=[]
            with patch.object(m,'utc_now',return_value=m.timestamp('2026-01-02T00:00:30Z')), patch.object(m,'probe') as request:
                m.collect(self.protocol(),'http://localhost:8000/api/v1/health/ready',Path(directory)/'observations.jsonl',rows)
            request.assert_not_called()
            self.assertEqual(rows,[])
            self.assertEqual(self.report(rows=rows)['unknown_seconds'],20)

    def test_interruption_writes_incomplete_report_and_releases_lock(self):
        from argparse import Namespace
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        import tempfile,json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/'protocol.json';p.write_text(json.dumps(self.protocol()))
            args=Namespace(protocol=p,url='http://localhost:8000/api/v1/health/ready',output=root/'evidence',dry_run=False,summarize_only=False,max_samples=None)
            with patch.object(m,'utc_now',return_value=m.timestamp('2026-01-02T00:00:30Z')), patch.object(m,'collect',side_effect=KeyboardInterrupt()),redirect_stdout(StringIO()):
                self.assertEqual(m.run(args),130)
            report=json.loads((args.output/'report.json').read_text())
            self.assertTrue(report['interrupted']);self.assertFalse(report['sampled_threshold_met'])
            self.assertFalse((args.output/'collector.lock').exists())

    def test_real_cli_collection_and_readonly_summary_on_loopback(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from threading import Thread
        from datetime import timedelta
        import tempfile,json,subprocess,sys
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200);self.end_headers()
                self.wfile.write(b'{"status":"ready","checks":{"database":"ok"}}')
            def log_message(self,*args): pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        worker=Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);now=datetime.now(timezone.utc)
                protocol=self.protocol(start=m.iso(now+timedelta(seconds=.5)),end=m.iso(now+timedelta(seconds=2.5)),approved_at=m.iso(now-timedelta(seconds=30)),interval_seconds=1,timeout_seconds=.5)
                p=root/'protocol.json';p.write_text(json.dumps(protocol));out=root/'evidence'
                cmd=[sys.executable,str(path),'--protocol',str(p),'--url',f'http://127.0.0.1:{server.server_port}/api/v1/health/ready','--output',str(out)]
                result=subprocess.run(cmd+['--max-samples','1'],capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(len(m.read_observations(out/'observations.jsonl')),1)
                report=json.loads(result.stdout)
                self.assertFalse(report['story_complete']);self.assertFalse(report['sampled_threshold_met'])
                self.assertTrue(report['limited_run'])
                before=(out/'observations.jsonl').read_bytes()
                result=subprocess.run(cmd+['--summarize-only'],capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(before,(out/'observations.jsonl').read_bytes())
                self.assertFalse(json.loads(result.stdout)['story_complete'])
        finally:
            server.shutdown();worker.join();server.server_close()


if __name__ == '__main__':
    unittest.main()
