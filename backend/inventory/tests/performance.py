"""Explicit S2-09 demo load run, not part of automatic test discovery.

Run this module deliberately with PostgreSQL16, INVENTORY_EVIDENCE_SOURCE_SHA
and INVENTORY_PERFORMANCE_OUTPUT set. Fixtures do not claim intake acceptance.
"""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import ctypes
import json
import math
import os
from pathlib import Path
import platform
import re
import secrets
from threading import Barrier
import time

import django
import requests
from django.contrib.auth import get_user_model
from django.db import connection, connections, transaction
from django.test import LiveServerTestCase, override_settings
from django.utils import timezone

from core.input_schemas import BLOOD_GROUPS
from donors.models import DonorProfile
from inventory.configuration import shelf_life_policy
from inventory.models import BloodUnit, CollectionEvent


def p95(values):
    return sorted(values)[math.ceil(len(values)*.95)-1] if values else None


def hardware():
    result = {'platform':platform.platform(),'machine':platform.machine(),
              'processor':platform.processor(),'logical_cpu_count':os.cpu_count()}
    if os.name == 'nt':
        class Memory(ctypes.Structure):
            _fields_ = [('length',ctypes.c_ulong),('load',ctypes.c_ulong)] + [
                (name,ctypes.c_ulonglong) for name in ('total_physical','available_physical',
                'total_pagefile','available_pagefile','total_virtual','available_virtual','extended')]
        value = Memory()
        value.length = ctypes.sizeof(value)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
            result['physical_memory_bytes'] = value.total_physical
    return result


@override_settings(ROOT_URLCONF='inventory.tests.urls',SESSION_COOKIE_SECURE=False,
                   CSRF_COOKIE_SECURE=False)
