import json
import shutil
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from unittest import mock

import httpx
from defusedxml import ElementTree as SafeET
from django.test import SimpleTestCase, TestCase, override_settings

from base.sample import load_sample, read_sample
from base.svg import UnsafeSvg, is_safe_svg, sanitize_svg
from .models import Competition, Match, Season, Standing, SyncRun, Team, TeamName
from .providers import football_data
from .providers.crests import badge_colours, crest_file
from .providers.football_data import STATUSES, FootballDataClient, ProviderError, regular_time
from .providers.rate_limit import RateLimiter
from .runner import Runner
from .services import run_sync

FIXTURES = Path(__file__).parent / "fixtures"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeClock:
    """A clock that only moves when the code under test sleeps."""

    def __init__(self, now=0.0):
        self.now = now
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class RecordedApi:
    """football-data.org answered from sports/fixtures, never from the network."""

    def __init__(self, overrides=None):
        self.paths = []
        self.overrides = overrides or {}

    def __call__(self, request):
        path = request.url.path
        self.paths.append(path)
        if self.overrides.get(path):
            return self.overrides[path].pop(0)
        if request.url.host == "crests.football-data.org":
            if path.endswith(".svg"):
                return httpx.Response(200, content=(FIXTURES / "crest_clean.svg").read_bytes())
            return httpx.Response(200, content=PNG)
        parts = path.strip("/").split("/")  # v4, competitions, PL[, teams]
        code = parts[2].lower()
        resource = parts[3] if len(parts) > 3 else "competition"
        return httpx.Response(200, json=fixture(f"{code}_{resource}.json"))


def client(api=None, clock=None):
    clock = clock or FakeClock()
    return FootballDataClient(
        "test-token",
        base_url="https://api.football-data.org/v4",
        transport=httpx.MockTransport(api or RecordedApi()),
        limiter=RateLimiter(per_minute=10, clock=clock, sleep=clock.sleep),
    )


class RateLimiterTests(SimpleTestCase):
    def test_the_eleventh_call_in_a_minute_waits_for_the_first_to_age_out(self):
        clock = FakeClock()
        limiter = RateLimiter(per_minute=10, clock=clock, sleep=clock.sleep)
        for _ in range(10):
            limiter.wait()
            clock.now += 1
        self.assertEqual(clock.sleeps, [])

        limiter.wait()
        self.assertEqual(clock.sleeps, [50])  # the first call was at 0 s, now it is 10 s

    def test_calls_spread_over_more_than_a_minute_never_wait(self):
        clock = FakeClock()
        limiter = RateLimiter(per_minute=10, clock=clock, sleep=clock.sleep)
        for _ in range(30):
            limiter.wait()
            clock.now += 6
        self.assertEqual(clock.sleeps, [])

    def test_a_429_waits_for_the_reset_and_retries(self):
        clock = FakeClock()
        limited = httpx.Response(429, headers={"X-RequestCounter-Reset": "23"})
        api = RecordedApi({"/v4/competitions/PL": [limited]})

        data = client(api, clock).competition("PL")

        self.assertEqual(data.code, "PL")
        self.assertEqual(api.paths, ["/v4/competitions/PL", "/v4/competitions/PL"])
        self.assertEqual(clock.sleeps, [24])

    def test_it_gives_up_after_repeated_429s(self):
        clock = FakeClock()
        api = RecordedApi({"/v4/competitions/PL": [httpx.Response(429) for _ in range(4)]})
        with self.assertRaises(ProviderError):
            client(api, clock).competition("PL")

    def test_the_token_goes_to_the_api_but_not_to_the_crest_host(self):
        seen = {}

        def handler(request):
            seen[request.url.host] = request.headers.get("X-Auth-Token")
            if request.url.host == "crests.football-data.org":
                return httpx.Response(200, content=PNG)
            return httpx.Response(200, json=fixture("pl_competition.json"))

        api_client = client(handler)
        api_client.competition("PL")
        api_client.download("https://crests.football-data.org/57.png")

        self.assertEqual(seen["api.football-data.org"], "test-token")
        self.assertIsNone(seen["crests.football-data.org"])


