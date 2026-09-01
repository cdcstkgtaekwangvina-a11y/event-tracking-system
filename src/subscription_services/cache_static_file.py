from fastapi.staticfiles import StaticFiles


class CachedStaticFiles(StaticFiles):
    def __init__(self, *args, cache_control: str = "public, max-age=2592000", **kwargs):
        self.cache_control = cache_control
        super().__init__(*args, **kwargs)

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        if response.status_code == 200:
            response.headers["Cache-Control"] = self.cache_control
        return response
