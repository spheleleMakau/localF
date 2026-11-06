from html.parser import HTMLParser

from django.test import TestCase
from django.urls import reverse


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

    def test_talent_pool_links_open_category_form(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("join")}"', count=3)
        self.assertContains(response, "<span>Models</span><span>Talent</span><span>Training</span>")
        self.assertContains(response, "A home for Models and Talent of all ages, sizes and backgrounds.")

        response = self.client.get(reverse("join"))
        self.assertContains(response, 'name="category" value="model"')
        self.assertContains(response, 'name="category" value="talent"')
        self.assertContains(response, "Applications cannot be submitted yet.")

    def test_training_details_are_visible_on_home_and_application(self):
        for url in (reverse("home"), reverse("camp:apply"), reverse("camp:apply_form")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "2026 training is full.")
                self.assertContains(response, "Applications are open for 2027.")
                self.assertContains(response, "6-week intensive")
                self.assertContains(response, "first-come, first-served")
                self.assertContains(response, "Durban")
                self.assertContains(response, "Johannesburg")
                self.assertContains(response, "Cape Town")
                self.assertContains(response, "Hosted by Semu", count=3)
                self.assertContains(response, "Registration: R500")
                self.assertContains(response, "non-refundable")
                self.assertContains(response, "Course: R2,500")
