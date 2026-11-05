import json
import shutil
import tempfile
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from threading import Thread
from unittest import mock

import httpx
from defusedxml import ElementTree as SafeET
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Sum
from django.utils import timezone
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings, tag
from rest_framework.test import APIClient

from base.sample import load_sample, read_sample
from base.svg import UnsafeSvg, is_safe_svg, sanitize_svg
from fairness.rng import float_stream
from leaderboard.services import GAME_KINDS
from wallet.models import Transaction, Wallet
from wallet.services import InsufficientFunds, open_wallet
from . import betting, engine
from .models import Bet, Competition, Market, Match, Season, Selection, Standing, SyncRun, Team, TeamName
from .odds import close_started_markets, price_match, refresh_odds
from .providers import football_data
from .providers.crests import badge_colours, crest_file
from .providers.football_data import STATUSES, FootballDataClient, ProviderError, regular_time
from .providers.rate_limit import RateLimiter
from .runner import Runner
from .services import run_sync

FIXTURES = Path(__file__).parent / "fixtures"
User = get_user_model()
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

    def test_the_first_full_sync_runs_at_once(self):
        self.assertEqual(self.runner(datetime(2026, 11, 5, 1, 0, tzinfo=UTC)).step(), SyncRun.Kind.FULL)

    def test_the_full_sync_runs_once_a_day_after_three_utc(self):
        early = self.runner(datetime(2026, 11, 5, 2, 0, tzinfo=UTC))
        early.last_full = datetime(2026, 11, 4, 3, 0, tzinfo=UTC)
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


# ---------------------------------------------------------------- S2: odds engine, bets, settlement


def stream(seed):
    """Reproducible uniforms for simulations (fairness.rng, never `random`)."""
    return float_stream(seed, "sports-tests", 0)


