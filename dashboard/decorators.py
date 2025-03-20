from functools import wraps
from django.shortcuts import render
from django.http import HttpResponseServerError
from urllib3.exceptions import MaxRetryError

def server_down_handler(view_func):
    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except MaxRetryError as e:
            # logger.error(e)
            return HttpResponseServerError(render(request, 'cluster_error.html'))

    return _wrapped_view_func
