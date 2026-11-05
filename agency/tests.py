from html.parser import HTMLParser

from django.test import TestCase


class PageLinksParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.fragment_links = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag == "a":
            href = attributes.get("href", "")
            if href.startswith("#"):
                self.fragment_links.add(href[1:])


class HomePageTests(TestCase):
    def test_homepage_renders_editorial_sections(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REAL PEOPLE.")
        self.assertContains(response, "SUMMER MODELLING ACADEMY")
        self.assertContains(response, "Get Represented")
        self.assertContains(response, "agency/img/founder-portrait.jpg")
        for label in ("Home", "About", "Talent", "Training", "Photography", "Contact"):
            self.assertContains(response, f">{label}</a>")

    def test_homepage_navigation_and_fragment_links_resolve(self):
        response = self.client.get("/")
        parser = PageLinksParser()
        parser.feed(response.content.decode())

        self.assertEqual(parser.fragment_links - parser.ids, set())
