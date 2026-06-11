from __future__ import annotations

import html
from typing import Any

from .templates import render_static_site_template, static_template_html
from .text import plain_text


def render_page(
    title: str,
    body: str,
    *,
    description: str = "",
    body_class: str = "",
    extra_head: str = "",
    extra_scripts: str = "",
    index_body: bool | None = False,
) -> str:
    if index_body is True:
        main_attr = " data-pagefind-body"
    elif index_body is False:
        main_attr = " data-pagefind-ignore"
    else:
        main_attr = ""
    return render_static_site_template(
        "layout.html",
        {
            "title": title,
            "description": description,
            "body_class": body_class,
            "main_attr_html": static_template_html(main_attr),
            "extra_head_html": static_template_html(extra_head),
            "header_html": static_template_html(site_header()),
            "body_html": static_template_html(body),
            "footer_html": static_template_html(site_footer()),
            "extra_scripts_html": static_template_html(extra_scripts),
        },
    )


def site_header() -> str:
    return render_static_site_template("header.html").strip()


def site_footer() -> str:
    return render_static_site_template("footer.html").strip()


def page_header(
    title: str, subtitle: Any = "", bg: str = "1", *, pagefind_body: bool = False
) -> str:
    subtitle_text = plain_text(subtitle)
    subtitle_html = (
        f'<h3 class="page-header__meta">{html.escape(subtitle_text)}</h3>'
        if subtitle_text
        else ""
    )
    pagefind_attr = " data-pagefind-body" if pagefind_body else ""
    return f'<div class="page-header header-bg-{html.escape(str(bg))}"><div class="row title"><header class="large-12 columns"><h1{pagefind_attr}>{html.escape(plain_text(title))}</h1>{subtitle_html}</header></div></div>'


def feature_block(title: str, content: str, icon: str = "info-circle") -> str:
    return (
        '<section class="feature-block collapsible">'
        '<div class="feature-block__header">'
        f'<h3 class="feature-block__title"><i class="icon-{html.escape(icon)} icon-padded"></i> {title}</h3>'
        "</div>"
        f"{content}"
        "</section>"
    )
