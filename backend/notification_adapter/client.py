"""Existing public Python→Node boundary; dedicated token, bounded private HTTP, no browser auth."""
import os,uuid
from urllib.parse import urlsplit
import requests
from django.conf import settings

class NotificationTransportUnavailable(Exception): pass

def send_notification_intent(*, event: dict) -> dict:
    base=getattr(settings,'NOTIFICATION_BASE_URL',os.environ.get('NOTIFICATION_BASE_URL','http://notifications:3000')).rstrip('/')
    token=getattr(settings,'NOTIFICATION_INTERNAL_TOKEN',os.environ.get('NOTIFICATION_INTERNAL_TOKEN',''))
    try:
        url=urlsplit(base)
        if url.scheme not in {'http','https'} or url.username or url.password or url.query or url.fragment or url.path not in ('','/') or not url.hostname: raise ValueError()
        if url.scheme=='http' and url.hostname not in {'notifications','127.0.0.1','localhost','::1'}: raise ValueError()
        if len(token)<32 or token.startswith('CHANGE_ME'): raise ValueError()
    except (ValueError,TypeError): raise NotificationTransportUnavailable('Notification transport is not configured.') from None
    try:
        response=requests.post(base+'/internal/notifications',json=event,headers={'Authorization':'Bearer '+token},timeout=(2,3),allow_redirects=False)
        if response.status_code!=202: raise ValueError()
        data=response.json()
        if set(data)!={'event_id','delivery_mode','receipts'} or uuid.UUID(data['event_id'])!=uuid.UUID(str(event['event_id'])) or data['delivery_mode']!='mock': raise ValueError()
        receipts=data['receipts']
        if not isinstance(receipts,list) or len(receipts)!=len(event['channels']): raise ValueError()
        if any(set(x)!={'channel','status'} or x['status']!='DELIVERED' for x in receipts): raise ValueError()
        if sorted(x['channel'] for x in receipts)!=sorted(event['channels']): raise ValueError()
        return data
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
        raise NotificationTransportUnavailable('Mock notification receipt unavailable.') from None