class EngineTests(SimpleTestCase):
    def test_every_market_sums_to_one(self):
        for lam, mu, rho in [(1.5, 1.1, -0.05), (0.6, 2.4, 0.0), (2.8, 0.4, -0.1)]:
            probabilities = engine.market_probabilities(engine.score_matrix(lam, mu, rho))
            markets = {}
            for (kind, line, _), p in probabilities.items():
                markets[(kind, line)] = markets.get((kind, line), 0) + p
            for market, total in markets.items():
                with self.subTest(lam=lam, mu=mu, market=market):
                    # double chance's three picks overlap: each result is in two of them
                    expected = 2 if market[0] == engine.DOUBLE_CHANCE else 1
                    self.assertAlmostEqual(total, expected, places=9)

    def test_the_overround_is_the_margin(self):
        odds = engine.match_odds(engine.Ratings(base={"PL": 0.25}, home={"PL": 0.2}), "PL", 1, 2)
        markets = {}
        for (kind, line, code), (p, price) in odds.items():
            markets.setdefault((kind, line), []).append(price)
        for (kind, line), prices in markets.items():
            if kind == engine.DOUBLE_CHANCE or engine.MIN_ODDS in prices:
                continue  # overlapping picks, or a floored price that can't carry the margin
            margin = engine.margin_for(kind)
            overround = sum(1 / float(price) for price in prices) - 1
            with self.subTest(market=(kind, line)):
                # rounding odds down only ever adds a little to the margin, never takes from it
                self.assertGreaterEqual(overround, margin - 1e-9)
                self.assertLess(overround, margin + 0.01 * len(prices))

    def test_equal_teams_without_home_advantage_are_symmetric(self):
        ratings = engine.Ratings(base={"PL": 0.3}, home={"PL": 0.0}, rho=-0.05)
        lam, mu = engine.expected_goals(ratings, "PL", 1, 2)
        matrix = engine.score_matrix(lam, mu, ratings.rho)
        home, draw, away = engine.one_x_two(matrix)
        self.assertAlmostEqual(home, away, places=12)
        for x in range(4):
            for y in range(4):
                self.assertAlmostEqual(matrix[x][y], matrix[y][x], places=12)

    def test_odds_round_down_and_have_a_floor(self):
        self.assertEqual(engine.price(0.5, 0.055), Decimal("1.89"))  # 1 / 0.5275 = 1.8957...
        self.assertEqual(engine.price(0.999, 0.055), Decimal("1.01"))
        self.assertEqual(engine.price(0.0, 0.055), engine.MAX_ODDS)

    def test_dixon_coles_moves_only_the_low_scores_and_keeps_the_total(self):
        plain = engine.score_matrix(1.4, 1.1, 0.0)
        corrected = engine.score_matrix(1.4, 1.1, -0.1)
        self.assertGreater(corrected[0][0], plain[0][0])  # more 0-0 and 1-1 with ρ < 0
        self.assertGreater(corrected[1][1], plain[1][1])
        self.assertAlmostEqual(sum(map(sum, corrected)), 1.0, places=12)

    def test_the_fit_finds_the_parameters_that_made_the_data(self):
        teams = range(1, 9)
        truth = engine.Ratings(
            base={"PL": 0.15},
            home={"PL": 0.3},
            attack={team: (team - 4.5) * 0.08 for team in teams},
            defence={team: (4.5 - team) * 0.05 for team in teams},
        )
        uniforms = stream("fit")
        results, day = [], date(2026, 1, 1)
        for _ in range(60):  # 60 double round robins of 8 teams: 3,360 matches on one day
            for home in teams:
                for away in teams:
                    if home != away:
                        lam, mu = engine.expected_goals(truth, "PL", home, away)
                        x, y = engine.sample_score(engine.score_matrix(lam, mu), next(uniforms))
                        results.append(engine.Result("PL", home, away, x, y, day))

        fitted = engine.fit(results, day, shrinkage=0.01)

        self.assertAlmostEqual(fitted.home["PL"], 0.3, delta=0.05)
        mean_attack = sum(fitted.attack.values()) / len(teams)  # only differences between teams are known
        mean_defence = sum(fitted.defence.values()) / len(teams)
        for team in teams:
            with self.subTest(team=team):
                self.assertAlmostEqual(fitted.attack[team] - mean_attack, truth.attack[team], delta=0.1)
                self.assertAlmostEqual(fitted.defence[team] - mean_defence, truth.defence[team], delta=0.1)

    def test_shrinkage_keeps_a_team_with_few_matches_near_the_average(self):
        day = date(2026, 1, 1)
        results = [engine.Result("PL", 1, 2, 5, 0, day)]
        loose = engine.fit(results, day, shrinkage=0.01)
        strict = engine.fit(results, day, shrinkage=4.0)
        self.assertLess(abs(strict.attack[1]), abs(loose.attack[1]))

    def test_older_matches_count_less(self):
        today = date(2026, 5, 1)
        self.assertEqual(engine.weight(today, today), 1)
        self.assertAlmostEqual(engine.weight(date(2026, 1, 1), today), 0.5, delta=0.01)  # 120 days

    def test_settlement_table(self):
        L = Decimal
        cases = [
            # kind, line, code, home goals, away goals, wins
            (engine.ONE_X_TWO, None, "home", 2, 1, True),
            (engine.ONE_X_TWO, None, "draw", 2, 2, True),
            (engine.ONE_X_TWO, None, "away", 2, 2, False),
            (engine.DOUBLE_CHANCE, None, "1X", 1, 1, True),
            (engine.DOUBLE_CHANCE, None, "12", 1, 1, False),
            (engine.DOUBLE_CHANCE, None, "X2", 0, 3, True),
            (engine.TOTAL, L("2.5"), "over", 2, 1, True),
            (engine.TOTAL, L("2.5"), "under", 2, 1, False),
            (engine.TOTAL, L("0.5"), "under", 0, 0, True),
            (engine.TOTAL, L("4.5"), "over", 3, 1, False),
            (engine.BTTS, None, "yes", 1, 1, True),
            (engine.BTTS, None, "no", 3, 0, True),
            (engine.CORRECT_SCORE, None, "2-1", 2, 1, True),
            (engine.CORRECT_SCORE, None, "2-1", 1, 2, False),
            (engine.CORRECT_SCORE, None, "other", 4, 0, True),
            (engine.CORRECT_SCORE, None, "other", 3, 3, False),
        ]
        for kind, line, code, home, away, wins in cases:
            with self.subTest(kind=kind, line=line, code=code, score=(home, away)):
                self.assertIs(engine.selection_wins(kind, line, code, home, away), wins)

    def test_backtest_beats_the_baseline_on_model_data(self):
        teams = range(1, 7)
        truth = engine.Ratings(base={"PL": 0.2}, home={"PL": 0.35}, attack={1: 0.5, 6: -0.5}, defence={1: 0.4, 6: -0.4})
        uniforms = stream("backtest")
        results = []
        for week in range(30):
            day = date(2026, 1, 1) + timedelta(days=7 * week)
            for home in teams:
                for away in teams:
                    if home != away and (home + away + week) % 3 == 0:
                        lam, mu = engine.expected_goals(truth, "PL", home, away)
                        x, y = engine.sample_score(engine.score_matrix(lam, mu), next(uniforms))
                        results.append(engine.Result("PL", home, away, x, y, day))

        report = engine.backtest(results, min_history=40)

        self.assertGreater(report["matches"], 100)
        self.assertLess(report["model_log_loss"], report["baseline_log_loss"])
        self.assertLess(report["model_brier"], report["baseline_brier"])


