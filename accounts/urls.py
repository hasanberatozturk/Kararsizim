from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("kayit/", views.RegisterView.as_view(), name="register"),
    path("giris/", views.UserLoginView.as_view(), name="login"),
    path("cikis/", views.UserLogoutView.as_view(), name="logout"),
]
