import json
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from core.errors import DecisionRequired
from notification_adapter.services.dispatch import dispatch_due

class Command(BaseCommand):
    help='Dispatch durable due notification intents to the private mock service. No real SMS/email.'
    def add_arguments(self,parser):parser.add_argument('--limit',type=int,default=100)
    def handle(self,*args,**options):
        try:result=dispatch_due(now=timezone.now(),limit=options['limit'])
        except (DecisionRequired,ValueError,RuntimeError) as exc:raise CommandError(str(exc)) from None
        self.stdout.write(json.dumps(result,sort_keys=True))
