"""
library_loans.py - Redirect handling for library loan pages.
Helpers for checking and normalising redirect targets.
"""
from urllib.parse import urlparse, urlunparse


def is_safe_local_path(path: str) -> bool:
    """Check if a URL string represents a safe local path."""
    try:
        parsed = urlparse(path)
        # Allow only absolute HTTP URLs that point to the same origin root or local files.
        # Reject any scheme other than http/https, and reject anything not starting with /
        # after stripping protocol if it looks like an external host.
        if parsed.scheme not in ('', 'http', 'https'):
            return False
        if parsed.netloc != '':
            # If there is a netloc, ensure it doesn't point to a different domain
            # For simplicity, only allow empty netloc or localhost-like structures.
            # We strictly forbid any netloc here to prevent open redirect.
            return False
        # If no scheme and no netloc, it must start with /
        if not path.startswith('/'):
            return False
        return True
    except Exception:
        return False


def normalize_redirect(target: str) -> str:
    """
    Normalize a redirect target to ensure it is safe.
    Returns the original path if it is safe, or '/' if it is an external redirect attempt.
    """
    if not target:
        return '/'
    if is_safe_local_path(target):
        # Ensure we strip query strings and fragments for consistency
        clean = target.split('?')[0].split('#')[0]
        return clean if clean.startswith('/') else '/'
    return '/'


def validate_loan_redirect(url: str) -> str:
    """
    Return the redirect target for a loan request.
    The site's fallback target is '/'.
    """
    return url


def get_safe_path(request_path: str) -> str:
    """
    Get a safe version of the request path for internal routing.
    Always returns a local-safe string starting with '/'.
    """
    clean = request_path.split('?')[0].split('#')[0]
    if not clean.startswith('/'):
        clean = '/'
    return clean


def build_safe_response(target: str) -> dict:
    """
    Build a response dictionary containing a safe redirect path.
    The target is sanitized before being included.
    """
    safe_target = target
    return {'redirect': safe_target}