@tag("slow")
class SimulationTests(SimpleTestCase):
    """manage.py test --tag slow. A bettor who backs a random pick of every market gets 1/(1+margin) back."""

    MATCHES = 200_000

    def test_a_bettor_gets_back_one_over_one_plus_the_margin(self):
        uniforms = stream("simulation")
        ratings = engine.Ratings(base={"PL": 0.25}, home={"PL": 0.25}, rho=-0.05)
        returned = {"main": 0.0, "correct_score": 0.0}
        staked = {"main": 0, "correct_score": 0}
        prices = {}
        for index in range(self.MATCHES):
            # a new pairing every match: attack and defence drawn around the average
            home_attack, away_attack = next(uniforms) - 0.5, next(uniforms) - 0.5
            ratings.attack = {1: home_attack * 0.8, 2: away_attack * 0.8}
            ratings.defence = {1: (next(uniforms) - 0.5) * 0.6, 2: (next(uniforms) - 0.5) * 0.6}
            lam, mu = engine.expected_goals(ratings, "PL", 1, 2)
            matrix = engine.score_matrix(lam, mu, ratings.rho)
            prices = engine.match_odds(ratings, "PL", 1, 2)
            x, y = engine.sample_score(matrix, next(uniforms))
            # one bet on a random pick of one random market
            keys = list(prices)
            kind, line, code = keys[int(next(uniforms) * len(keys))]
            group = "correct_score" if kind == engine.CORRECT_SCORE else "main"
            staked[group] += 1
            if engine.selection_wins(kind, line, code, x, y):
                returned[group] += float(prices[(kind, line, code)][1])

        for group, margin in [("main", engine.MAIN_MARGIN), ("correct_score", engine.CORRECT_SCORE_MARGIN)]:
            rtp = returned[group] / staked[group]
            with self.subTest(group=group, rtp=rtp, bets=staked[group]):
                # rounding odds down costs the bettor a little more; the rest is sampling noise
                self.assertLess(rtp, 1 / (1 + margin) + 0.01)
                self.assertGreater(rtp, 1 / (1 + margin) - 0.03)


