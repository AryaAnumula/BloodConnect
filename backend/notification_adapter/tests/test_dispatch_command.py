from datetime import timedelta
from io import StringIO
import json
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from django.utils import timezone
from core.errors import DecisionRequired


class DispatchCommandTests(SimpleTestCase):
    def test_existing_one_shot_behavior_is_preserved(self):
        out = StringIO()
        with patch('notification_adapter.management.commands.dispatch_notifications.dispatch_due', return_value={'delivered': 1}) as dispatch, \
                patch('notification_adapter.management.commands.dispatch_notifications.time.sleep') as sleep:
            call_command('dispatch_notifications', stdout=out)
        self.assertEqual(json.loads(out.getvalue()), {'delivered': 1})
        self.assertEqual(dispatch.call_count, 1)
        sleep.assert_not_called()

    def test_bounded_watch_rereads_clock_and_dispatches_each_cycle(self):
        now = timezone.now()
        clocks = [now+timedelta(seconds=i) for i in range(3)]
        out = StringIO()
        with patch('notification_adapter.management.commands.dispatch_notifications.dispatch_due', return_value={'delivered': 0}) as dispatch, \
                patch('notification_adapter.management.commands.dispatch_notifications.time.monotonic', side_effect=[0, 0, 1, 1, 2, 2, 3]), \
                patch('notification_adapter.management.commands.dispatch_notifications.time.sleep') as sleep, \
                patch('notification_adapter.management.commands.dispatch_notifications.timezone.now', side_effect=clocks):
            call_command('dispatch_notifications', watch_seconds=3, interval_seconds=1, stdout=out)
        self.assertEqual([c.kwargs['now'] for c in dispatch.call_args_list], clocks)
        self.assertEqual(len(out.getvalue().splitlines()), 3)
        self.assertEqual(sleep.call_count, 3)

    def test_invalid_watch_configuration_is_rejected_before_dispatch(self):
        for options in ({'watch_seconds': -1}, {'watch_seconds': 3601}, {'interval_seconds': 0}, {'limit': 0}):
            with patch('notification_adapter.management.commands.dispatch_notifications.dispatch_due') as dispatch:
                with self.assertRaises(CommandError):
                    call_command('dispatch_notifications', **options)
                dispatch.assert_not_called()

    def test_unapproved_policy_fails_before_sleep_or_fake_success(self):
        out = StringIO()
        with patch('notification_adapter.management.commands.dispatch_notifications.dispatch_due', side_effect=DecisionRequired('policy')), \
                patch('notification_adapter.management.commands.dispatch_notifications.time.sleep') as sleep:
            with self.assertRaises(CommandError):
                call_command('dispatch_notifications', watch_seconds=2, stdout=out)
        sleep.assert_not_called()
        self.assertEqual(out.getvalue(), '')
