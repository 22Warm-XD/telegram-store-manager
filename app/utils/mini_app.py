from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def build_mini_app_url(
    base_url: str | None,
    app_version: str,
    *,
    product_id: int | None = None,
) -> str | None:
    """Build a versioned HTTPS Mini App URL while retaining unrelated query params."""
    if not base_url:
        return None

    parsed = urlparse(base_url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        return None

    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != "v"]
    if product_id is not None:
        query = [(key, value) for key, value in query if key != "product"]
    query.insert(0, ("v", app_version or "dev"))
    if product_id is not None:
        query.append(("product", str(product_id)))

    return urlunparse(parsed._replace(query=urlencode(query)))
