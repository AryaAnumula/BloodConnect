import json
import time
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from core.errors import DecisionRequired
from notification_adapter.services.dispatch import dispatch_due

class Command(BaseCommand):
    help='Dispatch durable due notification intents to the private mock service. No real SMS/email.'
    def add_arguments(self,parser):
        parser.add_argument('--limit',type=int,default=100)
        parser.add_argument('--watch-seconds',type=int,default=0,help='Bounded repeated dispatch;0 keeps existing one-shot behavior.')
        parser.add_argument('--interval-seconds',type=int,default=60,help='Polling interval during a bounded watch.')
    def handle(self,*args,**options):
        duration, interval, limit = options['watch_seconds'], options['interval_seconds'], options['limit']
        if (type(duration) is not int or not 0 <= duration <= 3600
                or type(interval) is not int or not 1 <= interval <= 3600
                or type(limit) is not int or not 1 <= limit <= 1000):
            raise CommandError('Use watch0..3600, interval1..3600 and limit1..1000 whole numbers.')
        deadline = time.monotonic() + duration
        while True:
            try:result=dispatch_due(now=timezone.now(),limit=limit)
            except (DecisionRequired,ValueError,RuntimeError) as exc:raise CommandError(str(exc)) from None
            self.stdout.write(json.dumps(result,sort_keys=True))
            if duration == 0:
                return
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(interval, remaining))
            if time.monotonic() >= deadline:
                return
