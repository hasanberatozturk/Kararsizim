import json

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import PollForm
from .models import MAX_OPTIONS, MIN_OPTIONS, Option, Poll, Vote
from .utils import decorate_polls, get_voter_key, set_voter_cookie

User = get_user_model()

PAGE_SIZE = 10


def poll_queryset():
    """Polls with author, options (with vote counts) and totals loaded without N+1 queries."""
    return (
        Poll.objects.select_related("author")
        .prefetch_related(Prefetch("options", queryset=Option.objects.annotate(vote_count=Count("votes"))))
        .annotate(total_votes=Count("votes", distinct=True))
        .order_by("-created_at", "-id")  # annotate() drops Meta.ordering
    )


def paginate(request, queryset):
    """Paginate and decorate the page's polls with results and the viewer's vote."""
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("sayfa"))
    decorate_polls(page, get_voter_key(request, create=False))
    return page


def poll_list(request):
    sort = "populer" if request.GET.get("sirala") == "populer" else "yeni"
    queryset = poll_queryset()
    if sort == "populer":
        queryset = queryset.order_by("-total_votes", "-created_at", "-id")
    return render(request, "polls/list.html", {"page_obj": paginate(request, queryset), "sort": sort})


def poll_detail(request, pk):
    poll = get_object_or_404(poll_queryset(), pk=pk)
    decorate_polls([poll], get_voter_key(request, create=False))
    return render(request, "polls/detail.html", {"poll": poll})


def user_polls(request, username):
    profile = get_object_or_404(User, username__iexact=username)
    queryset = poll_queryset().filter(author=profile)
    return render(
        request, "polls/user_polls.html", {"profile": profile, "page_obj": paginate(request, queryset)}
    )


def wants_json(request):
    return (
        request.content_type == "application/json"
        or "application/json" in request.headers.get("Accept", "")
    )


def read_option_id(request):
    if request.content_type == "application/json":
        try:
            raw = json.loads(request.body or b"{}").get("option_id")
        except (ValueError, AttributeError):
            return None
    else:
        raw = request.POST.get("option_id")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@require_POST
def poll_vote(request, pk):
    poll = get_object_or_404(Poll, pk=pk)
    voter_key = get_voter_key(request)
    status, error, voted_option_id = 200, None, None

    option_id = read_option_id(request)
    if not poll.is_active:
        status, error = 403, "Bu anket artık oy kabul etmiyor."
    elif option_id is None or not Option.objects.filter(pk=option_id, poll=poll).exists():
        status, error = 400, "Geçersiz seçenek."
    else:
        try:
            with transaction.atomic():
                Vote.objects.create(
                    poll=poll,
                    option_id=option_id,
                    user=request.user if request.user.is_authenticated else None,
                    voter_key=voter_key,
                )
        except IntegrityError:
            # The unique (poll, voter_key) constraint is the source of truth for double votes.
            status, error = 409, "Bu ankete zaten oy verdin."

    if wants_json(request):
        response = vote_json_response(request, pk, voter_key, status, error)
    else:
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Oyun kaydedildi!")
        next_url = request.POST.get("next", "")
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = poll_detail_url(pk)
        response = redirect(next_url)
    return set_voter_cookie(request, response)


def poll_detail_url(pk):
    return Poll(pk=pk).get_absolute_url()


def vote_json_response(request, pk, voter_key, status, error):
    if status in (400, 403) and not Vote.objects.filter(poll_id=pk, voter_key=voter_key).exists():
        # No results are revealed to someone who hasn't voted.
        return JsonResponse({"ok": False, "error": error}, status=status)

    poll = poll_queryset().get(pk=pk)
    decorate_polls([poll], voter_key)
    payload = {
        "ok": error is None,
        "voted_option_id": poll.voted_option_id,
        "total_votes": poll.total_votes,
        "results": [
            {key: result[key] for key in ("id", "text", "votes", "percent")} for result in poll.results
        ],
        "html": render_to_string("partials/poll_options.html", {"poll": poll}, request=request),
    }
    if error:
        payload["error"] = error
    return JsonResponse(payload, status=status)


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
