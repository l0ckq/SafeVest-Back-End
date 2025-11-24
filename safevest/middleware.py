# safevest/middleware.py
class DebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'usuarios' in request.path:
            print("🔵" * 25)
            print(f"🔵 PATH: {request.path}")
            print(f"🔵 METHOD: {request.method}")
            print(f"🔵 PATH_INFO: {request.META.get('PATH_INFO')}")
            print("🔵" * 25)
        
        response = self.get_response(request)
        return response