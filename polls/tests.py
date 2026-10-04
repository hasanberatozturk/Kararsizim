import json

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from .models import Option, Poll, Vote

User = get_user_model()


class VoteConstraintTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="a@example.com", username="ali", password="x-Strong-pass-1"
        )
        self.poll = Poll.objects.create(author=self.author, question="Sinema mı restoran mı?")
        self.opt1 = Option.objects.create(poll=self.poll, text="Sinema", order=0)
        self.opt2 = Option.objects.create(poll=self.poll, text="Restoran", order=1)

    def test_second_vote_with_same_voter_key_is_rejected(self):
        Vote.objects.create(poll=self.poll, option=self.opt1, voter_key="a:abc")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vote.objects.create(poll=self.poll, option=self.opt2, voter_key="a:abc")
        self.assertEqual(Vote.objects.count(), 1)

    def test_different_voters_can_vote(self):
        Vote.objects.create(poll=self.poll, option=self.opt1, voter_key="a:abc")
        Vote.objects.create(poll=self.poll, option=self.opt1, voter_key="u:1")
        self.assertEqual(Vote.objects.count(), 2)


PASSWORD = "x-Strong-pass-1"


def make_poll(author, question="Sinema mı restoran mı?", options=("Sinema", "Restoran")):
    poll = Poll.objects.create(author=author, question=question)
    for index, text in enumerate(options):
        Option.objects.create(poll=poll, text=text, order=index)
    return poll


class PollCreateTests(TestCase):
    url = "/anket/yeni/"

    def setUp(self):
        self.user = User.objects.create_user(email="ali@example.com", username="ali", password=PASSWORD)

    def post(self, options, question="Bugün ne yapsam?"):
        return self.client.post(self.url, {"question": question, "options": options})

    def test_anonymous_redirected_to_login_with_next(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, "/giris/?next=/anket/yeni/")

    def test_login_then_returns_to_form(self):
        response = self.client.post(
            "/giris/?next=/anket/yeni/",
            {"username": "ali@example.com", "password": PASSWORD, "next": "/anket/yeni/"},
        )
        self.assertRedirects(response, "/anket/yeni/", fetch_redirect_response=False)

    def test_form_opens_with_two_empty_options(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.context["option_values"], ["", ""])

    def test_valid_poll_created_with_ordered_options(self):
        self.client.force_login(self.user)
        response = self.post(["Sinema", " Restoran ", "", "Ev"])
        poll = Poll.objects.get()
        self.assertRedirects(response, poll.get_absolute_url())
        self.assertEqual(poll.author, self.user)
        self.assertEqual(
            list(poll.options.values_list("text", "order")), [("Sinema", 0), ("Restoran", 1), ("Ev", 2)]
        )

    def test_one_option_rejected(self):
        self.client.force_login(self.user)
        response = self.post(["Sinema", "  "])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Poll.objects.count(), 0)

    def test_six_options_rejected(self):
        self.client.force_login(self.user)
        response = self.post(["1", "2", "3", "4", "5", "6"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Poll.objects.count(), 0)

    def test_five_options_accepted(self):
        self.client.force_login(self.user)
        self.post(["1", "2", "3", "4", "5"])
        self.assertEqual(Option.objects.count(), 5)

    def test_duplicate_options_rejected_case_insensitive(self):
        self.client.force_login(self.user)
        self.post(["Sinema", "SINEMA"])
        self.assertEqual(Poll.objects.count(), 0)

    def test_short_question_rejected(self):
        self.client.force_login(self.user)
        self.post(["a", "b"], question="abc")
        self.assertEqual(Poll.objects.count(), 0)

    def test_invalid_submit_keeps_entered_options(self):
        self.client.force_login(self.user)
        response = self.post(["Sinema"])
        self.assertContains(response, 'value="Sinema"')


class PollListTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email="ali@example.com", username="ali", password=PASSWORD)

    def test_empty_state(self):
        self.assertContains(self.client.get("/"), "Henüz hiç anket yok")

    def test_card_shows_username_not_email(self):
        make_poll(self.author)
        response = self.client.get("/")
        self.assertContains(response, "@ali")
        self.assertNotContains(response, "ali@example.com")
        self.assertContains(self.client.get("/anket/1/"), "@ali")
        self.assertNotContains(self.client.get("/u/ali/"), "ali@example.com")

    def test_pagination_ten_per_page(self):
        for i in range(12):
            make_poll(self.author, question=f"Soru numarası {i}")
        self.assertEqual(len(self.client.get("/").context["page_obj"]), 10)
        self.assertEqual(len(self.client.get("/?sayfa=2").context["page_obj"]), 2)

    def test_newest_first_by_default(self):
        first = make_poll(self.author, question="Birinci anket")
        second = make_poll(self.author, question="İkinci anket")
        self.assertEqual(list(self.client.get("/").context["page_obj"]), [second, first])

    def test_popular_sort(self):
        quiet = make_poll(self.author, question="Sessiz anket")
        popular = make_poll(self.author, question="Popüler anket")
        Vote.objects.create(poll=popular, option=popular.options.first(), voter_key="a:1")
        Vote.objects.create(poll=popular, option=popular.options.first(), voter_key="a:2")
        polls = list(self.client.get("/?sirala=populer").context["page_obj"])
        self.assertEqual(polls, [popular, quiet])
        self.assertEqual(polls[0].total_votes, 2)

    def test_list_query_count_is_constant(self):
        for i in range(5):
            make_poll(self.author, question=f"Soru numarası {i}")
        with self.assertNumQueries(3):  # count + polls + options prefetch
            self.client.get("/")

    def test_user_polls_page(self):
        make_poll(self.author)
        other = User.objects.create_user(email="v@example.com", username="veli", password=PASSWORD)
        make_poll(other, question="Veli'nin sorusu")
        response = self.client.get("/u/ALI/")
        self.assertContains(response, "Sinema mı restoran mı?")
        self.assertNotContains(response, "Veli'nin sorusu")
        self.assertEqual(self.client.get("/u/yok/").status_code, 404)


class PollDeleteTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email="ali@example.com", username="ali", password=PASSWORD)
        self.other = User.objects.create_user(email="v@example.com", username="veli", password=PASSWORD)
        self.poll = make_poll(self.author)
        self.url = f"/anket/{self.poll.pk}/sil/"

    def test_owner_can_delete(self):
        self.client.force_login(self.author)
        self.assertRedirects(self.client.post(self.url), "/")
        self.assertEqual(Poll.objects.count(), 0)

    def test_other_user_gets_403(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertEqual(Poll.objects.count(), 1)

    def test_anonymous_redirected_to_login(self):
        self.client.post(self.url)
        self.assertEqual(Poll.objects.count(), 1)

    def test_get_not_allowed(self):
        self.client.force_login(self.author)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(Poll.objects.count(), 1)

    def test_delete_button_only_for_owner(self):
        self.assertNotContains(self.client.get("/"), "/sil/")
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get("/"), "/sil/")
        self.client.force_login(self.author)
        self.assertContains(self.client.get("/"), "/sil/")


class VoteViewTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email="ali@example.com", username="ali", password=PASSWORD)
        self.poll = make_poll(self.author)
        self.opt1, self.opt2 = self.poll.options.all()
        self.url = f"/anket/{self.poll.pk}/oy/"

    def vote_json(self, client, option_id, poll_url=None):
        return client.post(
            poll_url or self.url,
            {"option_id": option_id},
            headers={"Accept": "application/json"},
        )

    def test_anonymous_can_vote_and_gets_contract_response(self):
        response = self.vote_json(self.client, self.opt1.pk)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["voted_option_id"], self.opt1.pk)
        self.assertEqual(data["total_votes"], 1)
        self.assertEqual(
            data["results"],
            [
                {"id": self.opt1.pk, "text": "Sinema", "votes": 1, "percent": 100},
                {"id": self.opt2.pk, "text": "Restoran", "votes": 0, "percent": 0},
            ],
        )
        vote = Vote.objects.get()
        self.assertTrue(vote.voter_key.startswith("a:"))
        self.assertIsNone(vote.user)

    def test_voter_cookie_is_signed_httponly(self):
        response = self.vote_json(self.client, self.opt1.pk)
        cookie = response.cookies["kararsizim_voter"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(int(cookie["max-age"]), 60 * 60 * 24 * 365)
        self.assertIn(":", cookie.value)  # signed value: <uuid>:<timestamp>:<sig>

    def test_anonymous_sees_results_after_reload_and_cannot_revote(self):
        self.vote_json(self.client, self.opt1.pk)
        page = self.client.get(self.poll.get_absolute_url())
        self.assertContains(page, "poll-results")
        self.assertContains(page, "✓")
        self.assertNotContains(page, "vote-form")
        self.assertContains(self.client.get("/"), "poll-results")

        response = self.vote_json(self.client, self.opt2.pk)
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.json()["voted_option_id"], self.opt1.pk)
        self.assertEqual(Vote.objects.count(), 1)

    def test_visitor_without_cookie_sees_buttons(self):
        self.assertContains(self.client.get("/"), "vote-form")

    def test_tampered_cookie_is_ignored(self):
        self.client.cookies["kararsizim_voter"] = "deadbeef:forged:signature"
        self.vote_json(self.client, self.opt1.pk)
        self.assertNotIn("deadbeef", Vote.objects.get().voter_key)

    def test_member_vote_uses_user_key_and_blocks_other_browser(self):
        member = User.objects.create_user(email="v@example.com", username="veli", password=PASSWORD)
        first, second = Client(), Client()
        first.force_login(member)
        second.force_login(member)
        self.assertEqual(self.vote_json(first, self.opt1.pk).status_code, 200)
        vote = Vote.objects.get()
        self.assertEqual(vote.voter_key, f"u:{member.pk}")
        self.assertEqual(vote.user, member)
        self.assertEqual(self.vote_json(second, self.opt2.pk).status_code, 409)
        self.assertContains(second.get("/"), "poll-results")

    def test_owner_can_vote_on_own_poll(self):
        self.client.force_login(self.author)
        self.assertEqual(self.vote_json(self.client, self.opt1.pk).status_code, 200)

    def test_option_from_other_poll_rejected(self):
        other = make_poll(self.author, question="Başka bir anket")
        response = self.vote_json(self.client, other.options.first().pk)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Vote.objects.count(), 0)

    def test_invalid_option_rejected(self):
        for value in ("abc", "", "99999"):
            self.assertEqual(self.vote_json(self.client, value).status_code, 400)

    def test_inactive_poll_returns_403(self):
        Poll.objects.filter(pk=self.poll.pk).update(is_active=False)
        response = self.vote_json(self.client, self.opt1.pk)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Vote.objects.count(), 0)

    def test_json_body_accepted(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"option_id": self.opt2.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Vote.objects.get().option, self.opt2)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.url, {"option_id": self.opt1.pk})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Vote.objects.count(), 0)

    def test_csrf_accepted_with_token_header(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get("/")
        token = page.cookies["csrftoken"].value
        response = client.post(
            self.url,
            {"option_id": self.opt1.pk},
            headers={"X-CSRFToken": token, "Accept": "application/json"},
        )
        self.assertEqual(response.status_code, 200)

    def test_non_js_form_post_redirects_and_shows_results(self):
        response = self.client.post(self.url, {"option_id": self.opt1.pk, "next": "/"}, follow=True)
        self.assertRedirects(response, "/")
        self.assertContains(response, "poll-results")
        self.assertEqual(Vote.objects.count(), 1)

    def test_non_js_double_vote_shows_error_message(self):
        self.client.post(self.url, {"option_id": self.opt1.pk})
        response = self.client.post(self.url, {"option_id": self.opt2.pk}, follow=True)
        self.assertContains(response, "zaten oy verdin")
        self.assertEqual(Vote.objects.count(), 1)

    def test_open_redirect_is_blocked(self):
        response = self.client.post(self.url, {"option_id": self.opt1.pk, "next": "https://evil.example/"})
        self.assertRedirects(response, self.poll.get_absolute_url(), fetch_redirect_response=False)

    def test_percentages_sum_to_about_100(self):
        for i, option in enumerate([self.opt1, self.opt1, self.opt2]):
            Vote.objects.create(poll=self.poll, option=option, voter_key=f"a:{i}")
        data = self.vote_json(self.client, self.opt2.pk).json()
        self.assertEqual(data["total_votes"], 4)
        self.assertEqual(sum(r["percent"] for r in data["results"]), 100)

    def test_voted_state_uses_constant_queries(self):
        for i in range(5):
            make_poll(self.author, question=f"Soru numarası {i}")
        self.vote_json(self.client, self.opt1.pk)
        with self.assertNumQueries(4):  # count + polls + options prefetch + viewer's votes
            self.client.get("/")


class ErrorPageTests(TestCase):
    def test_custom_404_page(self):
        response = self.client.get("/anket/9999/")
        self.assertContains(response, "Aradığın sayfa bulunamadı", status_code=404)

    def test_custom_403_page(self):
        author = User.objects.create_user(email="ali@example.com", username="ali", password=PASSWORD)
        other = User.objects.create_user(email="v@example.com", username="veli", password=PASSWORD)
        poll = make_poll(author)
        self.client.force_login(other)
        response = self.client.post(f"/anket/{poll.pk}/sil/")
        self.assertContains(response, "yetkin yok", status_code=403)

    def test_500_template_is_standalone(self):
        from django.template.loader import render_to_string

        self.assertIn("Bir şeyler ters gitti", render_to_string("500.html"))


class PageMetaTests(TestCase):
    def test_base_has_title_description_favicon(self):
        response = self.client.get("/")
        self.assertContains(response, 'name="description"')
        self.assertContains(response, "favicon.svg")
        self.assertContains(response, "Plus+Jakarta+Sans")
