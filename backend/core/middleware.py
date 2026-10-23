import uuid
class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        # Do not trust arbitrary client-controlled log metadata.
        try:
            request.request_id = str(uuid.UUID(request.headers.get('X-Request-ID', '')))
        except (ValueError, TypeError, AttributeError):
            request.request_id = str(uuid.uuid4())
        response = self.get_response(request)
        response['X-Request-ID'] = request.request_id
        return response
