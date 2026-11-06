from datetime import UTC, date, datetime, timedelta
import time
from threading import Thread
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from rest_framework.test import APIClient

from base.sample import load_sample, read_sample
from errors.exceptions import CodedError
from sports import predictions
from sports.models import Competition, Match, Prediction, Season, Team
from . import services, text
from .models import BannedWord, Forum, ForumBan, Post, PostLike, PostReport, Topic, TopicView

User = get_user_model()
NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def code_of(exc):
    return exc.exception.detail.code


# ------------------------------------------------------------------ the pure text rules


class CleanTests(SimpleTestCase):
    def test_it_trims_and_keeps_one_empty_line(self):
        self.assertEqual(text.clean("  hello \r\n\r\n\r\n\r\nworld  \n"), "hello\n\nworld")

    def test_control_and_invisible_characters_are_removed(self):
        self.assertEqual(text.clean("a\x00b\x07c​d‮e"), "abcde")

    def test_a_text_of_only_blanks_is_empty(self):
        self.assertEqual(text.clean(" \n\t ​ \n"), "")

    def test_armenian_letters_count_one_each(self):
        self.assertEqual(len(text.clean("Արսենալ")), 7)


class LinkTests(SimpleTestCase):
    def test_links_in_every_shape_are_found(self):
        for sample in [
            "http://example.com", "https://x.y/z", "HTTPS://EXAMPLE.COM", "ftp://files.net", "www.example.org",
            "example.com", "see example.ru/path", "site . com", "mail me a@b.org", "WWW . site", "visit 1xbet.co now",
            "h​ttp://x.am",
        ]:
            with self.subTest(sample=sample):
                self.assertTrue(text.has_link(sample))

    def test_ordinary_football_text_is_not_a_link(self):
        for sample in ["Arsenal v. Chelsea", "3.5 goals", "He scored. Then he left", "Mr. Smith", "5-2 win", "ok...", "Սա լավ խաղ էր։"]:
            with self.subTest(sample=sample):
                self.assertFalse(text.has_link(sample))


class BannedWordTests(SimpleTestCase):
    def hit(self, sample, *entries):
        return text.banned_hit(sample, [(text.key_of(word), inside) for word, inside in entries])

    def test_case_and_punctuation_do_not_matter(self):
        for sample in ["You IDIOT", "idiot!", "what an Idiot.", "Idiot"]:
            with self.subTest(sample=sample):
                self.assertTrue(self.hit(sample, ("idiot", False)))

    def test_obvious_bypasses_are_caught(self):
        for sample in [
            "i d i o t", "i.d.i.o.t", "I-D-I-O-T", "idi0t", "1diot", "id​iot", "іdiot",  # Cyrillic i
            "idiooot", "iiidiot", "ІDІOT", "idiot́",
        ]:
            with self.subTest(sample=sample):
                self.assertTrue(self.hit(sample, ("idiot", False)))

    def test_a_longer_word_is_not_a_hit(self):
        # "ass" must not trip "class", "assist" or "pass", and "idiot" not "idiotic" unless the entry says so
        for sample in ["class", "she is the assistant coach", "great pass", "assassin"]:
            with self.subTest(sample=sample):
                self.assertFalse(self.hit(sample, ("ass", False)))
        self.assertFalse(self.hit("idiotic", ("idiot", False)))
        self.assertTrue(self.hit("idiotic", ("idiot", True)))
        self.assertTrue(self.hit("you ass", ("ass", False)))
        self.assertTrue(self.hit("assss", ("ass", False)))

    def test_short_common_words_stay_safe(self):
        self.assertFalse(self.hit("as it was", ("ass", False)))

    def test_a_phrase_matches_as_a_phrase(self):
        self.assertTrue(self.hit("win real money fast", ("real money", False)))
        self.assertFalse(self.hit("a real fan with money", ("real money", False)))

    def test_russian_with_endings_and_capitals(self):
        self.assertTrue(self.hit("ИДИОТЫ", ("идиот", True)))
        self.assertTrue(self.hit("какой идиот", ("идиот", False)))
        self.assertFalse(self.hit("какой идиотизм", ("идиот", False)))

    def test_armenian_with_capitals_and_endings(self):
        self.assertTrue(self.hit("ԱՊՈՒՇԸ", ("ապուշ", True)))
        self.assertTrue(self.hit("դու ապուշ ես", ("ապուշ", False)))
        self.assertTrue(self.hit("Ապուշ", ("ապուշ", False)))
        self.assertFalse(self.hit("ապուշություն", ("ապուշ", False)))
        self.assertFalse(self.hit("Արսենալը հաղթեց", ("ապուշ", True)))

    def test_an_empty_entry_matches_nothing(self):
        self.assertFalse(self.hit("anything", ("", False)))

    def test_key_of_folds_the_same_way_as_the_text(self):
        self.assertEqual(text.key_of("1xBET"), text.key_of("ixbet"))
        self.assertEqual(text.key_of("Real  Money"), "real money")


# ------------------------------------------------------------------ the rules in services.py


