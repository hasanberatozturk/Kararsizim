from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

PASSWORD = "x-Strong-pass-1"


class UserModelTests(TestCase):
    def test_email_is_username_field_and_lowercased(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        user = User.objects.create_user(email="Ali@Example.COM", username="ali", password=PASSWORD)
        self.assertEqual(user.email, "ali@example.com")

    def test_login_with_email_is_case_insensitive(self):
        User.objects.create_user(email="ali@example.com", username="ali", password=PASSWORD)
        self.assertIsNotNone(authenticate(username="ALI@example.com", password=PASSWORD))

    def test_username_unique_case_insensitive(self):
        User.objects.create_user(email="a@example.com", username="Ali", password=PASSWORD)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="b@example.com", username="ali", password=PASSWORD)

    def test_email_unique(self):
        User.objects.create_user(email="a@example.com", username="ali", password=PASSWORD)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="a@example.com", username="veli", password=PASSWORD)


class RegisterTests(TestCase):
    url = reverse("accounts:register")

    def register(self, **overrides):
        data = {
            "username": "ali",
            "email": "ali@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return self.client.post(self.url, data, follow=True)

    def test_register_logs_user_in_and_shows_username_only(self):
        response = self.register()
        self.assertRedirects(response, reverse("polls:list"))
        self.assertContains(response, "@ali")
        self.assertNotContains(response, "ali@example.com")
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_email_rejected_case_insensitive(self):
        self.register()
        self.client.logout()
        response = self.register(username="veli", email="ALI@example.com")
        self.assertEqual(User.objects.count(), 1)
        self.assertContains(response, "zaten bir hesap var")

    def test_duplicate_username_rejected_case_insensitive(self):
        self.register()
        self.client.logout()
        response = self.register(username="ALI", email="baska@example.com")
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors.get("username"))

    def test_invalid_username_rejected(self):
        response = self.register(username="a b")
        self.assertEqual(User.objects.count(), 0)
        self.assertTrue(response.context["form"].errors.get("username"))

    def test_password_mismatch_rejected(self):
        response = self.register(password2="baska-parola-2")
        self.assertEqual(User.objects.count(), 0)
        self.assertTrue(response.context["form"].errors.get("password2"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="ali@example.com", username="ali", password=PASSWORD)

    def test_login_with_email(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "ali@example.com", "password": PASSWORD}, follow=True
        )
        self.assertRedirects(response, reverse("polls:list"))
        self.assertContains(response, "@ali")

    def test_login_with_username_is_not_accepted(self):
        response = self.client.post(reverse("accounts:login"), {"username": "ali", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)

    def test_wrong_password_generic_message(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "ali@example.com", "password": "yanlis"}
        )
        self.assertContains(response, "E-posta veya parola hatalı.")

    def test_unknown_email_same_generic_message(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "yok@example.com", "password": PASSWORD}
        )
        self.assertContains(response, "E-posta veya parola hatalı.")

    def test_login_respects_next(self):
        response = self.client.post(
            reverse("accounts:login") + "?next=/admin/",
            {"username": "ali@example.com", "password": PASSWORD, "next": "/admin/"},
        )
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("polls:list"))
        self.assertNotIn("_auth_user_id", self.client.session)


class LoginLockoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="ali@example.com", username="ali", password=PASSWORD)
        self.url = reverse("accounts:login")

    def attempt(self, email, password, ip="203.0.113.7"):
        return self.client.post(
            self.url,
            {"username": email, "password": password},
            headers={"X-Vercel-Forwarded-For": ip},
        )

    def test_locks_out_after_five_failures_even_with_correct_password(self):
        for _ in range(5):
            self.assertEqual(self.attempt("ali@example.com", "yanlis").status_code, 200)
        locked = self.attempt("ali@example.com", PASSWORD)
        self.assertEqual(locked.status_code, 429)
        self.assertContains(locked, "Çok fazla başarısız giriş", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_email_case_does_not_reset_the_counter(self):
        for email in ["ali@example.com", "ALI@example.com", "Ali@Example.com", "ali@example.com", "ALI@EXAMPLE.COM"]:
            self.attempt(email, "yanlis")
        self.assertEqual(self.attempt("aLi@example.com", PASSWORD).status_code, 429)

    def test_other_ip_can_still_log_in(self):
        for _ in range(5):
            self.attempt("ali@example.com", "yanlis")
        response = self.attempt("ali@example.com", PASSWORD, ip="198.51.100.9")
        self.assertEqual(response.status_code, 302)

    def test_success_resets_failure_count(self):
        for _ in range(4):
            self.attempt("ali@example.com", "yanlis")
        self.assertEqual(self.attempt("ali@example.com", PASSWORD).status_code, 302)
        self.client.logout()
        for _ in range(4):
            self.attempt("ali@example.com", "yanlis")
        self.assertEqual(self.attempt("ali@example.com", PASSWORD).status_code, 302)

    def test_admin_login_is_protected_too(self):
        User.objects.create_superuser(email="root@example.com", username="root", password=PASSWORD)
        for _ in range(5):
            self.client.post(
                "/admin/login/",
                {"username": "root@example.com", "password": "yanlis"},
                headers={"X-Vercel-Forwarded-For": "203.0.113.7"},
            )
        response = self.client.post(
            "/admin/login/",
            {"username": "root@example.com", "password": PASSWORD},
            headers={"X-Vercel-Forwarded-For": "203.0.113.7"},
        )
        self.assertEqual(response.status_code, 429)