class BettingTestCase(TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
        self.competition = Competition.objects.get(code="PL")
        self.season = Season.objects.create(
            competition=self.competition, provider_id=1, start_date=date(2026, 8, 1), end_date=date(2027, 5, 30),
            is_current=True,
        )
        self.teams = [Team.objects.create(provider_id=index, name=f"Team {index}", tla=f"T{index}") for index in range(1, 7)]
        self.matches = [
            self.match(1, self.teams[0], self.teams[1]),
            self.match(2, self.teams[2], self.teams[3]),
            self.match(3, self.teams[4], self.teams[5]),
        ]
        ratings = engine.Ratings(base={"PL": 0.25}, home={"PL": 0.25})
        for match in self.matches:
            price_match(match, ratings, self.now)
        self.user = User.objects.create_user(username="fan@lumora.dev", email="fan@lumora.dev")
        self.wallet = open_wallet(self.user)

    def match(self, provider_id, home, away, hours=24):
        return Match.objects.create(
            provider_id=provider_id, competition=self.competition, season=self.season, home=home, away=away,
            kickoff=self.now + timedelta(hours=hours), status=Match.Status.SCHEDULED, provider_status="TIMED",
        )

    def selection(self, match, kind, code, line=None):
        return Selection.objects.get(market__match=match, market__kind=kind, market__line=line, code=code)

    def pick(self, match, kind="1x2", code="home", line=None):
        selection = self.selection(match, kind, code, line)
        return betting.Pick(selection.id, selection.odds)

    def place(self, picks, stake="10.00", key="k1", now=None):
        return betting.place_bet(self.user, key, Decimal(stake), picks, now=now or self.now)

    def balance(self):
        self.wallet.refresh_from_db()
        return self.wallet.balance

    def finish(self, match, home, away, home_regular=None, away_regular=None, duration="REGULAR"):
        match.status = Match.Status.FINISHED
        match.home_score, match.away_score = home, away
        match.home_regular = home if home_regular is None else home_regular
        match.away_regular = away if away_regular is None else away_regular
        match.duration = duration
        match.save()


class PlaceBetTests(BettingTestCase):
    def test_a_single_takes_the_stake_and_keeps_the_odds(self):
        pick = self.pick(self.matches[0])
        before = self.balance()

        bet, created = self.place([pick])

        self.assertTrue(created)
        self.assertEqual((bet.kind, bet.stake, bet.total_odds), ("single", Decimal("10.00"), pick.odds))
        self.assertEqual(bet.potential_win, (Decimal("10.00") * pick.odds).quantize(Decimal("0.01")))
        self.assertEqual(self.balance(), before - Decimal("10.00"))
        row = Transaction.objects.get(wallet=self.wallet, kind="bet")
        self.assertEqual((row.game, row.round_id), ("football", f"bet:{bet.id}"))

    def test_an_express_multiplies_the_odds(self):
        picks = [self.pick(self.matches[0]), self.pick(self.matches[1], "total", "over", Decimal("2.5"))]
        bet, _ = self.place(picks)
        self.assertEqual(bet.kind, "express")
        self.assertEqual(bet.total_odds, (picks[0].odds * picks[1].odds).quantize(Decimal("0.01"), ROUND_DOWN))
        self.assertEqual(bet.picks.count(), 2)

    def test_changed_odds_answer_409_with_the_new_odds(self):
        pick = self.pick(self.matches[0])
        with self.assertRaises(betting.OddsChanged) as caught:
            self.place([betting.Pick(pick.selection, pick.odds + Decimal("0.10"))])
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(caught.exception.extra, {"selections": [{"selection": pick.selection, "odds": str(pick.odds)}]})
        self.assertFalse(Bet.objects.exists())

    def test_no_bets_after_kickoff(self):
        pick = self.pick(self.matches[0])
        with self.assertRaises(betting.BetError) as caught:
            self.place([pick], now=self.now + timedelta(hours=24))
        self.assertEqual(caught.exception.code, "market_closed")

    def test_closed_markets_take_no_bets(self):
        close_started_markets(self.now + timedelta(hours=25))
        with self.assertRaises(betting.BetError) as caught:
            self.place([self.pick(self.matches[0])])
        self.assertEqual(caught.exception.code, "market_closed")

    def test_one_match_only_once_in_an_express(self):
        picks = [self.pick(self.matches[0]), self.pick(self.matches[0], "btts", "yes")]
        with self.assertRaises(betting.BetError) as caught:
            self.place(picks)
        self.assertEqual(caught.exception.code, "same_match_twice")

    def test_limits(self):
        pick = self.pick(self.matches[0])
        cases = [
            ([pick], "0.50", "stake_too_low"),
            ([pick], "5000.01", "stake_too_high"),
            ([pick] * 11, "10", "too_many_selections"),
            ([self.pick(self.matches[0], "correct_score", "3-3"), self.pick(self.matches[1], "correct_score", "3-3")],
             "10", "odds_too_high"),
        ]
        for picks, stake, code in cases:
            with self.subTest(code=code), self.assertRaises(betting.BetError) as caught:
                self.place(picks, stake=stake, key=code)
            self.assertEqual(caught.exception.code, code)

    def test_the_potential_win_has_a_cap(self):
        picks = [self.pick(self.matches[0], "correct_score", "3-3")]
        with mock.patch.object(betting, "MAX_WIN", Decimal("500.00")), self.assertRaises(betting.BetError) as caught:
            self.place(picks, stake="100")
        self.assertEqual(caught.exception.code, "win_too_high")

    def test_the_same_key_charges_once(self):
        pick = self.pick(self.matches[0])
        first, created = self.place([pick])
        again, created_again = self.place([pick])
        self.assertEqual((first.id, created, created_again), (again.id, True, False))
        self.assertEqual(Transaction.objects.filter(wallet=self.wallet, kind="bet").count(), 1)

    def test_not_enough_lc(self):
        Wallet.objects.filter(pk=self.wallet.pk).update(balance=Decimal("5.00"))
        with self.assertRaises(InsufficientFunds):
            self.place([self.pick(self.matches[0])])
        self.assertFalse(Bet.objects.exists())


class SettlementTests(BettingTestCase):
    def test_every_market_settles_on_the_regular_time_score(self):
        match = self.matches[0]
        self.finish(match, 3, 2, home_regular=2, away_regular=2, duration="EXTRA_TIME")  # a CL tie: 2-2, 3-2 a.e.t.

        betting.settle_markets(self.now + timedelta(days=2))

        def result(kind, code, line=None):
            return self.selection(match, kind, code, line).result

        self.assertEqual(result("1x2", "draw"), "won")
        self.assertEqual(result("1x2", "home"), "lost")
        self.assertEqual(result("double_chance", "X2"), "won")
        self.assertEqual(result("total", "over", Decimal("3.5")), "won")
        self.assertEqual(result("total", "over", Decimal("4.5")), "lost")
        self.assertEqual(result("btts", "yes"), "won")
        self.assertEqual(result("correct_score", "2-2"), "won")
        self.assertEqual(result("correct_score", "other"), "lost")
        self.assertFalse(Market.objects.filter(match=match).exclude(status="settled").exists())

    def test_a_match_without_its_regular_time_score_waits(self):
        match = self.matches[0]
        self.finish(match, 3, 2)
        Match.objects.filter(pk=match.pk).update(home_regular=None, away_regular=None)
        self.assertEqual(betting.settle_markets(self.now + timedelta(days=2)), 0)

    def test_a_winning_single_is_paid(self):
        pick = self.pick(self.matches[0])
        bet, _ = self.place([pick])
        before = self.balance()
        self.finish(self.matches[0], 2, 0)

        betting.settle(self.now + timedelta(days=2))

        bet.refresh_from_db()
        self.assertEqual((bet.status, bet.payout), ("won", bet.potential_win))
        self.assertEqual(self.balance(), before + bet.potential_win)
        self.assertEqual(Transaction.objects.get(wallet=self.wallet, kind="win").game, "football")

    def test_one_lost_pick_loses_the_express(self):
        bet, _ = self.place([self.pick(self.matches[0]), self.pick(self.matches[1])])
        before = self.balance()
        self.finish(self.matches[0], 2, 0)
        self.finish(self.matches[1], 0, 1)

        betting.settle(self.now + timedelta(days=2))

        bet.refresh_from_db()
        self.assertEqual((bet.status, bet.payout), ("lost", Decimal("0.00")))
        self.assertEqual(self.balance(), before)

    def test_an_express_waits_for_all_its_matches(self):
        bet, _ = self.place([self.pick(self.matches[0]), self.pick(self.matches[1])])
        self.finish(self.matches[0], 2, 0)
        betting.settle(self.now + timedelta(days=2))
        bet.refresh_from_db()
        self.assertEqual(bet.status, "open")

    def test_a_void_single_gives_the_stake_back(self):
        bet, _ = self.place([self.pick(self.matches[0])])
        before = self.balance()
        Match.objects.filter(pk=self.matches[0].pk).update(status=Match.Status.POSTPONED)

        betting.settle(self.now + timedelta(days=2))

        bet.refresh_from_db()
        self.assertEqual((bet.status, bet.payout), ("void", Decimal("10.00")))
        self.assertEqual(self.balance(), before + Decimal("10.00"))
        self.assertEqual(Transaction.objects.get(wallet=self.wallet, kind="refund").amount, Decimal("10.00"))

    def test_a_void_pick_counts_as_one_in_an_express(self):
        first, second = self.pick(self.matches[0]), self.pick(self.matches[1])
        bet, _ = self.place([first, second])
        self.finish(self.matches[0], 2, 0)
        Match.objects.filter(pk=self.matches[1].pk).update(status=Match.Status.CANCELLED)

        betting.settle(self.now + timedelta(days=2))

        bet.refresh_from_db()
        self.assertEqual((bet.status, bet.payout), ("won", (Decimal("10.00") * first.odds).quantize(Decimal("0.01"))))

    def test_a_suspended_match_is_void_only_after_48_hours(self):
        bet, _ = self.place([self.pick(self.matches[0])])
        Match.objects.filter(pk=self.matches[0].pk).update(status=Match.Status.SUSPENDED)

        betting.settle(self.now + timedelta(hours=30))
        bet.refresh_from_db()
        self.assertEqual(bet.status, "open")

        betting.settle(self.now + timedelta(hours=24 + 49))
        bet.refresh_from_db()
        self.assertEqual(bet.status, "void")

    def test_settling_again_changes_nothing(self):
        self.place([self.pick(self.matches[0])])
        self.finish(self.matches[0], 1, 0)
        later = self.now + timedelta(days=2)
        betting.settle(later)
        balance, rows = self.balance(), Transaction.objects.count()

        self.assertEqual(betting.settle(later), (0, 0))

        self.assertEqual((self.balance(), Transaction.objects.count()), (balance, rows))

    def test_the_leaderboard_counts_football_and_nets_a_refund_to_zero(self):
        self.place([self.pick(self.matches[0])])
        Match.objects.filter(pk=self.matches[0].pk).update(status=Match.Status.POSTPONED)
        betting.settle(self.now + timedelta(days=2))
        net = Transaction.objects.filter(wallet=self.wallet, kind__in=GAME_KINDS).aggregate(net=Sum("amount"))["net"]
        self.assertEqual(net, Decimal("0.00"))


class OddsRefreshTests(BettingTestCase):
    def test_new_odds_keep_the_previous_ones_and_kickoff_freezes_them(self):
        selection = self.selection(self.matches[0], "1x2", "home")
        stronger = engine.Ratings(base={"PL": 0.25}, home={"PL": 0.25}, attack={self.teams[0].id: 0.6})
        price_match(self.matches[0], stronger, self.now)

        moved = self.selection(self.matches[0], "1x2", "home")
        self.assertLess(moved.odds, selection.odds)
        self.assertEqual(moved.previous_odds, selection.odds)

        close_started_markets(self.now + timedelta(hours=25))
        price_match(self.matches[0], engine.Ratings(base={"PL": 0.25}, home={"PL": 0.25}), self.now + timedelta(hours=25))
        self.assertEqual(self.selection(self.matches[0], "1x2", "home").odds, moved.odds)

    def test_refresh_prices_the_next_14_days_only(self):
        far = self.match(4, self.teams[0], self.teams[2], hours=24 * 20)
        run = refresh_odds(self.now)
        self.assertEqual(run.priced_matches, 3)
        self.assertFalse(Market.objects.filter(match=far).exists())


class SportBetApiTests(BettingTestCase):
    @classmethod
    def setUpTestData(cls):
        load_sample(read_sample())

    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def post(self, picks, key="api-1", stake="10.00"):
        body = {"key": key, "stake": stake, "selections": [{"selection": p.selection, "odds": str(p.odds)} for p in picks]}
        with mock.patch("sports.betting.timezone.now", return_value=self.now):
            return self.api.post("/api/sport_bets", body, format="json")

    def test_markets_can_be_asked_by_matches_day_and_kind(self):
        day = self.matches[0].kickoff.date().isoformat()
        both = f"{self.matches[0].id},{self.matches[1].id}"
        self.assertEqual({row["match"] for row in self.client.get(f"/api/markets?match={both}").json()}, {self.matches[0].id, self.matches[1].id})
        rows = self.client.get(f"/api/markets?date={day}&kind=1x2").json()
        self.assertEqual({row["kind"] for row in rows}, {"1x2"})
        self.assertEqual(len(rows), 3)
        self.assertEqual(self.client.get("/api/markets?date=nope").json(), [])
        self.assertEqual(self.client.get("/api/markets?match=1,x").json(), [])
        self.assertEqual(self.client.get(f"/api/matches/{self.matches[0].id}").json()["market_count"], 9)

    def test_markets_of_a_match(self):
        rows = self.client.get(f"/api/markets?match={self.matches[0].id}").json()
        kinds = {row["kind"] for row in rows}
        self.assertEqual(kinds, {"1x2", "double_chance", "total", "btts", "correct_score"})
        self.assertEqual(len([row for row in rows if row["kind"] == "total"]), 5)
        self.assertEqual(self.client.get("/api/markets?match=abc").json(), [])

    def test_place_and_list_bets(self):
        response = self.post([self.pick(self.matches[0])])
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual((body["kind"], body["stake"], body["status"]), ("single", "10.00", "open"))
        self.assertIn("balance", body)
        self.assertEqual(self.post([self.pick(self.matches[0])]).status_code, 200)  # same key

        self.assertEqual(len(self.api.get("/api/sport_bets?status=open").json()), 1)
        self.assertEqual(self.api.get("/api/sport_bets?status=settled").json(), [])
        self.assertEqual(self.api.get("/api/sport_bets/summary").json()["open"], 1)

    def test_changed_odds_answer_409_in_the_players_language(self):
        pick = self.pick(self.matches[0])
        response = self.post([betting.Pick(pick.selection, pick.odds + 1)])
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body["code"], "odds_changed")
        self.assertEqual(body["selections"], [{"selection": pick.selection, "odds": str(pick.odds)}])

    def test_bets_are_private(self):
        self.assertEqual(self.client.get("/api/sport_bets").status_code, 401)

    def test_summary_of_the_week(self):
        self.post([self.pick(self.matches[0])], key="a")
        self.post([self.pick(self.matches[1])], key="b")
        self.finish(self.matches[0], 1, 0)
        self.finish(self.matches[1], 0, 1)
        betting.settle(self.now + timedelta(days=2))

        summary = self.api.get("/api/sport_bets/summary").json()
        won = Bet.objects.get(key="a").payout

        self.assertEqual(summary["staked"], "20.00")
        self.assertEqual(summary["returned"], str(won))
        self.assertEqual(summary["profit"], str(won - Decimal("20.00")))
        self.assertEqual((summary["won"], summary["open"], summary["bets"]), (1, 0, 2))

    def test_bet_labels_in_every_language(self):
        for lang in ["en", "am", "ru"]:
            with self.subTest(lang=lang):
                self.assertEqual([row["lang"] for row in self.client.get(f"/api/bet_labels?lang={lang}").json()], [lang])