class ForumTestCase(TestCase):
    def setUp(self):
        self.now = NOW
        self.competition = Competition.objects.get(code="PL")
        self.season = Season.objects.create(
            competition=self.competition, provider_id=1, start_date=date(2026, 8, 1), end_date=date(2027, 5, 30),
            is_current=True,
        )
        self.arsenal = Team.objects.create(provider_id=1, name="Arsenal", tla="ARS")
        self.chelsea = Team.objects.create(provider_id=2, name="Chelsea", tla="CHE")
        for team in (self.arsenal, self.chelsea):
            team.competitions.add(self.competition)
        services.ensure_forums()
        self.match = self.make_match(1, self.arsenal, self.chelsea, days=1)
        self.user = self.player("gunner")
        self.other = self.player("kite")

    def player(self, name, display_name=None):
        return User.objects.create_user(username=f"{name}@lumora.dev", email=f"{name}@lumora.dev", display_name=name if display_name is None else display_name)

    def make_match(self, provider_id, home, away, days=1, status=Match.Status.SCHEDULED):
        return Match.objects.create(
            provider_id=provider_id, competition=self.competition, season=self.season, home=home, away=away,
            kickoff=self.now + timedelta(days=days), status=status, provider_status="TIMED",
        )

    def at(self, seconds=0):
        return self.now + timedelta(seconds=seconds)

    def topic(self, user=None, seconds=0, **kwargs):
        kwargs.setdefault("title", "Who starts?")
        kwargs.setdefault("tag", "match_talk")
        kwargs.setdefault("body", "The big question.")
        return services.create_topic(user or self.user, self.arsenal.id, now=self.at(seconds), **kwargs)

    def reply(self, topic, user=None, seconds=0, body="I agree.", **kwargs):
        return services.create_post(user or self.user, topic.id, body, now=self.at(seconds), **kwargs)

    def refused(self, call):
        with self.assertRaises(CodedError) as caught:
            call()
        return code_of(caught)


class ForumCreationTests(ForumTestCase):
    def test_every_club_of_an_active_competition_has_one_forum(self):
        self.assertEqual(Forum.objects.count(), 2)
        self.assertEqual({forum.team_id for forum in Forum.objects.all()}, {self.arsenal.id, self.chelsea.id})

    def test_running_it_again_creates_no_duplicates(self):
        services.ensure_forums()
        services.ensure_forums()
        self.assertEqual(Forum.objects.count(), 2)

    def test_a_new_club_gets_its_forum_and_old_forums_stay(self):
        before = list(Forum.objects.values_list("pk", flat=True).order_by("pk"))
        spurs = Team.objects.create(provider_id=3, name="Spurs")
        spurs.competitions.add(self.competition)
        services.ensure_forums()
        self.assertEqual(Forum.objects.count(), 3)
        self.assertEqual(list(Forum.objects.filter(pk__in=before).values_list("pk", flat=True).order_by("pk")), before)

    def test_a_club_of_no_active_competition_has_no_forum(self):
        loner = Team.objects.create(provider_id=9, name="Loner")
        services.ensure_forums()
        self.assertFalse(Forum.objects.filter(team=loner).exists())
        self.competition.is_active = False
        self.competition.save()
        late = Team.objects.create(provider_id=10, name="Late")
        late.competitions.add(self.competition)
        services.ensure_forums()
        self.assertFalse(Forum.objects.filter(team=late).exists())

    def test_the_football_sync_creates_forums_for_new_clubs(self):
        from sports.services import after_sync

        spurs = Team.objects.create(provider_id=3, name="Spurs")
        spurs.competitions.add(self.competition)
        after_sync(self.now)
        self.assertTrue(Forum.objects.filter(team=spurs).exists())


