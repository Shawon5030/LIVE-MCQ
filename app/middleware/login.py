from django.http import HttpResponse

class ForLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.method =='POST' and request.user.is_superuser:
            print("Hello, world!")
