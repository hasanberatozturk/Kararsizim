from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_email_is_username_field_and_lowercased(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        user = User.objects.create_user(
            email="Ali@Example.COM", username="ali", password="x-Strong-pass-1"
        )
        self.assertEqual(user.email, "ali@example.com")

    def test_login_with_email_is_case_insensitive(self):
        User.objects.create_user(email="ali@example.com", username="ali", password="x-Strong-pass-1")
        user = authenticate(username="ALI@example.com", password="x-Strong-pass-1")
        self.assertIsNotNone(user)

    def test_username_unique_case_insensitive(self):
        User.objects.create_user(email="a@example.com", username="Ali", password="x-Strong-pass-1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="b@example.com", username="ali", password="x-Strong-pass-1")

    def test_email_unique(self):
        User.objects.create_user(email="a@example.com", username="ali", password="x-Strong-pass-1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="a@example.com", username="veli", password="x-Strong-pass-1")
