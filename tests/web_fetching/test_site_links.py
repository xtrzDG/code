"""Which pages of a site a website import reads, and in what order."""

from app.utilities.knowledge.website.site_links import (
    normalize_page_url,
    page_key,
    rank_pages,
    same_site_pages,
    site_host,
)
from app.utilities.knowledge.website.sitemap import read_sitemap, sitemap_address


def test_only_pages_of_the_same_site_are_kept() -> None:
    pages = same_site_pages(
        [
            "https://www.cafe.example/menu#dinner",
            "http://cafe.example/menu",
            "https://cafe.example:443/prices?utm_source=x&size=big",
            "https://other.example/menu",
            "https://shop.cafe.example/",
            "mailto:hi@cafe.example",
            "https://cafe.example/logo.PNG",
            "https://cafe.example/menu.pdf",
            "https://cafe.example/wp-admin/",
            "https://cafe.example/cart",
            "https://user@cafe.example/secret",
            "https://cafe.example:8080/admin-panel",
            "javascript:alert(1)",
            "https://cafe.example/",
        ],
        site="cafe.example",
        already_known=["https://cafe.example/"],
    )

    assert pages == [
        "https://www.cafe.example/menu",
        "https://cafe.example/prices?size=big",
        "https://cafe.example:8080/admin-panel",
    ]


def test_addresses_have_one_spelling() -> None:
    assert normalize_page_url("HTTPS://Cafe.Example:443") == "https://cafe.example/"
    assert normalize_page_url("https://cafe.example:99999/") is None
    assert normalize_page_url("ftp://cafe.example/") is None
    assert page_key("https://www.cafe.example/menu/") == page_key(
        "http://cafe.example/menu"
    )
    assert site_host("https://WWW.Cafe.Example./") == "cafe.example"


def test_useful_and_shallow_pages_come_first() -> None:
    ranked = rank_pages(
        [
            "https://cafe.example/blog/2024/our-new-chef",
            "https://cafe.example/gallery",
            "https://cafe.example/privacy-policy",
            "https://cafe.example/ka/%E1%83%9B%E1%83%94%E1%83%9C%E1%83%98%E1%83%A3",
            "https://cafe.example/about/team/history",
            "https://cafe.example/menu",
            "https://cafe.example/ru/%D1%86%D0%B5%D0%BD%D1%8B",
            "https://cafe.example/vintage-room",
        ]
    )

    assert ranked == [
        "https://cafe.example/menu",
        "https://cafe.example/ka/%E1%83%9B%E1%83%94%E1%83%9C%E1%83%98%E1%83%A3",
        "https://cafe.example/ru/%D1%86%D0%B5%D0%BD%D1%8B",
        "https://cafe.example/about/team/history",
        "https://cafe.example/gallery",
        "https://cafe.example/vintage-room",
        "https://cafe.example/privacy-policy",
        "https://cafe.example/blog/2024/our-new-chef",
    ]


def test_a_sitemap_lists_pages_or_sitemaps() -> None:
    sitemap = read_sitemap(
        """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc> https://cafe.example/menu?a=1&amp;b=2 </loc></url>
          <url><loc>https://cafe.example/contacts</loc></url>
          <url><loc></loc></url>
        </urlset>"""
    )
    index = read_sitemap(
        "<sitemapindex><sitemap><loc>https://cafe.example/pages.xml</loc>"
        "</sitemap></sitemapindex>"
    )

    assert sitemap.pages == [
        "https://cafe.example/menu?a=1&b=2",
        "https://cafe.example/contacts",
    ]
    assert sitemap.sitemaps == []
    assert index.sitemaps == ["https://cafe.example/pages.xml"]
    assert sitemap_address("https://www.cafe.example/ka/menu?x=1") == (
        "https://www.cafe.example/sitemap.xml"
    )


def test_a_hostile_sitemap_is_read_quickly_and_safely() -> None:
    entities = (
        '<!DOCTYPE x [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;">]>'
        "<urlset><url><loc>&b;</loc></url></urlset>"
    )
    unclosed = "<loc>" * 200_000

    assert read_sitemap(entities).pages == ["&b;"]
    assert read_sitemap(unclosed).pages == []
