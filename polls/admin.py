from django.contrib import admin
from django.db.models import Count

from .models import Option, Poll, Vote


class OptionInline(admin.TabularInline):
    model = Option
    extra = 2
    min_num = 2
    max_num = 5


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    inlines = [OptionInline]
    list_display = ("question", "author", "created_at", "is_active", "vote_count")
    list_filter = ("is_active", "created_at")
    search_fields = ("question", "author__username")
    list_select_related = ("author",)
    raw_id_fields = ("author",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(vote_count=Count("votes"))

    @admin.display(description="oy sayısı", ordering="vote_count")
    def vote_count(self, obj):
        return obj.vote_count


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("poll", "option", "user", "voter_key", "created_at")
    list_select_related = ("poll", "option", "user")
    raw_id_fields = ("poll", "option", "user")