class ParallelBetTests(TransactionTestCase):
    """Real parallel requests on PostgreSQL: the row locks keep the money right."""

    def setUp(self):
        now = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
        # TransactionTestCase empties the tables between tests, the seeded competitions too
        competition, _ = Competition.objects.get_or_create(code="PL", defaults={"name": "Premier League"})
        season = Season.objects.create(
            competition=competition, provider_id=1, start_date=date(2026, 8, 1), end_date=date(2027, 5, 30)
        )
        home = Team.objects.create(provider_id=1, name="A")
        away = Team.objects.create(provider_id=2, name="B")
        self.match = Match.objects.create(
            provider_id=1, competition=competition, season=season, home=home, away=away,
            kickoff=now + timedelta(days=1), status=Match.Status.SCHEDULED, provider_status="TIMED",
        )
        price_match(self.match, engine.Ratings(base={"PL": 0.25}), now)
        self.selection = Selection.objects.get(market__match=self.match, market__kind="1x2", code="home")
        self.user = User.objects.create_user(username="p@lumora.dev", email="p@lumora.dev")
        self.wallet = open_wallet(self.user)
        self.now = now

    def run_parallel(self, calls):
        results = []

        def run(call):
            try:
                results.append(call())
            except Exception as exc:  # noqa: BLE001 - the test inspects what each thread got
                results.append(exc)
            finally:
                connection.close()

        threads = [Thread(target=run, args=(call,)) for call in calls]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return results

    def bet(self, key, stake):
        pick = betting.Pick(self.selection.id, self.selection.odds)
        return lambda: betting.place_bet(self.user, key, Decimal(stake), [pick], now=self.now)

    def test_the_same_key_twice_at_once_charges_once(self):
        self.run_parallel([self.bet("same", "10"), self.bet("same", "10")])
        self.assertEqual(Bet.objects.count(), 1)
        self.assertEqual(Transaction.objects.filter(wallet=self.wallet, kind="bet").count(), 1)

    def test_two_bets_bigger_than_the_balance_together_one_fails(self):
        Wallet.objects.filter(pk=self.wallet.pk).update(balance=Decimal("5000.00"))
        results = self.run_parallel([self.bet("a", "3000"), self.bet("b", "3000")])
        self.assertEqual(sum(isinstance(result, InsufficientFunds) for result in results), 1)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("2000.00"))

    def test_settling_twice_at_once_pays_once(self):
        betting.place_bet(self.user, "s", Decimal("10"), [betting.Pick(self.selection.id, self.selection.odds)], now=self.now)
        Match.objects.filter(pk=self.match.pk).update(
            status=Match.Status.FINISHED, home_score=1, away_score=0, home_regular=1, away_regular=0
        )
        later = self.now + timedelta(days=2)
        self.run_parallel([lambda: betting.settle(later), lambda: betting.settle(later)])
        self.assertEqual(Transaction.objects.filter(wallet=self.wallet, kind="win").count(), 1)