class ParsingTests(SimpleTestCase):
    def test_every_provider_status_has_our_status(self):
        expected = {
            "SCHEDULED": "scheduled",
            "TIMED": "scheduled",
            "IN_PLAY": "live",
            "EXTRA_TIME": "live",
            "PENALTY_SHOOTOUT": "live",
            "PAUSED": "paused",
            "FINISHED": "finished",
            "AWARDED": "awarded",
            "POSTPONED": "postponed",
            "SUSPENDED": "suspended",
            "CANCELLED": "cancelled",
        }
        self.assertEqual(STATUSES, expected)
        self.assertTrue(set(STATUSES.values()) <= set(Match.Status.values))

    def test_an_unknown_status_is_an_error_not_a_guess(self):
        raw = fixture("pl_matches.json")["matches"][0] | {"status": "SOMETHING_NEW"}
        with self.assertRaises(ProviderError):
            football_data.match(raw)

    def test_regular_time_of_a_regular_match_is_the_full_time(self):
        score = regular_time({"duration": "REGULAR", "fullTime": {"home": 2, "away": 1}})
        self.assertEqual((score.home, score.away), (2, 1))

    def test_regular_time_comes_from_the_provider_after_extra_time(self):
        raw = fixture("cl_matches.json")["matches"][0]["score"]
        score = regular_time(raw)
        self.assertEqual((score.home, score.away), (2, 2))

    def test_without_regular_time_it_is_full_time_minus_extra_time(self):
        raw = {"duration": "EXTRA_TIME", "fullTime": {"home": 3, "away": 1}, "extraTime": {"home": 1, "away": 0}}
        score = regular_time(raw)
        self.assertEqual((score.home, score.away), (2, 1))

    def test_regular_time_stays_unknown_without_numbers(self):
        score = regular_time({"duration": "EXTRA_TIME", "fullTime": {"home": 1, "away": 1}})
        self.assertEqual((score.home, score.away), (None, None))

    def test_badge_colours_from_club_colours(self):
        self.assertEqual(badge_colours("Red / White"), ("#d71920", "#ffffff"))
        self.assertEqual(badge_colours("Sky Blue / White"), ("#6cabdd", "#111111"))
        self.assertIsNone(badge_colours("Unknown / Hues"))


class SvgTests(SimpleTestCase):
    def test_scripts_handlers_and_external_links_are_removed(self):
        clean = sanitize_svg((FIXTURES / "crest_evil.svg").read_bytes())
        text = clean.decode()
        for bad in ["script", "onload", "onclick", "foreignObject", "iframe", "javascript:", "evil.example", "image"]:
            with self.subTest(bad=bad):
                self.assertNotIn(bad, text)
        self.assertIn("circle", text)  # the drawing itself stays
        SafeET.fromstring(clean)  # and it is still a valid SVG

    def test_entities_and_doctypes_are_refused(self):
        with self.assertRaises(UnsafeSvg):
            sanitize_svg((FIXTURES / "crest_xxe.svg").read_bytes())

    def test_a_clean_svg_passes_unchanged_in_substance(self):
        data = (FIXTURES / "crest_clean.svg").read_bytes()
        self.assertTrue(is_safe_svg(data))
        self.assertFalse(is_safe_svg((FIXTURES / "crest_evil.svg").read_bytes()))

    def test_not_an_svg_is_refused(self):
        for data in [b"<html><body/></html>", b"not xml", b"<svg"]:
            with self.subTest(data=data), self.assertRaises(UnsafeSvg):
                sanitize_svg(data)

    def test_crest_files(self):
        svg = crest_file("https://crests.football-data.org/61.svg", (FIXTURES / "crest_evil.svg").read_bytes())
        self.assertEqual(svg.name, "61.svg")
        self.assertNotIn(b"script", svg.read())
        self.assertEqual(crest_file("https://crests.football-data.org/57.png", PNG).name, "57.png")
        self.assertIsNone(crest_file("https://crests.football-data.org/57.png", b"GIF? no, text"))


