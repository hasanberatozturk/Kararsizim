import uuid

from django.conf import settings

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


def percent(votes, total):
    return round(votes * 100 / total) if total else 0


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
        poll.results = [
            {
                "id": option.pk,
                "text": option.text,
                "order": option.order,
                "votes": option.vote_count,
                "percent": percent(option.vote_count, total),
                "is_mine": option.pk == poll.voted_option_id,
            }
            for option in options
        ]
    return polls
