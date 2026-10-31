from django.conf import settings
from rest_framework.renderers import JSONRenderer


def absolutize_media(data, base_url):
    if isinstance(data, dict):
        return {key: absolutize_media(value, base_url) for key, value in data.items()}
    if isinstance(data, list):
        return [absolutize_media(value, base_url) for value in data]
    if isinstance(data, str) and data.startswith(settings.MEDIA_URL):
        return base_url + data
    return data


class MediaURLJSONRenderer(JSONRenderer):
    """Turns /media/... paths into full URLs on the Next site, which rewrites them to Django."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        request = (renderer_context or {}).get("request")
        if request is not None:
            base_url = settings.PUBLIC_BASE_URL or request.build_absolute_uri("/").rstrip("/")
            data = absolutize_media(data, base_url)
        return super().render(data, accepted_media_type, renderer_context)
