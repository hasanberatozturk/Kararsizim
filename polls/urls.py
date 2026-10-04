from django.urls import path

from . import views

app_name = "polls"

urlpatterns = [
    path("", views.poll_list, name="list"),
    path("anket/yeni/", views.poll_create, name="create"),
    path("anket/<int:pk>/", views.poll_detail, name="detail"),
    path("anket/<int:pk>/sil/", views.poll_delete, name="delete"),
    path("u/<str:username>/", views.user_polls, name="user_polls"),
]
