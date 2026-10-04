from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PollForm
from .models import MAX_OPTIONS, MIN_OPTIONS, Poll

User = get_user_model()

PAGE_SIZE = 10


def poll_queryset():
    """Polls with author, options and vote totals loaded without N+1 queries."""
    return (
        Poll.objects.select_related("author")
        .prefetch_related("options")
        .annotate(total_votes=Count("votes", distinct=True))
        .order_by("-created_at", "-id")  # annotate() drops Meta.ordering
    )


def paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("sayfa"))


def poll_list(request):
    sort = "populer" if request.GET.get("sirala") == "populer" else "yeni"
    queryset = poll_queryset()
    if sort == "populer":
        queryset = queryset.order_by("-total_votes", "-created_at", "-id")
    return render(request, "polls/list.html", {"page_obj": paginate(request, queryset), "sort": sort})


def poll_detail(request, pk):
    poll = get_object_or_404(poll_queryset(), pk=pk)
    return render(request, "polls/detail.html", {"poll": poll})


def user_polls(request, username):
    profile = get_object_or_404(User, username__iexact=username)
    queryset = poll_queryset().filter(author=profile)
    return render(
        request, "polls/user_polls.html", {"profile": profile, "page_obj": paginate(request, queryset)}
    )


@login_required
def poll_create(request):
    if request.method == "POST":
        form = PollForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                poll = form.save(author=request.user)
            messages.success(request, "Anketin yayında!")
            return redirect(poll)
        option_values = request.POST.getlist("options")[:MAX_OPTIONS]
    else:
        form = PollForm()
        option_values = []
    option_values += [""] * (MIN_OPTIONS - len(option_values))
    return render(
        request,
        "polls/create.html",
        {"form": form, "option_values": option_values, "min_options": MIN_OPTIONS, "max_options": MAX_OPTIONS},
    )


@login_required
@require_POST
def poll_delete(request, pk):
    poll = get_object_or_404(Poll, pk=pk)
    if poll.author_id != request.user.id:
        raise PermissionDenied
    poll.delete()
    messages.success(request, "Anket silindi.")
    return redirect("polls:list")
