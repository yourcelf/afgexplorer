from django.utils.cache import patch_response_headers

class ExpiresHeader(object):
    """ 
    Sets the Expires, ETag, and Last-Modified headers for every HTTP request.
    Expires is set to now + CACHE_MIDDLEWARE_SECONDS.
    """
    def process_response(self, request, response):
        patch_response_headers(response)
        return response
