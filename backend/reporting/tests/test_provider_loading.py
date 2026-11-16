"""Actual provider loading: distinguish absent integration from broken installed code."""
from types import SimpleNamespace
from unittest.mock import patch

from django.db import DatabaseError
from django.test import SimpleTestCase

from reporting.exceptions import ReportingUnavailable
from reporting.providers import invoke


class ProviderLoadingTests(SimpleTestCase):
    def test_absent_provider_or_parent_is_redacted_unavailable(self):
        for missing in ('inventory', 'inventory.selectors', 'inventory.selectors.stock'):
            with self.subTest(missing=missing), patch(
                'reporting.providers.import_module',
                side_effect=ModuleNotFoundError('private filesystem detail', name=missing),
            ):
                with self.assertRaises(ReportingUnavailable) as error:
                    invoke('inventory.selectors.stock', 'stock_summary')
                self.assertNotIn('private', str(error.exception))

    def test_broken_internal_dependency_is_not_misreported_as_missing_provider(self):
        for failure in (
            ModuleNotFoundError(name='unrelated_library'),
            ImportError('cannot import expected symbol'),
            AttributeError('broken module initialization'),
            ModuleNotFoundError('missing dependency with no diagnostic name'),
        ):
            with self.subTest(failure=type(failure).__name__), patch(
                'reporting.providers.import_module', side_effect=failure,
            ):
                with self.assertRaises(type(failure)) as error:
                    invoke('inventory.selectors.stock', 'stock_summary')
                self.assertIs(error.exception, failure)

    def test_missing_or_non_callable_provider_is_unavailable(self):
        for module in (SimpleNamespace(), SimpleNamespace(stock_summary=None),
                       SimpleNamespace(stock_summary=23)):
            with self.subTest(module=module), patch(
                'reporting.providers.import_module', return_value=module,
            ):
                with self.assertRaises(ReportingUnavailable):
                    invoke('inventory.selectors.stock', 'stock_summary')

    def test_real_callable_receives_arguments_and_returns_its_result(self):
        captured = {}
        result = {'count': 0, 'results': []}

        def provider(**kwargs):
            captured.update(kwargs)
            return result

        with patch('reporting.providers.import_module',
                   return_value=SimpleNamespace(stock_summary=provider)):
            self.assertIs(invoke('inventory.selectors.stock', 'stock_summary',
                                 actor='trusted actor', filters={}, page=1), result)
        self.assertEqual(captured, {'actor': 'trusted actor', 'filters': {}, 'page': 1})

    def test_storage_error_is_redacted_but_provider_programming_error_propagates(self):
        def unavailable(**kwargs):
            raise DatabaseError('private database connection')

        with patch('reporting.providers.import_module',
                   return_value=SimpleNamespace(stock_summary=unavailable)):
            with self.assertRaises(ReportingUnavailable) as error:
                invoke('inventory.selectors.stock', 'stock_summary')
            self.assertNotIn('private', str(error.exception))

        def broken(**kwargs):
            raise TypeError('wrong implementation')

        with patch('reporting.providers.import_module',
                   return_value=SimpleNamespace(stock_summary=broken)):
            with self.assertRaises(TypeError):
                invoke('inventory.selectors.stock', 'stock_summary')
