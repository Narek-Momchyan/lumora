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
    "invalid_bet",
    "too_many_lines",
    "round_limit_exceeded",
]

SPORTS_CODES = [
    "odds_changed",
    "market_closed",
    "same_match_twice",
    "too_many_selections",
    "stake_too_low",
    "stake_too_high",
    "odds_too_high",
    "win_too_high",
    "prediction_locked",
    "prediction_invalid",
    "match_not_found",
]

FORUM_CODES = [
    "forum_banned",
    "display_name_required",
    "display_name_invalid",
    "post_empty",
    "post_too_long",
    "title_invalid",
    "post_has_link",
    "post_banned_word",
    "post_too_fast",
    "too_many_topics",
    "topic_locked",
    "post_hidden",
    "already_reported",
    "own_post_report",
    "forum_not_found",
    "topic_not_found",
    "post_not_found",
    "invalid_tag",
    "invalid_report_reason",
    "invalid_match",
    "no_prediction",
]

FIELD_CODES = [
    "email_taken",
    "display_name_has_at",
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

ERROR_CODES = AUTH_CODES + GAME_CODES + SPORTS_CODES + FORUM_CODES + FIELD_CODES + REQUEST_CODES
