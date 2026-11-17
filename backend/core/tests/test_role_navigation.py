from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve


class RoleNavigationTests(SimpleTestCase):
    def render(self, role=None, authenticated=True, **kwargs):
        request = RequestFactory().get('/')
        request.user = SimpleNamespace(is_authenticated=authenticated, is_active=kwargs.get('active', True),
                                       is_superuser=kwargs.get('superuser', False), role=role,
                                       email='synthetic@example.test')
        return render_to_string('base.html', request=request)

    def test_each_role_gets_its_own_working_links(self):
        expected = {
            'ADMIN': ['/dashboard', '/reports', '/camps', '/staff/inventory'],
            'STAFF': ['/staff/requests', '/staff/inventory', '/staff/inventory/alerts', '/camps', '/staff/donors', '/screening'],
            'REQUESTER': ['/requests/new', '/requests'],
            'DONOR': ['/screening', '/eligibility', '/camps', '/appointments'],
        }
        for role, links in expected.items():
            with self.subTest(role=role):
                page = self.render(role)
                for link in links:
                    self.assertIn(f'href="{link}"', page)
                    self.assertIsNotNone(resolve(link))
                self.assertIn('id="session-logout"', page)
                self.assertNotIn('College demonstration:', page)
                if role != 'ADMIN': self.assertNotIn('href="/reports"', page)
                if role != 'STAFF': self.assertNotIn('href="/staff/inventory/alerts"', page)

    def test_anonymous_and_inactive_users_do_not_get_operational_links(self):
        for user in (dict(authenticated=False), dict(role='ADMIN', active=False), dict(role='ADMIN', superuser=True)):
            with self.subTest(user=user):
                page = self.render(**user)
                self.assertIn('href="/login"', page)
                self.assertNotIn('href="/dashboard"', page)

    def test_inventory_templates_share_sidebar_and_keep_forms(self):
        request = RequestFactory().get('/staff/inventory')
        request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=False,
                                       role='STAFF', email='staff@example.test')
        for name, marker in [('stock', 'id="refresh"'), ('intake', 'id="intake"'), ('alerts', 'id="rows"')]:
            with self.subTest(page=name):
                html = render_to_string(f'inventory/{name}.html', {'can_manage_inventory': True}, request=request)
                self.assertIn('href="/staff/requests"', html)
                self.assertIn(marker, html)
