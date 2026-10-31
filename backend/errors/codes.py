"""Every error code the API can answer with. Each one has a text in every language in the sample."""

AUTH_CODES = [
    "invalid_credentials",
    "authentication_failed",
    "not_authenticated",
    "session_expired",
    "permission_denied",
    "csrf_failed",
]

GAME_CODES = [
    "not_enough_lc",
    "bonus_already_claimed",
    "bet_out_of_range",
    "target_out_of_range",
    "game_unavailable",
    "game_not_found",
    "round_closed",
    "already_bet",
    "too_late",
    "not_flying",
    "no_bet",
    "already_cashed_out",
]

FIELD_CODES = [
    "email_taken",
    "required",
    "blank",
    "null",
    "invalid",
    "max_length",
    "max_digits",
    "max_decimal_places",
    "max_whole_digits",
    "password_too_short",
    "password_too_common",
    "password_entirely_numeric",
    "password_too_similar",
]

REQUEST_CODES = [
    "validation_error",
    "not_found",
    "method_not_allowed",
    "parse_error",
    "unsupported_media_type",
    "not_acceptable",
    "throttled",
]

ERROR_CODES = AUTH_CODES + GAME_CODES + FIELD_CODES + REQUEST_CODES
