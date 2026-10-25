class Headers:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' blob: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