class PostRuleTests(ForumTestCase):
    def test_a_topic_comes_with_its_opening_post(self):
        topic = self.topic()
        self.assertEqual((topic.post_count, topic.posts.count()), (1, 1))
        self.assertEqual(topic.posts.get().body, "The big question.")
        self.assertEqual(topic.last_post_at, self.now)

    def test_the_30_second_rule_at_its_edge(self):
        topic = self.topic()
        self.assertEqual(self.refused(lambda: self.reply(topic, seconds=29)), "post_too_fast")
        self.assertEqual(self.refused(lambda: self.reply(topic, seconds=1)), "post_too_fast")
        self.reply(topic, seconds=30)  # exactly 30 s later is fine
        self.assertEqual(topic.posts.count(), 2)

    def test_the_30_seconds_are_per_player_across_topics(self):
        self.topic()  # the player posts at 0 s in one topic ...
        theirs = self.topic(user=self.other, seconds=1, title="Other")
        self.assertEqual(self.refused(lambda: self.reply(theirs, seconds=5)), "post_too_fast")  # ... and is slow in another
        self.reply(theirs, seconds=31)
        self.assertEqual(theirs.posts.count(), 2)

    def test_the_other_player_is_not_slowed_by_the_first(self):
        topic = self.topic()
        self.reply(topic, user=self.other, seconds=1)  # a different player, one second later
        self.assertEqual(topic.posts.count(), 2)

    def test_ten_topics_a_day_the_eleventh_is_refused(self):
        for index in range(10):
            self.topic(seconds=index * 31, title=f"Topic {index}")
        self.assertEqual(Topic.objects.filter(author=self.user).count(), 10)
        self.assertEqual(self.refused(lambda: self.topic(seconds=10 * 31, title="Eleventh")), "too_many_topics")

    def test_the_topic_window_is_a_rolling_24_hours(self):
        for index in range(10):
            self.topic(seconds=index * 31, title=f"Topic {index}")
        later = 24 * 3600 + 5  # the first topics are more than a day old
        self.topic(seconds=later, title="Next day")
        self.assertEqual(Topic.objects.filter(author=self.user).count(), 11)

    def test_a_reply_does_not_count_as_a_topic(self):
        topic = self.topic()
        for index in range(1, 15):
            self.reply(topic, seconds=index * 31)
        self.topic(seconds=15 * 31, title="Another")

    def test_length_2000_is_fine_2001_is_not(self):
        topic = self.topic()
        self.reply(topic, seconds=31, body="x" * 2000)
        self.assertEqual(self.refused(lambda: self.reply(topic, seconds=62, body="x" * 2001)), "post_too_long")
        self.reply(topic, seconds=93, body="ա" * 2000)  # Armenian letters count one each
        self.assertEqual(self.refused(lambda: self.reply(topic, seconds=124, body="ա" * 2001)), "post_too_long")

    def test_length_is_counted_after_trimming(self):
        topic = self.topic()
        self.reply(topic, seconds=31, body="   " + "x" * 2000 + "\n\n   ")
        self.assertEqual(topic.posts.order_by("-id").first().body, "x" * 2000)

    def test_an_empty_or_blank_post_is_refused(self):
        topic = self.topic()
        for body in ["", "   ", "\n\n", "​​"]:
            with self.subTest(body=body):
                self.assertEqual(self.refused(lambda: self.reply(topic, seconds=31, body=body)), "post_empty")

    def test_title_limits(self):
        for title in ["", "   ", "x" * 121]:
            with self.subTest(title=title):
                self.assertEqual(self.refused(lambda: self.topic(title=title)), "title_invalid")
        self.topic(title="x" * 120)

    def test_links_are_refused_in_posts_and_titles(self):
        topic = self.topic()
        self.assertEqual(self.refused(lambda: self.reply(topic, seconds=31, body="see https://example.com")), "post_has_link")
        self.assertEqual(self.refused(lambda: self.topic(seconds=40, title="visit example.com")), "post_has_link")

    def test_an_unknown_tag_forum_or_topic(self):
        self.assertEqual(self.refused(lambda: self.topic(tag="gossip")), "invalid_tag")
        self.assertEqual(self.refused(lambda: services.create_topic(self.user, 999999, "T", "tactics", "B", now=self.now)), "forum_not_found")
        self.assertEqual(self.refused(lambda: services.create_post(self.user, 999999, "B", now=self.now)), "topic_not_found")

    def test_a_refused_post_leaves_nothing_behind(self):
        topic = self.topic()
        self.refused(lambda: self.reply(topic, seconds=1))
        topic.refresh_from_db()
        self.assertEqual((topic.post_count, topic.posts.count()), (1, 1))

    def test_a_reply_updates_the_topic(self):
        topic = self.topic()
        self.reply(topic, user=self.other, seconds=60)
        topic.refresh_from_db()
        self.assertEqual((topic.post_count, topic.last_post_at), (2, self.at(60)))


class BannedWordServiceTests(ForumTestCase):
    def setUp(self):
        super().setUp()
        BannedWord.objects.create(lang="en", word="numpty")
        BannedWord.objects.create(lang="ru", word="балбес", inside_words=True)
        BannedWord.objects.create(lang="am", word="անխելք", inside_words=True)

    def test_every_language_list_applies_to_every_post(self):
        topic = self.topic()
        for index, body in enumerate(["you numpty", "ты БАЛБЕСы", "դու անխելք ես", "n.u.m.p.t.y", "numрty"], start=1):
            with self.subTest(body=body):
                self.assertEqual(self.refused(lambda: self.reply(topic, seconds=31 * index, body=body)), "post_banned_word")

    def test_titles_are_checked_too(self):
        self.assertEqual(self.refused(lambda: self.topic(title="Numpty referee")), "post_banned_word")

    def test_a_clean_post_passes_and_the_word_is_not_echoed(self):
        topic = self.topic()
        self.reply(topic, seconds=31, body="Numptyland is not a word we ban, a great pass")
        with self.assertRaises(CodedError) as caught:
            self.reply(topic, seconds=62, body="numpty")
        self.assertNotIn("numpty", str(caught.exception.detail))

    def test_an_entry_added_in_the_admin_is_folded_when_saved(self):
        word = BannedWord.objects.create(lang="en", word="SCAM")
        self.assertEqual(word.key, "scam")
        self.assertEqual(self.refused(lambda: self.topic(title="Total $cam")), "post_banned_word")


class DisplayNameTests(ForumTestCase):
    def test_a_player_without_a_display_name_cannot_post(self):
        nameless = self.player("nameless", display_name="")
        self.assertEqual(self.refused(lambda: self.topic(user=nameless)), "display_name_required")
        self.assertEqual(self.refused(lambda: self.reply(self.topic(), user=nameless, seconds=40)), "display_name_required")

    def test_a_name_with_an_email_a_link_or_a_banned_word_is_refused(self):
        BannedWord.objects.create(lang="en", word="numpty")
        for name in ["me@lumora.dev", "visit example.com", "Big Numpty"]:
            with self.subTest(name=name):
                bad = self.player(f"p{abs(hash(name))}", display_name=name)
                self.assertEqual(self.refused(lambda: self.topic(user=bad)), "display_name_invalid")


