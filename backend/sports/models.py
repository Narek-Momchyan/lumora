from django.conf import settings
from django.db import models

from base.constants import LANG_CHOICES
from base.fields import IMAGE_OR_SVG_VALIDATORS


class SportsPageLabel(models.Model):
    """Every text of the football home page in one language.

    Until the football pages arrive (phase S3), the page shows only this hero.
    """

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    page_title = models.CharField(max_length=100)
    page_description = models.CharField(max_length=255)
    hero_eyebrow = models.CharField(max_length=100)
    hero_title = models.CharField(max_length=150)
    hero_text = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Sports page labels"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["lang"], name="unique_sports_page_label_lang"),
        ]

    def __str__(self):
        return f"Sports page labels ({self.lang})"


class Competition(models.Model):
    """One of our leagues. A league shows a country flag (a star for the Champions League), never a logo."""

    code = models.CharField(max_length=10, help_text="football-data.org code: PL, PD, SA, BL1, FL1, CL")
    provider_id = models.PositiveIntegerField(null=True, blank=True, editable=False)
    name = models.CharField(max_length=100, help_text="English name from the provider")
    flag = models.FileField(
        upload_to="images/sports/flags/", max_length=255, blank=True, validators=IMAGE_OR_SVG_VALIDATORS
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, help_text="Off: the sync skips it and the site hides it")

    class Meta:
        verbose_name_plural = "Competitions"
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["code"], name="unique_competition_code")]

    def __str__(self):
        return self.name


class CompetitionName(models.Model):
    """The competition's name in another language; without one the English name is shown."""

    competition = models.ForeignKey(Competition, related_name="names", on_delete=models.CASCADE)
    lang = models.CharField(max_length=10, choices=LANG_CHOICES)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Competition names"
        ordering = ["competition", "lang"]
        constraints = [
            models.UniqueConstraint(fields=["competition", "lang"], name="unique_competition_name_lang"),
        ]

    def __str__(self):
        return f"{self.name} ({self.lang})"


class Season(models.Model):
    competition = models.ForeignKey(Competition, related_name="seasons", on_delete=models.CASCADE)
    provider_id = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    current_matchday = models.PositiveSmallIntegerField(null=True, blank=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Seasons"
        ordering = ["competition", "-start_date"]
        constraints = [models.UniqueConstraint(fields=["provider_id"], name="unique_season_provider_id")]

    def __str__(self):
        return f"{self.competition.code} {self.start_date.year}/{self.end_date.year}"


class Team(models.Model):
    """A club from the provider. Its colours and crest can be changed in the admin."""

    provider_id = models.PositiveIntegerField(editable=False)
    name = models.CharField(max_length=100, help_text="English name from the provider")
    short_name = models.CharField(max_length=60, blank=True)
    tla = models.CharField(
        "short code", max_length=5, blank=True, help_text="Shown on the initials badge: ARS, BAY ..."
    )
    color = models.CharField(max_length=7, default="#1b3a27", help_text="Badge colour, hex")
    text_color = models.CharField(max_length=7, default="#ffffff", help_text="Initials colour on the badge, hex")
    crest = models.FileField(
        upload_to="images/sports/crests/", max_length=255, blank=True, validators=IMAGE_OR_SVG_VALIDATORS
    )
    crest_source_url = models.URLField(max_length=255, blank=True, editable=False)
    crest_locked = models.BooleanField(default=False, help_text="On: the sync never replaces this crest")
    competitions = models.ManyToManyField(Competition, related_name="teams", blank=True)

    class Meta:
        verbose_name_plural = "Teams"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["provider_id"], name="unique_team_provider_id")]

    def __str__(self):
        return self.name


class TeamName(models.Model):
    """The club's name in another language; without one the provider's English name is shown."""

    team = models.ForeignKey(Team, related_name="names", on_delete=models.CASCADE)
    lang = models.CharField(max_length=10, choices=LANG_CHOICES)
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=60, blank=True)

    class Meta:
        verbose_name_plural = "Team names"
        ordering = ["team", "lang"]
        constraints = [models.UniqueConstraint(fields=["team", "lang"], name="unique_team_name_lang")]

    def __str__(self):
        return f"{self.name} ({self.lang})"


class TeamAlias(models.Model):
    """Another provider's name for the club (API-Football in S5), to match the same team."""

    team = models.ForeignKey(Team, related_name="aliases", on_delete=models.CASCADE)
    provider = models.CharField(max_length=30)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Team aliases"
        ordering = ["provider", "name"]
        constraints = [
            models.UniqueConstraint(fields=["provider", "name"], name="unique_team_alias_provider_name"),
        ]

    def __str__(self):
        return f"{self.name} ({self.provider})"