class FootballPageApiTests(BettingTestCase):
    @classmethod
    def setUpTestData(cls):
        load_sample(read_sample())

    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def test_ui_labels_in_every_language(self):
        for lang in ["en", "am", "ru"]:
            with self.subTest(lang=lang):
                rows = self.client.get(f"/api/sports_ui_labels?lang={lang}").json()
                self.assertEqual([row["lang"] for row in rows], [lang])
                self.assertTrue(rows[0]["slip_title"])

    def test_the_match_page_has_form_and_table_places(self):
        a, b = self.teams[0], self.teams[1]
        for index, (home, away) in enumerate([(2, 0), (1, 1), (0, 3)]):  # a is at home: W, D, L
            past = self.match(100 + index, a, b, hours=-24 * (index + 1))
            past.status = Match.Status.FINISHED
            past.home_regular, past.away_regular = home, away
            past.save()
        Standing.objects.create(season=self.season, team=a, position=3, points=21)

        body = self.client.get(f"/api/matches/{self.matches[0].id}").json()

        self.assertEqual(body["home_form"], ["W", "D", "L"])  # newest first
        self.assertEqual(body["away_form"], ["L", "D", "W"])
        self.assertEqual(body["home_table"], {"position": 3, "points": 21})
        self.assertIsNone(body["away_table"])
        self.assertEqual(self.client.get("/api/matches/999999").status_code, 404)

    def test_popular_picks_are_the_most_bet_open_picks(self):
        self.assertEqual(self.client.get("/api/popular_picks").json(), [])
        popular = self.pick(self.matches[0])
        other = self.pick(self.matches[1])
        betting.place_bet(self.user, "one", Decimal("5"), [popular], now=self.now)
        second = User.objects.create_user(username="two@lumora.dev", email="two@lumora.dev")
        open_wallet(second)
        betting.place_bet(second, "two", Decimal("5"), [popular], now=self.now)
        betting.place_bet(self.user, "three", Decimal("5"), [other], now=self.now)

        with mock.patch("sports.views.timezone.now", return_value=self.now):
            rows = self.client.get("/api/popular_picks").json()

        self.assertEqual([(row["id"], row["picks"]) for row in rows], [(popular.selection, 2), (other.selection, 1)])
        self.assertEqual(rows[0]["match"]["home"]["tla"], "T1")

    def test_the_summary_has_the_profit_of_each_of_the_last_7_days(self):
        bet, _ = self.place([self.pick(self.matches[0])])
        self.finish(self.matches[0], 1, 0)
        settle_time = timezone.now()
        betting.settle(settle_time)

        days = self.api.get("/api/sport_bets/summary").json()["by_day"]

        self.assertEqual(len(days), 7)
        self.assertEqual(days[-1]["date"], settle_time.date().isoformat())
        bet.refresh_from_db()
        self.assertEqual(days[-1]["profit"], str(bet.payout - bet.stake))
        self.assertTrue(all(day["profit"] == "0.00" for day in days[:-1]))