class BanLockHideTests(ForumTestCase):
    def test_a_banned_player_cannot_post_topic_like_or_report(self):
        topic = self.topic(user=self.other)
        post = topic.posts.get()
        ForumBan.objects.create(user=self.user, until=self.at(3600))
        self.assertEqual(self.refused(lambda: self.topic(seconds=40, title="New")), "forum_banned")
        self.assertEqual(self.refused(lambda: self.reply(topic, seconds=40)), "forum_banned")
        self.assertEqual(self.refused(lambda: services.like_post(self.user, post.id, now=self.at(40))), "forum_banned")
        self.assertEqual(self.refused(lambda: services.report_post(self.user, post.id, "spam_ads", now=self.at(40))), "forum_banned")

    def test_the_ban_message_has_the_date(self):
        ForumBan.objects.create(user=self.user, until=self.at(3600))
        with self.assertRaises(CodedError) as caught:
            self.topic(seconds=5)
        self.assertEqual(caught.exception.params["until"], "2026-11-07 13:00 UTC")

    def test_a_ban_ends_on_its_date(self):
        ForumBan.objects.create(user=self.user, until=self.at(3600))
        self.assertEqual(self.refused(lambda: self.topic(seconds=3599)), "forum_banned")
        self.topic(seconds=3601)

    def test_only_the_banned_player_is_stopped(self):
        ForumBan.objects.create(user=self.user, until=self.at(3600))
        self.topic(user=self.other, seconds=5)

    def test_a_locked_topic_refuses_posts(self):
        topic = self.topic()
        Topic.objects.filter(pk=topic.pk).update(is_locked=True)
        self.assertEqual(self.refused(lambda: self.reply(topic, user=self.other, seconds=60)), "topic_locked")
        Topic.objects.filter(pk=topic.pk).update(is_locked=False)
        self.reply(topic, user=self.other, seconds=61)

    def test_hiding_a_post_closes_its_reports_and_unhiding_restores_it(self):
        topic = self.topic()
        post = self.reply(topic, user=self.other, seconds=40)
        services.report_post(self.user, post.id, "insult_hate", now=self.at(50))
        moderator = self.player("mod")
        services.hide_post(post, "insult_hate", moderator, now=self.at(60))
        post.refresh_from_db()
        self.assertEqual((post.is_hidden, post.hidden_rule, post.hidden_by), (True, "insult_hate", moderator))
        self.assertEqual(PostReport.objects.get().status, "actioned")
        services.unhide_post(post)
        post.refresh_from_db()
        self.assertEqual((post.is_hidden, post.hidden_rule, post.hidden_by), (False, "", None))

    def test_a_hidden_post_cannot_be_liked_or_reported(self):
        post = self.topic().posts.get()
        services.hide_post(post, "spam_ads", self.player("mod"), now=self.now)
        self.assertEqual(self.refused(lambda: services.like_post(self.other, post.id, now=self.at(5))), "post_hidden")
        self.assertEqual(self.refused(lambda: services.report_post(self.other, post.id, "other", now=self.at(5))), "post_hidden")

    def test_dismissing_reports(self):
        post = self.topic().posts.get()
        services.report_post(self.other, post.id, "other", now=self.at(5))
        services.dismiss_reports(post)
        self.assertEqual(PostReport.objects.get().status, "dismissed")

    def test_ban_player_sets_the_date(self):
        ban = services.ban_player(self.user, self.other, now=self.now)
        self.assertEqual(ban.until, self.now + timedelta(days=7))


class LikeReportViewTests(ForumTestCase):
    def test_a_like_is_unique_and_repeating_it_changes_nothing(self):
        post = self.topic().posts.get()
        services.like_post(self.other, post.id, now=self.at(5))
        services.like_post(self.other, post.id, now=self.at(6))
        self.assertEqual(PostLike.objects.filter(post=post).count(), 1)
        services.like_post(self.user, post.id, now=self.at(7))
        self.assertEqual(PostLike.objects.filter(post=post).count(), 2)

    def test_unliking_is_idempotent(self):
        post = self.topic().posts.get()
        services.like_post(self.other, post.id, now=self.at(5))
        services.unlike_post(self.other, post.id)
        services.unlike_post(self.other, post.id)
        self.assertEqual(PostLike.objects.count(), 0)

    def test_liking_a_missing_post(self):
        self.assertEqual(self.refused(lambda: services.like_post(self.user, 999999, now=self.now)), "post_not_found")

    def test_one_report_per_player_and_post(self):
        post = self.topic().posts.get()
        services.report_post(self.other, post.id, "spam_ads", now=self.at(5))
        self.assertEqual(self.refused(lambda: services.report_post(self.other, post.id, "other", now=self.at(6))), "already_reported")
        self.assertEqual(PostReport.objects.count(), 1)

    def test_you_cannot_report_yourself_or_use_an_unknown_reason(self):
        post = self.topic().posts.get()
        self.assertEqual(self.refused(lambda: services.report_post(self.user, post.id, "spam_ads", now=self.at(5))), "own_post_report")
        self.assertEqual(self.refused(lambda: services.report_post(self.other, post.id, "boring", now=self.at(5))), "invalid_report_reason")

    def test_a_view_is_counted_once_per_player(self):
        topic = self.topic()
        for _ in range(3):
            services.record_view(self.other, topic)
        services.record_view(self.user, topic)
        self.assertEqual(TopicView.objects.filter(topic=topic).count(), 2)


