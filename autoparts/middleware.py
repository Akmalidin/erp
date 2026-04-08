"""
Middleware to prevent browser caching of dynamic pages.
Static files are excluded (they have their own cache headers via whitenoise).
"""


class NoCacheMiddleware:
    """Add Cache-Control: no-cache, no-store to all non-static responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Only apply to HTML/JSON responses, not static files or media
        if not request.path.startswith(('/static/', '/media/')):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
