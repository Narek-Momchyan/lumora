from .constants import DEFAULT_LANG, LANG_CHOICES

LANG_CODES = [code for code, _ in LANG_CHOICES]


def get_lang(request):
    """The request's language: ?lang= -> lang cookie -> English. Always a supported code."""
    lang = request.GET.get("lang") or request.COOKIES.get("lang")
    return lang if lang in LANG_CODES else DEFAULT_LANG