class PredictionAndBadgeTests(ForumTestCase):
    def test_a_prediction_is_attached_only_when_asked_and_only_the_authors_own(self):
        Prediction.objects.create(user=self.user, match=self.match, home_goals=2, away_goals=1)
        plain = self.topic(match_id=self.match.id)
        self.assertIsNone(plain.posts.get().prediction)
        topic = self.topic(seconds=40, title="With", match_id=self.match.id, attach_prediction=True)
        self.assertEqual(topic.posts.get().prediction.home_goals, 2)
        self.assertEqual(self.refused(lambda: self.reply(topic, user=self.other, seconds=80, attach_prediction=True)), "no_prediction")

    def test_attaching_without_a_match_is_refused(self):
        self.assertEqual(self.refused(lambda: self.topic(attach_prediction=True)), "no_prediction")

    def test_a_topic_match_must_be_the_clubs_own(self):
        spurs = Team.objects.create(provider_id=3, name="Spurs")
        foreign = self.make_match(2, spurs, self.chelsea)
        self.assertEqual(self.refused(lambda: self.topic(match_id=foreign.id)), "invalid_match")

    def test_the_top_three_predictors_of_the_league_get_the_badge(self):
        finished = self.make_match(3, self.arsenal, self.chelsea, days=-1, status=Match.Status.FINISHED)
        Match.objects.filter(pk=finished.pk).update(home_score=1, away_score=0, home_regular=1, away_regular=0)
        Prediction.objects.create(user=self.user, match=finished, home_goals=1, away_goals=0)
        Prediction.objects.create(user=self.other, match=finished, home_goals=0, away_goals=3)
        predictions.score_predictions(self.now)
        forum = Forum.objects.get(team=self.arsenal)
        self.assertEqual(services.top_predictor_ids(forum), {self.user.id, self.other.id})


# ------------------------------------------------------------------ the API


