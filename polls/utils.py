import hashlib
import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Vote


def get_voter_key(request, create=True):
    """Return the stable voter key for this request, or None.

    Members: ``u:<id>``. Visitors: ``a:<uuid>`` from a signed HttpOnly cookie.
    With ``create=True`` a missing cookie gets a fresh uuid, which
    ``set_voter_cookie`` must write to the response.
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return f"u:{user.pk}"

    voter_id = request.get_signed_cookie(
        settings.VOTER_COOKIE_NAME, default=None, max_age=settings.VOTER_COOKIE_MAX_AGE
    )
    if voter_id is None:
        if not create:
            return None
        voter_id = request._new_voter_id = uuid.uuid4().hex
    return f"a:{voter_id}"


def set_voter_cookie(request, response):
    voter_id = getattr(request, "_new_voter_id", None)
    if voter_id:
        response.set_signed_cookie(
            settings.VOTER_COOKIE_NAME,
            voter_id,
            max_age=settings.VOTER_COOKIE_MAX_AGE,
            httponly=True,
            samesite="Lax",
            secure=request.is_secure(),
        )
    return response


def get_client_ip(request):
    """Client IP as seen by Vercel; falls back to REMOTE_ADDR (local development)."""
    forwarded = request.META.get("HTTP_X_VERCEL_FORWARDED_FOR", "").split(",")[0].strip()
    return forwarded or request.META.get("REMOTE_ADDR", "")


def get_ip_hash(request):
    """Salted hash of the client IP: lets us rate-limit votes without storing raw IPs."""
    digest = hashlib.sha256(f"{settings.SECRET_KEY}:{get_client_ip(request)}".encode()).hexdigest()
    return digest[:32]


def too_many_votes(poll, ip_hash):
    since = timezone.now() - timedelta(seconds=settings.VOTE_RATE_WINDOW)
    recent = Vote.objects.filter(poll=poll, ip_hash=ip_hash, created_at__gte=since).count()
    return recent >= settings.VOTE_RATE_LIMIT


def percentages(votes):
    """Whole-number percentages that always add up to 100 (largest remainder method)."""
    total = sum(votes)
    if not total:
        return [0] * len(votes)
    raw = [count * 100 / total for count in votes]
    result = [int(value) for value in raw]
    by_remainder = sorted(range(len(raw)), key=lambda i: raw[i] - result[i], reverse=True)
    for index in by_remainder[: 100 - sum(result)]:
        result[index] += 1
    return result


def decorate_polls(polls, voter_key):
    """Attach results and the viewer's own vote to polls (options prefetched with ``vote_count``)."""
    polls = list(polls)
    voted = {}
    if voter_key and polls:
        voted = dict(
            Vote.objects.filter(voter_key=voter_key, poll__in=polls).values_list("poll_id", "option_id")
        )
    for poll in polls:
        options = list(poll.options.all())
        total = sum(option.vote_count for option in options)
        poll.total_votes = total
        poll.voted_option_id = voted.get(poll.pk)
        shares = percentages([option.vote_count for option in options])
        poll.results = [
            {
                "id": option.pk,
                "text": option.text,
                "order": option.order,
                "votes": option.vote_count,
                "percent": share,
                "is_mine": option.pk == poll.voted_option_id,
            }
            for option, share in zip(options, shares)
        ]
    return polls