class SyncTestCase(TestCase):
    def setUp(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        settings = override_settings(MEDIA_ROOT=media)
        settings.enable()
        self.addCleanup(settings.disable)
        Competition.objects.exclude(code__in=["PL", "CL"]).update(is_active=False)

    def sync(self, kind=SyncRun.Kind.FULL, api=None):
        return run_sync(client(api), kind, today=date(2026, 11, 5))


class SyncTests(SyncTestCase):
    def counts(self):
        return {model.__name__: model.objects.count() for model in [Season, Team, Match, Standing]}

    def test_a_full_sync_stores_seasons_teams_matches_and_tables(self):
        runs = self.sync()

        self.assertTrue(all(run.ok for run in runs), [run.errors for run in runs])
        self.assertEqual(self.counts(), {"Season": 2, "Team": 6, "Match": 8, "Standing": 8})
        arsenal = Team.objects.get(provider_id=57)
        self.assertEqual((arsenal.tla, arsenal.color, arsenal.text_color), ("ARS", "#d71920", "#ffffff"))
        self.assertEqual(set(arsenal.competitions.values_list("code", flat=True)), {"PL", "CL"})
        self.assertTrue(arsenal.crest.name.endswith("57.png"))
        self.assertTrue(Team.objects.get(provider_id=61).crest.name.endswith("61.svg"))

    def test_running_it_twice_keeps_the_same_rows(self):
        self.sync()
        ids = {model: set(model.objects.values_list("id", flat=True)) for model in [Season, Team, Match, Standing]}

        runs = self.sync()

        for model, before in ids.items():
            with self.subTest(model=model.__name__):
                self.assertEqual(set(model.objects.values_list("id", flat=True)), before)
        self.assertEqual([(run.created, run.updated) for run in runs], [(0, 0), (0, 0)])

    def test_statuses_and_scores_are_stored(self):
        self.sync()
        finished = Match.objects.get(provider_id=500003)
        self.assertEqual((finished.status, finished.home_score, finished.away_score), ("finished", 2, 1))
        self.assertEqual((finished.home_regular, finished.away_regular), (2, 1))
        self.assertEqual(Match.objects.get(provider_id=500001).status, "scheduled")
        self.assertEqual(Match.objects.get(provider_id=500004).status, "live")
        self.assertEqual(Match.objects.get(provider_id=500005).status, "postponed")
        self.assertEqual(Match.objects.get(provider_id=500001).kickoff, datetime(2026, 11, 8, 16, 30, tzinfo=UTC))

    def test_knockout_matches_keep_the_regular_time_score_apart(self):
        self.sync()
        extra = Match.objects.get(provider_id=600001)
        self.assertEqual((extra.home_score, extra.away_score), (3, 2))
        self.assertEqual((extra.home_regular, extra.away_regular), (2, 2))
        self.assertEqual((extra.home_extra, extra.away_extra), (1, 0))

        shootout = Match.objects.get(provider_id=600002)
        self.assertEqual((shootout.home_regular, shootout.away_regular), (1, 1))
        self.assertEqual((shootout.home_penalties, shootout.away_penalties), (3, 4))
        self.assertEqual(shootout.duration, "PENALTY_SHOOTOUT")

    def test_a_crest_is_downloaded_once_and_an_admin_crest_is_never_replaced(self):
        self.sync()
        api = RecordedApi()
        team = Team.objects.get(provider_id=57)
        Team.objects.filter(provider_id=61).update(crest_locked=True, crest_source_url="")

        self.sync(api=api)

        self.assertFalse([path for path in api.paths if path.endswith((".png", ".svg"))])
        team.refresh_from_db()
        self.assertTrue(team.crest.name.endswith("57.png"))

    def test_a_today_sync_asks_only_for_yesterday_to_tomorrow(self):
        self.sync()
        seen = []

        def handler(request):
            seen.append(str(request.url))
            return RecordedApi()(request)

        self.sync(SyncRun.Kind.TODAY, handler)

        matches = [url for url in seen if url.split("?")[0].endswith("/matches")]
        self.assertTrue(matches)
        self.assertTrue(all("dateFrom=2026-11-04&dateTo=2026-11-06" in url for url in matches))
        self.assertFalse([url for url in seen if url.endswith("/teams")])

    def test_an_error_in_one_competition_is_recorded_and_the_others_go_on(self):
        api = RecordedApi({"/v4/competitions/PL": [httpx.Response(403)]})
        with self.assertLogs("sports.services", "ERROR"):
            runs = self.sync(api=api)

        by_code = {run.competition.code: run for run in runs}
        self.assertFalse(by_code["PL"].ok)
        self.assertIn("403", by_code["PL"].errors)
        self.assertTrue(by_code["CL"].ok)
        self.assertGreater(by_code["CL"].requests, 0)
        self.assertIsNotNone(by_code["PL"].finished_at)


class ApiTests(SyncTestCase):
    @classmethod
    def setUpTestData(cls):
        load_sample(read_sample())

    def setUp(self):
        super().setUp()
        self.sync()
        team = Team.objects.get(provider_id=57)
        TeamName.objects.create(team=team, lang="am", name="Արսենալ", short_name="Արսենալ")

    def get(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_competitions_have_their_current_season(self):
        rows = self.get("/api/competitions")
        self.assertEqual([row["code"] for row in rows], ["PL", "CL"])
        self.assertEqual(rows[0]["season"]["current_matchday"], 11)

    def test_team_names_fall_back_to_english(self):
        names = {row["tla"]: row["name"] for row in self.get("/api/teams?competition=PL&lang=am")}
        self.assertEqual(names["ARS"], "Արսենալ")
        self.assertEqual(names["CHE"], "Chelsea FC")
        self.assertEqual(len(self.get("/api/teams?competition=CL")), 4)

    def test_match_filters(self):
        self.assertEqual(len(self.get("/api/matches?competition=PL")), 5)
        self.assertEqual(len(self.get("/api/matches?date=2026-11-08")), 2)
        self.assertEqual(len(self.get("/api/matches?status=finished")), 3)
        team = Team.objects.get(provider_id=57).id
        self.assertEqual(len(self.get(f"/api/matches?team={team}")), 5)
        row = self.get("/api/matches?competition=CL&status=finished")[0]
        self.assertEqual((row["home"]["tla"], row["home_regular"], row["home_score"]), ("FCB", 2, 3))

    def test_unknown_filter_values_return_an_empty_list(self):
        for url in [
            "/api/matches?competition=XX",
            "/api/matches?date=tomorrow",
            "/api/matches?status=nope",
            "/api/matches?team=abc",
            "/api/teams?competition=XX",
            "/api/standings?competition=XX",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.get(url), [])

    def test_standings_of_the_current_season(self):
        rows = self.get("/api/standings?competition=PL")
        self.assertEqual([row["position"] for row in rows], [1, 2, 3, 4])
        self.assertEqual(rows[0]["team"]["tla"], "ARS")

    def test_the_football_api_is_read_only(self):
        for url in ["/api/competitions", "/api/teams", "/api/matches", "/api/standings"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, {}).status_code, 405)

    def test_sports_page_labels_in_every_language(self):
        for lang in ["en", "am", "ru"]:
            with self.subTest(lang=lang):
                self.assertEqual([row["lang"] for row in self.get(f"/api/sports_page_labels?lang={lang}")], [lang])


class RunnerTests(SyncTestCase):
    def runner(self, now):
        return Runner(client=client(), clock=lambda: now, sleep=lambda seconds: None)

    def test_the_full_sync_runs_once_a_day_after_three_utc(self):
        early = self.runner(datetime(2026, 11, 5, 2, 0, tzinfo=UTC))
        self.assertIsNone(early.step())

        runner = self.runner(datetime(2026, 11, 5, 3, 5, tzinfo=UTC))
        self.assertEqual(runner.step(), SyncRun.Kind.FULL)
        self.assertNotEqual(runner.step(), SyncRun.Kind.FULL)

        tomorrow = self.runner(datetime(2026, 11, 6, 3, 1, tzinfo=UTC))
        self.assertEqual(tomorrow.step(), SyncRun.Kind.FULL)

    @override_settings(SPORTS_SYNC_INTERVAL_MINUTES=5)
    def test_on_a_match_day_it_syncs_today_every_few_minutes(self):
        self.sync()
        now = datetime(2026, 11, 8, 17, 0, tzinfo=UTC)  # two matches today
        clock = mock.Mock(return_value=now)
        runner = Runner(client=client(), clock=clock, sleep=lambda seconds: None)
        runner.last_full = now  # today's full sync is done

        self.assertEqual(runner.step(), SyncRun.Kind.TODAY)
        clock.return_value = datetime(2026, 11, 8, 17, 3, tzinfo=UTC)
        self.assertIsNone(runner.step())
        clock.return_value = datetime(2026, 11, 8, 17, 6, tzinfo=UTC)
        self.assertEqual(runner.step(), SyncRun.Kind.TODAY)

    def test_on_a_day_without_matches_it_waits(self):
        self.sync()
        now = datetime(2026, 11, 10, 17, 0, tzinfo=UTC)
        runner = self.runner(now)
        runner.last_full = now
        self.assertIsNone(runner.step())