class ForumApiTests(ForumTestCase):
    @classmethod
    def setUpTestData(cls):
        load_sample(read_sample())

    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        patcher = mock.patch.object(services, "POST_INTERVAL_SECONDS", 0)
        patcher.start()
        self.addCleanup(patcher.stop)

    def new_topic(self, **extra):
        body = {"forum": self.arsenal.id, "title": "Who starts?", "tag": "match_talk", "body": "The big question."}
        return self.api.post("/api/topics", {**body, **extra}, format="json")

    def test_everything_needs_a_player_except_the_labels(self):
        anonymous = APIClient()
        for path in ("/api/forums", f"/api/topics?forum={self.arsenal.id}", "/api/posts?topic=1", "/api/topics/1"):
            with self.subTest(path=path):
                self.assertEqual(anonymous.get(path).status_code, 401)
        for path, body in (("/api/topics", {}), ("/api/posts", {}), ("/api/post_reports", {})):
            with self.subTest(path=path):
                self.assertEqual(anonymous.post(path, body, format="json").status_code, 401)
        self.assertEqual(anonymous.get("/api/forum_labels?lang=en").status_code, 200)

    def test_the_clubs_with_their_counts(self):
        self.new_topic()
        rows = self.api.get("/api/forums").json()
        arsenal = next(row for row in rows if row["id"] == self.arsenal.id)
        self.assertEqual((arsenal["topics"], arsenal["posts"], arsenal["competition"]), (1, 1, "PL"))
        self.assertEqual(arsenal["team"]["tla"], "ARS")
        self.assertEqual(self.api.get(f"/api/forums/{self.arsenal.id}").json()["id"], self.arsenal.id)
        self.assertEqual(self.api.get("/api/forums?competition=SA").json(), [])

    def test_creating_and_reading_a_topic(self):
        response = self.new_topic()
        self.assertEqual(response.status_code, 201)
        topic = response.json()
        self.assertEqual((topic["title"], topic["tag"], topic["replies"], topic["author"]["name"]), ("Who starts?", "match_talk", 0, "gunner"))
        rows = self.api.get(f"/api/topics?forum={self.arsenal.id}").json()
        self.assertEqual([row["id"] for row in rows], [topic["id"]])
        posts = self.api.get(f"/api/posts?topic={topic['id']}").json()
        self.assertEqual((len(posts), posts[0]["body"], posts[0]["is_author"], posts[0]["is_mine"]), (1, "The big question.", True, True))

    def test_replying_liking_and_the_counts(self):
        topic = self.new_topic().json()
        reply = self.api.post("/api/posts", {"topic": topic["id"], "body": "Agreed."}, format="json")
        self.assertEqual(reply.status_code, 201)
        post_id = reply.json()["id"]
        liked = self.api.post(f"/api/posts/{post_id}/like").json()
        self.assertEqual((liked["likes"], liked["liked_by_me"]), (1, True))
        self.assertEqual(self.api.post(f"/api/posts/{post_id}/like").json()["likes"], 1)
        unliked = self.api.delete(f"/api/posts/{post_id}/like").json()
        self.assertEqual((unliked["likes"], unliked["liked_by_me"]), (0, False))
        detail = self.api.get(f"/api/topics/{topic['id']}").json()
        self.assertEqual((detail["replies"], detail["views"]), (1, 1))
        self.api.get(f"/api/topics/{topic['id']}")
        self.assertEqual(self.api.get(f"/api/topics/{topic['id']}").json()["views"], 1)

    def test_a_hidden_post_has_no_text_and_a_rule(self):
        topic = self.new_topic().json()
        post = Post.objects.get(topic_id=topic["id"])
        services.hide_post(post, "insult_hate", self.other, now=NOW)
        row = self.api.get(f"/api/posts?topic={topic['id']}").json()[0]
        self.assertEqual((row["hidden"], row["hidden_rule"], row["body"]), (True, "insult_hate", None))
        self.assertNotIn("The big question", self.api.get(f"/api/posts?topic={topic['id']}").content.decode())

    def test_the_email_never_leaves_the_server(self):
        topic = self.new_topic().json()
        self.api.post("/api/posts", {"topic": topic["id"], "body": "hi"}, format="json")
        for path in ("/api/forums", f"/api/topics?forum={self.arsenal.id}", f"/api/topics/{topic['id']}", f"/api/posts?topic={topic['id']}"):
            with self.subTest(path=path):
                self.assertNotIn("lumora.dev", self.api.get(path).content.decode())
                self.assertNotIn("gunner@", self.api.get(path).content.decode())

    def test_player_text_is_stored_and_returned_exactly_as_plain_text(self):
        evil = '<script>alert(1)</script> <img src=x onerror=alert(2)> & "quotes" \'single\''
        topic = self.new_topic(title="<b>bold</b>", body=evil).json()
        self.assertEqual(topic["title"], "<b>bold</b>")
        self.assertEqual(self.api.get(f"/api/posts?topic={topic['id']}").json()[0]["body"], evil)
        self.assertEqual(self.api.get(f"/api/posts?topic={topic['id']}")["Content-Type"], "application/json")

    def test_refusals_have_a_code_and_a_text_in_every_language(self):
        topic = self.new_topic().json()
        cases = [
            ("/api/posts", {"topic": topic["id"], "body": "see https://example.com"}, "post_has_link"),
            ("/api/posts", {"topic": topic["id"], "body": "   "}, "post_empty"),
            ("/api/posts", {"topic": topic["id"], "body": "x" * 2001}, "post_too_long"),
            ("/api/posts", {"topic": topic["id"], "body": "win real money"}, "post_banned_word"),
            ("/api/topics", {"forum": self.arsenal.id, "title": "", "tag": "tactics", "body": "x"}, "title_invalid"),
            ("/api/topics", {"forum": self.arsenal.id, "title": "T", "tag": "nope", "body": "x"}, "invalid_tag"),
            ("/api/post_reports", {"post": 999999, "reason": "other"}, "post_not_found"),
        ]
        for lang in ("en", "am", "ru"):
            self.api.cookies["lang"] = lang
            for path, body, code in cases:
                with self.subTest(lang=lang, code=code):
                    response = self.api.post(path, body, format="json")
                    self.assertEqual(response.json()["code"], code)
                    self.assertTrue(response.json()["detail"])
                    self.assertNotIn("{", response.json()["detail"])
        self.api.cookies["lang"] = "en"
        response = self.api.post("/api/posts", {"topic": topic["id"], "body": "x" * 2001}, format="json")
        self.assertEqual(response.json()["detail"], "A post can have at most 2000 characters.")

    def test_the_starter_banned_list_comes_from_a_migration_and_is_not_public(self):
        for lang, word in (("en", "1xbet"), ("ru", "промокод"), ("am", "ապուշ")):
            self.assertTrue(BannedWord.objects.filter(lang=lang, word=word).exists(), (lang, word))
        self.assertEqual(self.api.get("/api/banned_words").status_code, 404)  # a public list would teach the bypasses
        self.assertNotIn("banned_words", read_sample())

    def test_the_30_second_rule_over_the_api(self):
        topic = self.new_topic().json()
        with mock.patch.object(services, "POST_INTERVAL_SECONDS", 30):
            response = self.api.post("/api/posts", {"topic": topic["id"], "body": "too soon"}, format="json")
        self.assertEqual((response.status_code, response.json()["code"]), (400, "post_too_fast"))
        self.assertIn("30", response.json()["detail"])

    def test_a_ban_over_the_api_shows_the_date(self):
        ForumBan.objects.create(user=self.user, until=NOW + timedelta(days=400))
        response = self.new_topic()
        self.assertEqual(response.json()["code"], "forum_banned")
        self.assertIn("UTC", response.json()["detail"])

    def test_reporting(self):
        topic = self.new_topic().json()
        post = Post.objects.get(topic_id=topic["id"])
        other = APIClient()
        other.force_authenticate(self.other)
        response = other.post("/api/post_reports", {"post": post.id, "reason": "spam_ads"}, format="json")
        self.assertEqual((response.status_code, PostReport.objects.count()), (201, 1))
        self.assertEqual(other.post("/api/post_reports", {"post": post.id, "reason": "other"}, format="json").json()["code"], "already_reported")
        self.assertEqual(self.api.post("/api/post_reports", {"post": post.id, "reason": "other"}, format="json").json()["code"], "own_post_report")

    def test_topics_pinned_first_filters_and_sorts(self):
        first = self.new_topic(title="First", tag="tactics").json()
        second = self.new_topic(title="Second", tag="transfers").json()
        self.reply_api(second["id"])
        Topic.objects.filter(pk=first["id"]).update(is_pinned=True)
        rows = self.api.get(f"/api/topics?forum={self.arsenal.id}").json()
        self.assertEqual([row["title"] for row in rows], ["First", "Second"])  # pinned first
        self.assertEqual([row["title"] for row in self.api.get(f"/api/topics?forum={self.arsenal.id}&tag=transfers").json()], ["Second"])
        self.assertEqual(self.api.get(f"/api/topics?forum={self.arsenal.id}&sort=replies").json()[0]["title"], "First")  # pinned wins
        Topic.objects.filter(pk=first["id"]).update(is_pinned=False)
        self.assertEqual(self.api.get(f"/api/topics?forum={self.arsenal.id}&sort=replies").json()[0]["title"], "Second")
        self.assertEqual(self.api.get(f"/api/topics?forum={self.arsenal.id}&sort=bogus").json(), [])
        self.assertEqual(self.api.get("/api/topics?forum=x").json(), [])
        self.assertEqual(self.api.get("/api/topics").json(), [])

    def reply_api(self, topic_id):
        return self.api.post("/api/posts", {"topic": topic_id, "body": "reply"}, format="json")

    def test_topic_lists_are_limited_to_50_and_page_with_before(self):
        forum = Forum.objects.get(team=self.arsenal)
        Topic.objects.bulk_create(
            Topic(forum=forum, author=self.user, title=f"T{index}", tag="tactics", post_count=1, last_post_at=NOW - timedelta(minutes=index))
            for index in range(55)
        )
        page = self.api.get(f"/api/topics?forum={self.arsenal.id}").json()
        self.assertEqual(len(page), 50)
        last = page[-1]
        cursor = f"{last['last_post_at']}_{last['id']}"
        rest = self.api.get("/api/topics", {"forum": self.arsenal.id, "before": cursor}).json()
        self.assertEqual(len(rest), 5)
        self.assertFalse({row["id"] for row in page} & {row["id"] for row in rest})
        self.assertEqual(self.api.get("/api/topics", {"forum": self.arsenal.id, "before": "junk"}).json(), [])
        self.assertEqual(self.api.get("/api/topics", {"forum": self.arsenal.id, "sort": "views", "before": cursor}).json(), [])

    def test_post_lists_are_limited_to_100_and_page_with_after(self):
        topic = self.new_topic().json()
        row = Topic.objects.get(pk=topic["id"])
        Post.objects.bulk_create(Post(topic=row, author=self.user, body=f"p{index}") for index in range(104))
        page = self.api.get(f"/api/posts?topic={topic['id']}").json()
        self.assertEqual(len(page), 100)
        rest = self.api.get(f"/api/posts?topic={topic['id']}&after={page[-1]['id']}").json()
        self.assertEqual(len(rest), 5)  # the opening post + 104 = 105 in all
        self.assertEqual([r["id"] for r in page + rest], sorted(r["id"] for r in page + rest))
        self.assertEqual(self.api.get(f"/api/posts?topic={topic['id']}&after=x").json(), [])
        self.assertEqual(self.api.get("/api/posts").json(), [])

    def test_the_badge_and_the_attached_prediction_in_the_api(self):
        finished = self.make_match(3, self.arsenal, self.chelsea, days=-1, status=Match.Status.FINISHED)
        Match.objects.filter(pk=finished.pk).update(home_score=2, away_score=1, home_regular=2, away_regular=1)
        Prediction.objects.create(user=self.user, match=finished, home_goals=2, away_goals=1)
        predictions.score_predictions(NOW)
        Prediction.objects.create(user=self.user, match=self.match, home_goals=3, away_goals=0)
        topic = self.new_topic(match=self.match.id, attach_prediction=True).json()
        row = self.api.get(f"/api/posts?topic={topic['id']}").json()[0]
        self.assertTrue(row["top_predictor"])
        self.assertEqual((row["prediction"]["home_goals"], row["prediction"]["away_goals"], row["prediction"]["home"]["tla"]), (3, 0, "ARS"))

    def test_labels_exist_in_every_language_with_the_same_fields(self):
        keys = []
        for lang in ("en", "am", "ru"):
            rows = self.client.get(f"/api/forum_labels?lang={lang}").json()
            self.assertEqual(len(rows), 1)
            self.assertTrue(all(value not in ("", None) for value in rows[0].values()))
            keys.append(set(rows[0]))
        self.assertEqual(keys[0], keys[1])
        self.assertEqual(keys[0], keys[2])

    def test_the_forums_sidebar_item_is_no_longer_soon(self):
        items = self.client.get("/api/sidebar_items?lang=en").json()
        self.assertFalse([item for item in items if item["url"] == "/forums" and item["is_soon"]])
        self.assertTrue([item for item in items if item["url"] == "/forums"])


