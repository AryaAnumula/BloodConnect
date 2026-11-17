"""Verify that the application URL configuration exposes inventory routes."""
from django.test import SimpleTestCase
from django.urls import resolve


class InventoryRouteWiringTests(SimpleTestCase):
    def test_inventory_api_and_staff_page_are_mounted(self):
        self.assertEqual(resolve('/api/v1/blood-units').view_name, 'inventory:blood-unit-intake')
        self.assertEqual(resolve('/staff/inventory').view_name, 'inventory-pages:stock')

    def test_existing_request_and_report_routes_remain_mounted(self):
        self.assertEqual(resolve('/requests').view_name, 'request-tracking-page')
        self.assertEqual(resolve('/api/v1/reports').view_name, 'reporting-activity:reports')
