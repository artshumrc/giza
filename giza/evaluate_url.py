from django.shortcuts import render, redirect

class Evaluate_URL:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        # return self.get_response(request)
        p = f'{request.scheme}://{request.get_host()}/'
        if 'admin' in request.get_full_path():
            return self.get_response(request)
        elif request.get_full_path() is '/' or request.META.get('HTTP_REFERER') == p:

            response = self.get_response(request)

            # Code to be executed for each request/response after
            # the view is called.

            return response
        else:
            return redirect(p)
            # return render(request, '404.html')