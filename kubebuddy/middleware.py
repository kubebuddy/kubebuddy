import re
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from urllib3.exceptions import MaxRetryError

class MaxRetryRedirectMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, MaxRetryError):
            # Extract cluster_name from the request path
            match = re.match(r'^/([^/]+)/', request.path)
            if match:
                cluster_name = match.group(1)
                return redirect('cluster_error', cluster_name=cluster_name)
            
            # If no cluster_name found, redirect to a default error page
            return redirect('/error-page/')  # Change this to a valid error route