class Match(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        LIVE = "live", "Live"
        PAUSED = "paused", "Half time"
        FINISHED = "finished", "Finished"
        POSTPONED = "postponed", "Postponed"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"
        AWARDED = "awarded", "Awarded"

    provider_id = models.PositiveIntegerField()
    competition = models.ForeignKey(Competition, related_name="matches", on_delete=models.CASCADE)
    season = models.ForeignKey(Season, related_name="matches", on_delete=models.CASCADE)
    matchday = models.PositiveSmallIntegerField(null=True, blank=True)
    stage = models.CharField(max_length=40, blank=True)
    group = models.CharField(max_length=40, blank=True)
    home = models.ForeignKey(Team, related_name="home_matches", on_delete=models.PROTECT)
    away = models.ForeignKey(Team, related_name="away_matches", on_delete=models.PROTECT)
    kickoff = models.DateTimeField(db_index=True, help_text="UTC")
    status = models.CharField(max_length=12, choices=Status.choices, db_index=True)
    provider_status = models.CharField(max_length=20)
    duration = models.CharField(max_length=20, blank=True, help_text="REGULAR, EXTRA_TIME or PENALTY_SHOOTOUT")
    # The full-time score includes extra time. Bets are settled on the regular-time score
    # (90 minutes + stoppage), kept apart for the knockout matches that go further.
    home_score = models.PositiveSmallIntegerField(null=True, blank=True)
    away_score = models.PositiveSmallIntegerField(null=True, blank=True)
    home_half = models.PositiveSmallIntegerField(null=True, blank=True)
    away_half = models.PositiveSmallIntegerField(null=True, blank=True)
    home_regular = models.PositiveSmallIntegerField(null=True, blank=True)
    away_regular = models.PositiveSmallIntegerField(null=True, blank=True)
    home_extra = models.PositiveSmallIntegerField(null=True, blank=True)
    away_extra = models.PositiveSmallIntegerField(null=True, blank=True)
    home_penalties = models.PositiveSmallIntegerField(null=True, blank=True)
    away_penalties = models.PositiveSmallIntegerField(null=True, blank=True)
    provider_updated = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Matches"
        ordering = ["kickoff", "id"]
        constraints = [models.UniqueConstraint(fields=["provider_id"], name="unique_match_provider_id")]

    def __str__(self):
        return f"{self.home} – {self.away} ({self.kickoff:%Y-%m-%d})"


class Standing(models.Model):
    season = models.ForeignKey(Season, related_name="standings", on_delete=models.CASCADE)
    stage = models.CharField(max_length=40, blank=True)
    group = models.CharField(max_length=40, blank=True)
    type = models.CharField(max_length=10, default="TOTAL")
    team = models.ForeignKey(Team, related_name="standings", on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()
    played = models.PositiveSmallIntegerField(default=0)
    won = models.PositiveSmallIntegerField(default=0)
    draw = models.PositiveSmallIntegerField(default=0)
    lost = models.PositiveSmallIntegerField(default=0)
    goals_for = models.PositiveSmallIntegerField(default=0)
    goals_against = models.PositiveSmallIntegerField(default=0)
    goal_difference = models.SmallIntegerField(default=0)
    points = models.PositiveSmallIntegerField(default=0)
    form = models.CharField(max_length=20, blank=True, help_text="W, D, L of the last matches")

    class Meta:
        verbose_name_plural = "Standings"
        ordering = ["season", "stage", "group", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["season", "stage", "group", "type", "team"], name="unique_standing_season_table_team"
            ),
        ]

    def __str__(self):
        return f"{self.position}. {self.team}"


class SyncRun(models.Model):
    """One run of the football sync: what it asked the provider and what it changed."""

    class Kind(models.TextChoices):
        FULL = "full", "Full season"
        TODAY = "today", "Today's matches"

    kind = models.CharField(max_length=10, choices=Kind.choices)
    competition = models.ForeignKey(Competition, null=True, blank=True, on_delete=models.SET_NULL)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    requests = models.PositiveIntegerField(default=0)
    created = models.PositiveIntegerField(default=0)
    updated = models.PositiveIntegerField(default=0)
    errors = models.TextField(blank=True)
    ok = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Sync runs"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.kind} {self.started_at:%Y-%m-%d %H:%M}"


class ModelRun(models.Model):
    """One fit of the odds model (sports/engine.py): when, on how many matches, and its ratings."""

    fitted_at = models.DateTimeField(auto_now_add=True)
    matches_used = models.PositiveIntegerField()
    rho = models.FloatField()
    params = models.JSONField(help_text="base and home per competition, attack and defence per team id")
    priced_matches = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Model runs"
        ordering = ["-fitted_at"]

    def __str__(self):
        return f"Model {self.fitted_at:%Y-%m-%d %H:%M} ({self.matches_used} matches)"


class Market(models.Model):
    """A match's market. Its odds follow the model until kickoff, then they are frozen."""

    class Kind(models.TextChoices):
        ONE_X_TWO = "1x2", "Match result"
        DOUBLE_CHANCE = "double_chance", "Double chance"
        TOTAL = "total", "Total goals"
        BTTS = "btts", "Both teams to score"
        CORRECT_SCORE = "correct_score", "Correct score"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed at kickoff"
        SETTLED = "settled", "Settled"
        VOID = "void", "Void"

    match = models.ForeignKey(Match, related_name="markets", on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    line = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="Total goals only")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Markets"
        ordering = ["match", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["match", "kind", "line"], nulls_distinct=False, name="unique_market_match_kind_line"
            ),
        ]

    def __str__(self):
        return f"{self.match} · {self.kind}{f' {self.line}' if self.line is not None else ''}"


