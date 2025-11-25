from typing import Optional

try:
    from weasyprint import HTML
except Exception:  # pragma: no cover
    HTML = None  # type: ignore


def render_pdf_from_html(html: str, base_url: Optional[str] = None) -> bytes:
    """Render HTML to PDF bytes using WeasyPrint."""
    if HTML is None:
        raise RuntimeError("WeasyPrint is not available; cannot render PDF")
    doc = HTML(string=html, base_url=base_url)
    return doc.write_pdf()
