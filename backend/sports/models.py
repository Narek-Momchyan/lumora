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