class Selection(models.Model):
    class Result(models.TextChoices):
        PENDING = "pending", "Pending"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        VOID = "void", "Void"

    market = models.ForeignKey(Market, related_name="selections", on_delete=models.CASCADE)
    code = models.CharField(max_length=10, help_text="home, draw, away, 1X, 12, X2, over, under, yes, no, 2-1, other")
    odds = models.DecimalField(max_digits=7, decimal_places=2)
    previous_odds = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    probability = models.DecimalField(max_digits=5, decimal_places=4, help_text="The model's fair probability")
    result = models.CharField(max_length=10, choices=Result.choices, default=Result.PENDING)

    class Meta:
        verbose_name_plural = "Selections"
        ordering = ["market", "id"]
        constraints = [models.UniqueConstraint(fields=["market", "code"], name="unique_selection_market_code")]

    def __str__(self):
        return f"{self.market} · {self.code} @ {self.odds}"


class Bet(models.Model):
    """A player's single (one pick) or express (2-10 picks from different matches)."""

    class Kind(models.TextChoices):
        SINGLE = "single", "Single"
        EXPRESS = "express", "Express"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        VOID = "void", "Void (stake returned)"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="sport_bets", on_delete=models.CASCADE)
    key = models.CharField(max_length=64, help_text="The client's idempotency key")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    stake = models.DecimalField(max_digits=12, decimal_places=2)
    total_odds = models.DecimalField(max_digits=10, decimal_places=2)
    potential_win = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    payout = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Bets"
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["user", "key"], name="unique_sport_bet_user_key")]

    def __str__(self):
        return f"{self.kind} {self.stake} @ {self.total_odds} ({self.status})"


class BetSelection(models.Model):
    bet = models.ForeignKey(Bet, related_name="picks", on_delete=models.CASCADE)
    selection = models.ForeignKey(Selection, related_name="picks", on_delete=models.PROTECT)
    match = models.ForeignKey(Match, related_name="picks", on_delete=models.PROTECT)
    odds = models.DecimalField(max_digits=7, decimal_places=2, help_text="The odds when the bet was placed")
    result = models.CharField(max_length=10, choices=Selection.Result.choices, default=Selection.Result.PENDING)

    class Meta:
        verbose_name_plural = "Bet selections"
        ordering = ["bet", "id"]
        constraints = [models.UniqueConstraint(fields=["bet", "match"], name="unique_bet_selection_match")]

    def __str__(self):
        return f"{self.selection} in bet {self.bet_id}"


class BetLabel(models.Model):
    """Names of the markets and picks in one language ({line} is the goal line, e.g. Over 2.5)."""

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    match_result = models.CharField(max_length=50)
    double_chance = models.CharField(max_length=50)
    total_goals = models.CharField(max_length=50)
    both_teams_to_score = models.CharField(max_length=50)
    correct_score = models.CharField(max_length=50)
    home = models.CharField(max_length=30, help_text="1X2 pick when the team's name doesn't fit")
    draw = models.CharField(max_length=30)
    away = models.CharField(max_length=30)
    home_or_draw = models.CharField(max_length=30)
    home_or_away = models.CharField(max_length=30)
    draw_or_away = models.CharField(max_length=30)
    over = models.CharField(max_length=30, help_text="{line} is replaced with the line")
    under = models.CharField(max_length=30, help_text="{line} is replaced with the line")
    yes = models.CharField(max_length=20)
    no = models.CharField(max_length=20)
    other_score = models.CharField(max_length=30)
    single = models.CharField(max_length=30)
    express = models.CharField(max_length=30)
    status_open = models.CharField(max_length=30)
    status_won = models.CharField(max_length=30)
    status_lost = models.CharField(max_length=30)
    status_void = models.CharField(max_length=30)
    model_label = models.CharField(max_length=50, help_text="Shown next to the fair probabilities")

    class Meta:
        verbose_name_plural = "Bet labels"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["lang"], name="unique_bet_label_lang")]

    def __str__(self):
        return f"Bet labels ({self.lang})"