class InventoryLoadEvidence(LiveServerTestCase):
    """500 donors/500 units; five session clients;10s warm-up,60s measured."""

    def test_approved_demo_read_load(self):
        source = os.environ.get('INVENTORY_EVIDENCE_SOURCE_SHA','')
        output = os.environ.get('INVENTORY_PERFORMANCE_OUTPUT','')
        self.assertRegex(source,r'^[0-9a-f]{40}$')
        self.assertTrue(output,'Set INVENTORY_PERFORMANCE_OUTPUT explicitly.')
        self.assertEqual(connection.vendor,'postgresql')
        with connection.cursor() as cursor:
            cursor.execute('SELECT version(), current_setting(\'server_version_num\')')
            version, numeric = cursor.fetchone()
        self.assertEqual(int(numeric)//10000,16,'This acceptance run requires PostgreSQL16.')
        password = secrets.token_urlsafe(24)
        users = [get_user_model().objects.create_user(email=f'load-staff-{i}@inventory.test',
            role='STAFF',password=password) for i in range(5)]
        collected = timezone.localdate()-timedelta(days=1)
        components = tuple(BloodUnit.Component.values)
        policy = shelf_life_policy()
        with transaction.atomic():
            accounts = [get_user_model()(email=f'load-donor-{i}@inventory.test',role='DONOR',
                password='!') for i in range(500)]
            get_user_model().objects.bulk_create(accounts)
            donors = [DonorProfile(user=account,full_name=f'Synthetic load donor {i}',
                mobile=f'+9190{i:08d}',blood_group=BLOOD_GROUPS[i%8],location='Synthetic load',
                last_confirmed_collection_date=collected) for i,account in enumerate(accounts)]
            DonorProfile.objects.bulk_create(donors)
            events = [CollectionEvent(donor=donor,collection_date=collected,
                blood_group=donor.blood_group,recorded_by=users[0]) for donor in donors]
            CollectionEvent.objects.bulk_create(events)
            BloodUnit.objects.bulk_create([BloodUnit(unit_code=f'LOAD-{i:05d}',donor=donor,
                collection_event=event,blood_group=donor.blood_group,
                component_type=components[(i//8)%4],collection_date=collected,
                expiry_date=collected+timedelta(days=policy[components[(i//8)%4]]))
                for i,(donor,event) in enumerate(zip(donors,events))])
        self.assertEqual(DonorProfile.objects.count(),500)
        self.assertEqual(BloodUnit.objects.count(),500)
        sessions = []
        for user in users:
            session = requests.Session()
            session.trust_env = False
            bootstrap = session.get(self.live_server_url+'/api/v1/auth/csrf',timeout=10)
            bootstrap.raise_for_status()
            response = session.post(self.live_server_url+'/api/v1/auth/login',
                json={'email':user.email,'password':password},
                headers={'X-CSRFToken':bootstrap.json()['csrf_token']},timeout=10)
            self.assertEqual(response.status_code,200)
            sessions.append(session)
        connections.close_all()
        measured = {}
        barrier = Barrier(5,action=lambda:measured.update(start=time.perf_counter()))
        started_at = timezone.now().isoformat()

        def request(session,index):
            endpoint = 'units' if index%5==4 else 'stock'
            path = ('/api/v1/blood-units?page='+str((index//5)%25+1)
                    if endpoint=='units' else '/api/v1/stock?page_size=100')
            start = time.perf_counter()
            status, error = None, None
            try:
                response = session.get(self.live_server_url+path,timeout=(3,10))
                elapsed = time.perf_counter()-start
                status = response.status_code
                if status!=200:
                    error='http_status'
                else:
                    data = response.json()
                    if (data['count'] != (500 if endpoint=='units' else 32)
                            or (endpoint=='stock' and sum(r['available_quantity'] for r in data['results'])!=500)):
                        error='source_reconciliation'
            except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
                elapsed = time.perf_counter()-start
                error=type(exc).__name__
            return {'endpoint':endpoint,'seconds':elapsed,'status':status,'error':error}

        def worker(session):
            index=0
            try:
                warmup_end=time.perf_counter()+10
                while time.perf_counter()<warmup_end:
                    sample=request(session,index)
                    if sample['error']:
                        raise AssertionError('Warm-up failed: '+sample['error'])
                    index+=1
                barrier.wait(timeout=30)
                samples=[]
                while time.perf_counter()<measured['start']+60:
                    samples.append(request(session,index))
                    index+=1
                return samples
            except Exception:
                barrier.abort()
                raise
            finally:
                session.close()

        with ThreadPoolExecutor(max_workers=5) as executor:
            groups=list(executor.map(worker,sessions))
        samples=[sample for group in groups for sample in group]
        elapsed=time.perf_counter()-measured['start']
        errors=[sample for sample in samples if sample['error']]
        durations=[sample['seconds'] for sample in samples]
        by_endpoint=defaultdict(list)
        for sample in samples:
            by_endpoint[sample['endpoint']].append(sample['seconds'])
        result={'source_sha':source,'database':version,'server_version_num':int(numeric),
            'python':platform.python_version(),'django':django.get_version(),'hardware':hardware(),
            'dataset':{'donors':500,'units':500,'events':500,'kind':'isolated synthetic ORM load fixture, not intake proof'},
            'protocol':'scoped S2-09, shared-rules v1.1,15Nov2026; no SRS rewrite',
            'clients':5,'warmup_seconds':10,'measurement_seconds':60,'actual_finish_seconds':elapsed,
            'started_at':started_at,'finished_at':timezone.now().isoformat(),
            'server':'Django LiveServerTestCase WSGI, localhost HTTP; test-only inventory route composition',
            'endpoint_mix':dict(Counter(sample['endpoint'] for sample in samples)),
            'sample_count':len(samples),'error_count':len(errors),'errors':errors,
            'p95_seconds':p95(durations),'max_seconds':max(durations),
            'under_2s_fraction':sum(value<=2 for value in durations)/len(durations),
            'endpoint_p95_seconds':{key:p95(values) for key,values in by_endpoint.items()},
            'all_samples':samples}
        target=Path(output)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({key:value for key,value in result.items() if key not in ('all_samples','hardware')},indent=2))
        self.assertEqual(len(errors),0)
        self.assertLessEqual(result['p95_seconds'],2)
