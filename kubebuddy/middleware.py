import re
from django.shortcuts import redirect, render
from django.utils.deprecation import MiddlewareMixin
from urllib3.exceptions import MaxRetryError
import logging
logger = logging.getLogger(__name__)

class MaxRetryRedirectMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, MaxRetryError):
            # Extract cluster_name from the request path
            match = re.match(r'^/([^/]+)/', request.path)
            if match:
                cluster_name = match.group(1)
                return redirect('cluster_error', cluster_name=cluster_name)
            
            # If no cluster_name found, redirect to a default error page
            return

class CustomExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        logger.exception("An error occurred: %s", str(exception))
        # Handle all exceptions
        context = {
            'error': str(exception)
        }
        return render(request, 'error.html', context)
        