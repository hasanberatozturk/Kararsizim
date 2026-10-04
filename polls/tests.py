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


class HomePageTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("polls:list"))
        self.assertContains(response, "Kararsızım çalışıyor")