# ------------------------------------------------------------------ the admin


class ForumAdminTests(ForumTestCase):
    def setUp(self):
        super().setUp()
        self.staff = User.objects.create_user(username="admin@lumora.dev", email="admin@lumora.dev", is_staff=True, is_superuser=True)
        self.client.force_login(self.staff)

    def act(self, model, action, ids):
        return self.client.post(f"/admin/forums/{model}/", {"action": action, "_selected_action": ids}, follow=True)

    def test_moderators_pin_and_lock_topics(self):
        topic = self.topic()
        self.act("topic", "pin", [topic.id])
        self.act("topic", "lock", [topic.id])
        topic.refresh_from_db()
        self.assertEqual((topic.is_pinned, topic.is_locked), (True, True))
        self.act("topic", "unpin", [topic.id])
        self.act("topic", "unlock", [topic.id])
        topic.refresh_from_db()
        self.assertEqual((topic.is_pinned, topic.is_locked), (False, False))

    def test_moderators_hide_and_unhide_posts_with_a_rule(self):
        post = self.topic().posts.get()
        self.act("post", "hide_spam_ads", [post.id])
        post.refresh_from_db()
        self.assertEqual((post.is_hidden, post.hidden_rule, post.hidden_by), (True, "spam_ads", self.staff))
        self.act("post", "unhide", [post.id])
        post.refresh_from_db()
        self.assertFalse(post.is_hidden)

    def test_a_report_can_hide_the_post_or_be_dismissed(self):
        topic = self.topic()
        post = self.reply(topic, user=self.other, seconds=40)
        report = services.report_post(self.user, post.id, "real_money", now=self.at(50))
        self.act("postreport", "hide_post", [report.id])
        post.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual((post.is_hidden, post.hidden_rule, report.status), (True, "real_money", "actioned"))
        other_post = self.reply(topic, user=self.other, seconds=100)
        other_report = services.report_post(self.user, other_post.id, "other", now=self.at(110))
        self.act("postreport", "dismiss", [other_report.id])
        other_report.refresh_from_db()
        self.assertEqual(other_report.status, "dismissed")

    def test_the_ban_action_bans_the_author_for_seven_days(self):
        post = self.topic().posts.get()
        self.act("post", "ban_author", [post.id])
        ban = ForumBan.objects.get(user=self.user)
        self.assertTrue(timedelta(days=6, hours=23) < ban.until - ban.created_at <= timedelta(days=7))
        self.assertEqual(ban.created_by, self.staff)

    def test_a_ban_added_by_hand_records_the_moderator(self):
        response = self.client.post(
            "/admin/forums/forumban/add/",
            {"user": self.user.id, "until_0": "2030-01-01", "until_1": "10:00:00", "reason": "spam"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ForumBan.objects.get().created_by, self.staff)

    def test_posts_cannot_be_added_or_deleted_in_the_admin(self):
        post = self.topic().posts.get()
        self.assertEqual(self.client.get("/admin/forums/post/add/").status_code, 403)
        self.assertEqual(self.client.post(f"/admin/forums/post/{post.id}/delete/", {"post": "yes"}).status_code, 403)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

    def test_the_moderators_group_has_only_forum_permissions(self):
        group = Group.objects.get(name="Forum moderators")
        codenames = set(group.permissions.values_list("content_type__app_label", "codename"))
        self.assertIn(("forums", "change_post"), codenames)
        self.assertTrue(all(app == "forums" for app, _ in codenames))
        self.assertNotIn(("wallet", "change_wallet"), codenames)


# ------------------------------------------------------------------ real parallel requests


class ParallelPostTests(TransactionTestCase):
    """Two requests of one player at the same moment: the player's row is locked, so only one passes."""

    def setUp(self):
        competition, _ = Competition.objects.get_or_create(code="PL", defaults={"name": "Premier League"})
        team = Team.objects.create(provider_id=1, name="Arsenal")
        team.competitions.add(competition)
        services.ensure_forums()
        self.team = team
        self.user = User.objects.create_user(username="p@lumora.dev", email="p@lumora.dev", display_name="player")
        self.topic = services.create_topic(self.user, team.id, "T", "tactics", "first", now=NOW - timedelta(hours=1))

    def slow_race(self):
        """Pause just after the rate check, so a missing lock would let every thread pass it before any posts."""
        original = services.check_rate

        def slow(user, now):
            original(user, now)
            time.sleep(0.3)

        return mock.patch.object(services, "check_rate", slow)

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

    def test_two_posts_at_once_only_one_passes_the_30_second_rule(self):
        with self.slow_race():
            results = self.run_parallel([lambda: services.create_post(self.user, self.topic.id, "a", now=NOW) for _ in range(2)])
        passed = [result for result in results if isinstance(result, Post)]
        refused = [result for result in results if isinstance(result, CodedError)]
        self.assertEqual((len(passed), len(refused)), (1, 1))
        self.assertEqual(refused[0].detail.code, "post_too_fast")
        self.assertEqual(Post.objects.filter(author=self.user).count(), 2)  # the opening post and one reply

    def test_two_posts_at_once_in_different_topics_only_one_passes(self):
        # The topic row is locked too, but two topics do not share a row: only the player's own row does.
        other = services.create_topic(self.user, self.team.id, "Other", "tactics", "first", now=NOW - timedelta(minutes=30))
        with self.slow_race():
            results = self.run_parallel(
                [lambda: services.create_post(self.user, self.topic.id, "a", now=NOW),
                 lambda: services.create_post(self.user, other.id, "b", now=NOW)]
            )
        self.assertEqual(sum(isinstance(result, Post) for result in results), 1)
        self.assertEqual(Post.objects.filter(author=self.user, created_at=NOW).count(), 1)

    def test_many_posts_at_once_still_only_one_passes(self):
        with self.slow_race():
            results = self.run_parallel([lambda: services.create_post(self.user, self.topic.id, "a", now=NOW) for _ in range(6)])
        self.assertEqual(sum(isinstance(result, Post) for result in results), 1)
        self.assertEqual(Post.objects.filter(author=self.user).count(), 2)

    def test_two_topics_at_once_with_nine_already_made_only_one_more_passes(self):
        forum = Forum.objects.get(team=self.team)
        for index in range(8):  # with the topic made in setUp that is 9 in the last 24 hours
            Topic.objects.create(
                forum=forum, author=self.user, title=f"old {index}", tag="tactics", post_count=1,
                last_post_at=NOW - timedelta(hours=2), created_at=NOW - timedelta(hours=2),
            )
        with self.slow_race():
            results = self.run_parallel(
                [lambda: services.create_topic(self.user, self.team.id, "new", "tactics", "x", now=NOW) for _ in range(2)]
            )
        self.assertEqual(sum(isinstance(result, Topic) for result in results), 1)
        refused = [result for result in results if isinstance(result, CodedError)]
        self.assertEqual([result.detail.code for result in refused], [refused[0].detail.code])
        self.assertIn(refused[0].detail.code, ("too_many_topics", "post_too_fast"))
        self.assertEqual(Topic.objects.filter(author=self.user, created_at__gt=NOW - timedelta(hours=24)).count(), 10)

    def test_players_do_not_block_each_other(self):
        other = User.objects.create_user(username="q@lumora.dev", email="q@lumora.dev", display_name="other")
        results = self.run_parallel(
            [lambda: services.create_post(self.user, self.topic.id, "a", now=NOW), lambda: services.create_post(other, self.topic.id, "b", now=NOW)]
        )
        self.assertEqual(sum(isinstance(result, Post) for result in results), 2)
