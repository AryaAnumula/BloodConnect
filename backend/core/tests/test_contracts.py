"""Verify starter route wiring and real infrastructure responses against the contract."""
from pathlib import Path
from django.conf import settings
from django.urls import resolve
from rest_framework.test import APITestCase
from jsonschema import Draft4Validator
import yaml

class StarterContractTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = yaml.safe_load((Path(settings.BASE_DIR) / 'docs/api/openapi.yaml').read_text())

    def validate_response(self, path, method, response):
        content = self.spec['paths'][path][method]['responses'][str(response.status_code)]['content']['application/json']['schema']
        root_schema = dict(content)
        root_schema['components'] = self.spec['components']
        Draft4Validator(root_schema).validate(response.json())

    def test_every_documented_route_and_method_is_wired(self):
        for path, methods in self.spec['paths'].items():
            concrete = path.replace('{donor_id}', '00000000-0000-4000-8000-000000000001')
            match = resolve(concrete)
            view_class = getattr(match.func, 'cls', None) or getattr(match.func, 'view_class', None)
            for method in methods:
                self.assertTrue(hasattr(view_class, method), f'{method.upper()} {path} is not wired')

    def test_real_health_csrf_and_error_responses_match_schemas(self):
        for path, method in [('/api/v1/health/live', 'get'), ('/api/v1/health/ready', 'get'), ('/api/v1/auth/csrf', 'get'), ('/api/v1/donors', 'get'), ('/api/v1/auth/login', 'post')]:
            response = getattr(self.client, method)(path, {}, format='json')
            self.validate_response(path, method, response)
