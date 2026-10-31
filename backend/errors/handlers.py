import re

from django.contrib.auth.password_validation import MinimumLengthValidator, get_default_password_validators
from rest_framework.exceptions import ErrorDetail
from rest_framework.views import exception_handler as drf_exception_handler

from base.constants import DEFAULT_LANG
from base.language import get_lang
from .models import ErrorMessage

VALIDATION_ERROR = "validation_error"
CODE_ALIASES = {"no_active_account": "invalid_credentials"}


def fill(text, params):
    """Replaces {name}. Unknown placeholders stay as they are, so a typo in the admin can't break a response."""
    return re.sub(r"\{(\w+)\}", lambda match: str(params.get(match[1], match[0])), text)


def translate(code, lang, default, **params):
    """Text in `lang`, else in English, else `default`, the text written in the code."""
    texts = dict(ErrorMessage.objects.filter(code=code, lang__in=[lang, DEFAULT_LANG]).values_list("lang", "text"))
    return fill(texts.get(lang) or texts.get(DEFAULT_LANG) or default, params)


def coded_body(request, code, default, **params):
    return {"code": code, "detail": translate(code, get_lang(request), default, **params)}


def validator_params(code):
    if code != "password_too_short":
        return {}
    for validator in get_default_password_validators():
        if isinstance(validator, MinimumLengthValidator):
            return {"min_length": validator.min_length}
    return {}


def validation_body(errors, request):
    """{"email": [ErrorDetail]} -> translated texts, plus their codes in `field_codes`."""
    lang = get_lang(request)
    body = coded_body(request, VALIDATION_ERROR, "Check the fields.")
    body["field_codes"] = {}
    for field, details in errors.items():
        if not isinstance(details, list):
            body[field] = details
            continue
        details = [detail for detail in details if isinstance(detail, ErrorDetail)]
        body[field] = [
            translate(detail.code, lang, str(detail), **validator_params(detail.code)) for detail in details
        ]
        body["field_codes"][field] = [detail.code for detail in details]
    return body


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None  # a real bug: Django answers 500

    request = context["request"]
    data = response.data
    if isinstance(data, list):
        data = {"non_field_errors": data}

    detail = data.get("detail")
    if isinstance(detail, ErrorDetail):
        code = CODE_ALIASES.get(detail.code, detail.code)
        response.data = {
            **coded_body(request, code, str(detail), **getattr(exc, "params", {})),
            **getattr(exc, "extra", {}),
        }
    else:
        response.data = validation_body(data, request)
    return response
