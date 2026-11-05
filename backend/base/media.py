from django.views.static import serve

# A file from /media/ opened on its own is a document of our origin. With this policy an SVG
# can't run scripts or load anything even if the sanitiser missed something (base/svg.py).
MEDIA_POLICY = "default-src 'none'; style-src 'unsafe-inline'; sandbox"


def serve_media(request, path, document_root=None):
    response = serve(request, path, document_root=document_root)
    response["Content-Security-Policy"] = MEDIA_POLICY
    response["X-Content-Type-Options"] = "nosniff"
    return response
