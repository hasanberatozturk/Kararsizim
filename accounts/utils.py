def axes_username(request, credentials=None):
    """Lowercased login e-mail so that 'ALI@x.com' and 'ali@x.com' share one lockout counter."""
    source = credentials or request.POST
    return (source.get("username") or "").strip().lower()
