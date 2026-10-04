from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
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
