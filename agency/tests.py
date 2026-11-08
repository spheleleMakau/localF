from html.parser import HTMLParser
from decimal import Decimal
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from camp.models import Application
from camp.tests import make_png
from .models import TrainingOrder
from .payfast import signature

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
        self.assertContains(response, "LOCAL FACES")
        self.assertContains(response, "MODELLING ACADEMY")
        self.assertContains(response, "Turn Your Look Into an Opportunity. Turn Your Name Into a Brand.")
        self.assertContains(response, "More Than Modelling. We’re Building Brands.")
        self.assertContains(response, "Your Look. Your Brand. Your Future.")
        self.assertContains(response, "What You’ll Walk Away With")
        self.assertContains(response, "Walk away focused, confident and career-ready")
        self.assertContains(response, "agency/img/walkaway.jpg")
        self.assertNotContains(response, 'class="walkaway"')
        self.assertNotContains(response, "SUMMER MODELLING ACADEMY")
        self.assertContains(response, "Get Represented")
        self.assertContains(response, "agency/img/founder.jpeg")
        self.assertContains(response, "agency/img/founder1.jpeg")
        self.assertContains(response, "agency/img/hero-collage.jpg")
        for label in ("Home", "About", "Talent", "Training", "Contact"):
            self.assertContains(response, f">{label}</a>")

    def test_model_slideshow_has_requested_images(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, " data-model-slide>", count=1)
        self.assertContains(response, " data-model-slide hidden>", count=5)
        self.assertNotContains(response, "data-slideshow-control")
        self.assertNotContains(response, "agency/img/hero-smile.jpg")
        self.assertNotContains(response, "agency/img/hero-profile.jpg")
        self.assertContains(response, f'href="{reverse("models_gallery")}"')
        gallery = self.client.get(reverse("models_gallery"))
        for filename in ("model.jpeg", "model1.jpeg", "model2.jpeg", "model3.jpeg", "model4.jpeg", "model5.jpeg"):
            self.assertContains(response, f"agency/img/{filename}")
            self.assertContains(gallery, f"agency/img/{filename}")

    def test_founder_portfolio_is_accessible_from_home(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("founder_portfolio")}"')
        portfolio = self.client.get(reverse("founder_portfolio"))
        for filename in ("brand.jpeg", "brand1.jpeg", "brand2.jpeg", "brand4.jpeg", "brand5.jpeg", "brand6.jpeg"):
            self.assertContains(portfolio, f"agency/img/{filename}")
        self.assertNotContains(portfolio, "brand3.jpeg")

    def test_content_creator_slideshow_has_requested_images(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("entertainers_gallery")}" aria-label="View the content creators gallery" data-entertainer-slideshow')
        self.assertContains(response, " data-entertainer-slide>", count=1)
        self.assertContains(response, " data-entertainer-slide hidden>", count=2)
        gallery = self.client.get(reverse("entertainers_gallery"))
        self.assertContains(gallery, "Content Creators.")
        for filename in ("e.jpeg", "e1.jpeg", "e2.jpeg"):
            self.assertContains(response, f"agency/img/{filename}")
            self.assertContains(gallery, f"agency/img/{filename}", count=1)

    def test_selfie_example_in_model_and_training_forms(self):
        self.assertContains(self.client.get(reverse("join")), "agency/img/self.jpeg")
        response = self.client.post(reverse("training_shop"), {"training": "course", "term": "1", "city": "Durban"})
        self.assertRedirects(response, reverse("training_application"))
        self.assertContains(self.client.get(reverse("training_application")), "agency/img/self.jpeg")
        response = self.client.post(reverse("training_shop"), {"training": "individual", "term": "1", "city": "Durban", "hours": "1"})
        self.assertRedirects(response, reverse("training_application"))
        self.assertContains(self.client.get(reverse("training_application")), "agency/img/self.jpeg")

    def test_logos_use_talent_agency_branding(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<span class="brand-tagline">Talent Agency</span>', count=3)
        self.assertContains(response, 'aria-label="Local Faces Talent Agency home"', count=2)
        self.assertContains(response, 'aria-label="Local Faces Talent Agency"')
        self.assertNotContains(response, '<span class="brand-tagline">Entertainment')
        self.assertContains(response, "Models of all ages and sizes &amp; Content Creators")
        self.assertContains(response, "Training and Packages Available")
        self.assertContains(response, "Production, Podcast &amp; Content Creation")
        self.assertNotContains(response, "Actors")
        self.assertNotContains(response, "MCs")

    def test_navigation_has_accessible_mobile_menu(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'aria-expanded="false" aria-controls="primary-navigation" data-menu-toggle')
        self.assertContains(response, 'id="primary-navigation" aria-label="Main navigation" data-navigation')
        for label in ("Home", "About", "Talent", "Training", "Cart", "Contact"):
            self.assertContains(response, f">{label}</a>")
        for fragment in ("photography", "entertainment", "merchandise"):
            self.assertNotContains(response, f'href="{reverse("home")}#{fragment}"')
            self.assertContains(response, f'id="{fragment}"')

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
        self.assertContains(response, "MODEL APPLICATION")
        self.assertContains(response, 'name="shoe_size"')
        self.assertContains(response, 'name="dress_size"')
        self.assertContains(response, "Talent applications are coming soon.")

    def test_training_details_are_visible_on_home_and_application(self):
        for url in (reverse("home"), reverse("camp:apply"), reverse("camp:apply_form"), reverse("training_shop")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "December intake fully booked!")
                self.assertContains(response, "Registrations for 2026 are officially closed.")
                self.assertContains(response, "December 2026 Academy Fashion Show &amp; Graduation")
                self.assertContains(response, "R50 per person")
                self.assertContains(response, "Shared upon enquiry")
                self.assertContains(response, 'href="mailto:info@localfaces.co.za"')
                self.assertContains(response, 'href="https://wa.me/27681946795"')
                self.assertContains(response, "2027 registrations now open!")
                self.assertContains(response, "Join Local Faces Modelling Academy in Johannesburg, Durban or Cape Town, hosted by Semu.")
                self.assertContains(response, "Limited spaces! First come, first served. Registration closes once classes are full.")
                self.assertContains(response, "Secure your spot today!")
                self.assertContains(response, "Training is available for 2027")
                self.assertContains(response, "What You’ll Walk Away With", count=1)
                self.assertContains(response, "Walk away focused, confident and career-ready", count=1)
                self.assertContains(response, "agency/img/walkaway.jpg", count=1)
                self.assertContains(response, "6-week intensive")
                self.assertContains(response, "Durban")
                self.assertContains(response, "Johannesburg")
                self.assertContains(response, "Cape Town")
                self.assertContains(response, "Hosted by Semu", count=3)
                self.assertContains(response, "Registration: R500")
                self.assertContains(response, "non-refundable")
                self.assertContains(response, "Course: R2,500")

    def test_training_links_go_to_details_and_shop(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<a class="service" href="#training-fees">')
        self.assertContains(response, '<p class="training-fees" id="training-fees"><strong>Registration: R500</strong>')
        self.assertContains(response, '<div class="academy-details" id="training-information">')
        self.assertContains(response, f'href="{reverse("training_shop")}"')
        self.assertContains(
            response,
            f'href="{reverse("camp:apply")}">Explore training</a>',
        )
        self.assertNotContains(response, "Apply for 2027 training")
        html = response.content.decode()
        self.assertLess(html.index("Learn. Practise. Grow."), html.index("LOCAL FACES<br>"))
        self.assertLess(html.index("Turn Your Look Into an Opportunity. Turn Your Name Into a Brand."), html.index("<h3>Training details</h3>"))
        self.assertLess(html.index("<h3>Training details</h3>"), html.index("December intake fully booked!"))
        self.assertLess(html.index("December intake fully booked!"), html.index("R1,500 per hour"))
        self.assertLess(html.index("R1,500 per hour"), html.index("agency/img/walkaway.jpg"))
        self.assertLess(html.index("agency/img/walkaway.jpg"), html.index("What You’ll Walk Away With"))

    def test_course_topics_appear_on_homepage_and_course_details(self):
        topics = (
            "Runway &amp; Modelling:",
            "Understanding the Industry:",
            "Confidence &amp; Career Longevity:",
            "Personal Branding &amp; Social Media:",
            "Industry Knowledge &amp; Representation",
            "Monetising Your Talent:",
        )
        home = self.client.get(reverse("home"))
        self.assertContains(home, "What the training covers")
        for topic in topics:
            self.assertContains(home, topic, count=1)
        for url in (reverse("camp:apply"), reverse("camp:apply_form"), reverse("training_shop")):
            response = self.client.get(url)
            self.assertContains(response, "What the training covers")
            for topic in topics:
                self.assertContains(response, topic)

    def test_academy_opportunity_is_accessible_from_home(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("academy_opportunity"))
        self.assertContains(response, f'href="{reverse("academy_opportunity")}">Start your academy →</a>')
        response = self.client.get(reverse("academy_opportunity"))
        self.assertContains(response, "agency/img/model4.jpeg")
        self.assertNotContains(response, "agency/img/academy-main.jpg")
        self.assertContains(response, "Three payments.")
        self.assertContains(response, "R5,000.")
        self.assertContains(response, "R1,666.67")
        self.assertContains(response, "R1,666.66")
        self.assertContains(response, "not charged automatically")
        self.assertContains(response, "Payment alone does not guarantee")
        self.assertContains(response, "info@localfaces.co.za")
        self.assertContains(response, "name and surname as the reference")
        self.assertContains(response, 'action="#start"')
        self.assertContains(response, 'name="city"')


@override_settings(
    PAYFAST_MERCHANT_ID="10000100",
    PAYFAST_MERCHANT_KEY="test-key",
    PAYFAST_PASSPHRASE="test passphrase",
    PAYFAST_SITE_URL="https://example.com",
    PAYFAST_SANDBOX=True,
)
class TrainingShopTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        settings_override = override_settings(MEDIA_ROOT=Path(self.media_directory.name))
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def application_data(self, **overrides):
        pending = self.client.session["pending_training"]
        data = {
            "submission_key": pending["submission_key"],
            "full_name": "Alex Example", "email": "alex@example.com",
            "phone": "123456789", "whatsapp_number": "123456789",
            "age": "20", "age_category": "seniors", "gender": "female",
            "city": pending["city"], "town": "Central", "current_occupation": "Student",
            "preferred_days": "Friday", "available_full_five_weeks": "yes",
            "has_modelling_experience": "no", "shoe_size": "6", "pants_size": "32",
            "dress_size": "10", "skirt_size": "10", "top_size": "M",
            "privacy_consent": "on", "photo_consent": "on",
            "headshot": SimpleUploadedFile("headshot.png", make_png(), content_type="image/png"),
            "full_length_photo": SimpleUploadedFile("full.png", make_png(), content_type="image/png"),
        }
        data.update(overrides)
        return data

    def add_item(self, **overrides):
        data = {"training": "course", "term": "2", "city": "Durban", "hours": "1"}
        data.update(overrides)
        response = self.client.post(reverse("training_shop"), data)
        if response.status_code == 302 and response["Location"] == reverse("training_application"):
            return self.client.post(reverse("training_application"), self.application_data())
        return response

    def create_order(self):
        self.add_item()
        self.add_item(training="individual", term="4", city="Johannesburg", hours="2")
        response = self.client.post(reverse("training_checkout"), {
            "first_name": "Alex", "last_name": "Example", "email": "alex@example.com"
        })
        self.assertEqual(response.status_code, 302)
        return TrainingOrder.objects.get()

    def test_academy_purchase_and_mixed_cart_snapshot(self):
        response = self.client.post(reverse("academy_opportunity"), {"city": "  Pretoria  ", "price": "0.01"})
        self.assertRedirects(response, reverse("training_cart"))
        self.add_item()
        cart = self.client.get(reverse("training_cart"))
        self.assertEqual(cart.context["total"], Decimal("2166.67"))
        self.assertContains(cart, "Proposed city: Pretoria")
        self.assertContains(cart, "R1,666.67 in month two and R1,666.66 in month three")
        self.assertNotContains(cart, "Term  · Pretoria")
        response = self.client.post(reverse("training_checkout"))
        order = TrainingOrder.objects.get()
        self.assertEqual(order.total, Decimal("2166.67"))
        self.assertEqual(order.items[0]["training"], "academy")
        self.assertEqual(order.items[0]["city"], "Pretoria")
        self.assertEqual(order.items[0]["subtotal"], "1666.67")
        self.assertEqual(order.items[0]["balance_due"], "3333.33")
        self.assertEqual(order.items[0]["remaining_installments"], ["1666.67", "1666.66"])
        self.assertEqual(order.items[1]["application_number"], Application.objects.get().application_number)
        payment = self.client.get(response["Location"])
        self.assertContains(payment, 'name="amount" value="2166.67"')
        self.assertContains(payment, "month two")
        self.assertContains(payment, "month three")
        self.assertContains(self.client.get(reverse("training_payment_return", args=[order.token])), "month three")

    def test_group_application_is_required_and_records_sizes_and_photos(self):
        response = self.client.post(reverse("training_shop"), {
            "training": "course", "term": "2", "city": "Durban", "hours": "1",
        })
        self.assertRedirects(response, reverse("training_application"))
        self.assertEqual(self.client.get(reverse("training_cart")).context["items"], [])
        self.assertRedirects(self.client.post(reverse("training_checkout")), reverse("training_cart"))
        page = self.client.get(reverse("training_application"))
        self.assertContains(page, 'name="shoe_size"')
        self.assertContains(page, 'name="dress_size"')
        data = self.application_data(dress_size="", skirt_size="")
        data.pop("headshot")
        response = self.client.post(reverse("training_application"), data)
        self.assertFormError(response.context["form"], "headshot", "This field is required.")
        self.assertFormError(response.context["form"], "dress_size", "This field is required.")
        self.assertFalse(Application.objects.exists())
        response = self.client.post(reverse("training_application"), self.application_data())
        self.assertRedirects(response, reverse("training_cart"))
        application = Application.objects.get()
        self.assertEqual(application.kind, Application.Kind.TRAINING)
        self.assertEqual((application.shoe_size, application.dress_size, application.top_size), ("6", "10", "M"))
        self.assertEqual(application.photos.count(), 2)
        self.assertContains(self.client.get(reverse("camp:shared_application", args=[application.share_token])), "Dress size")
        self.assertEqual(self.client.session["training_cart"][0]["application_number"], application.application_number)

    def test_group_application_prefills_city_and_preserves_edited_city(self):
        for city in ("Durban", "Johannesburg", "Cape Town"):
            with self.subTest(city=city):
                self.client.post(reverse("training_shop"), {
                    "training": "course", "term": "2", "city": city,
                })
                response = self.client.get(reverse("training_application"))
                self.assertEqual(response.context["form"]["city"].value(), city)
                self.assertContains(response, f'value="{city}"')

        data = self.application_data(city="Pretoria", dress_size="")
        response = self.client.post(reverse("training_application"), data)
        self.assertFormError(response.context["form"], "dress_size", "This field is required.")
        self.assertEqual(response.context["form"]["city"].value(), "Pretoria")
        response = self.client.post(reverse("training_application"), self.application_data(city="Pretoria"))
        self.assertRedirects(response, reverse("training_cart"))
        self.assertEqual(Application.objects.get().city, "Pretoria")
        self.assertEqual(self.client.session["training_cart"][0]["city"], "Cape Town")

    def test_legacy_group_item_cannot_bypass_application(self):
        session = self.client.session
        session["training_cart"] = [{"training": "course", "city": "Durban", "term": "1", "hours": 1}]
        session.save()
        response = self.client.post(reverse("training_checkout"), follow=True)
        self.assertContains(response, "needs an application")
        self.assertFalse(TrainingOrder.objects.exists())

    def test_one_on_one_requires_talent_style_form_before_checkout(self):
        response = self.client.post(reverse("training_shop"), {
            "training": "individual", "term": "4", "city": "Johannesburg", "hours": "2",
        })
        self.assertRedirects(response, reverse("training_application"))
        self.assertEqual(self.client.get(reverse("training_cart")).context["items"], [])
        page = self.client.get(reverse("training_application"))
        self.assertContains(page, "One-on-one training")
        self.assertNotContains(page, "R500 registration")
        self.assertNotContains(page, 'name="age_category"')
        self.assertNotContains(page, 'name="preferred_days"')
        self.assertNotContains(page, 'name="available_full_five_weeks"')
        self.assertContains(page, 'name="shoe_size"')
        self.assertContains(page, 'name="headshot"')
        self.assertEqual(page.context["form"]["city"].value(), "Johannesburg")

        data = self.application_data(dress_size="", skirt_size="")
        data.pop("headshot")
        data.pop("age_category")
        data.pop("preferred_days")
        data.pop("available_full_five_weeks")
        response = self.client.post(reverse("training_application"), data)
        self.assertFormError(response.context["form"], "headshot", "This field is required.")
        self.assertFormError(response.context["form"], "dress_size", "This field is required.")
        self.assertFalse(Application.objects.exists())

        data = self.application_data()
        for field in ("age_category", "preferred_days", "available_full_five_weeks"):
            data.pop(field)
        self.assertRedirects(self.client.post(reverse("training_application"), data), reverse("training_cart"))
        application = Application.objects.get()
        self.assertEqual(application.kind, Application.Kind.TRAINING)
        self.assertEqual((application.city, application.dress_size, application.photos.count()), ("Johannesburg", "10", 2))
        cart = self.client.get(reverse("training_cart"))
        self.assertContains(cart, application.application_number)
        self.assertEqual(cart.context["total"], Decimal("3000.00"))
        self.client.post(reverse("training_checkout"))
        order = TrainingOrder.objects.get()
        self.assertEqual(order.items[0]["application_number"], application.application_number)
        self.assertEqual(order.total, Decimal("3000.00"))

    def test_legacy_one_on_one_item_cannot_bypass_application(self):
        session = self.client.session
        session["training_cart"] = [{"training": "individual", "city": "Durban", "term": "1", "hours": 1}]
        session.save()
        response = self.client.post(reverse("training_checkout"), follow=True)
        self.assertContains(response, "needs an application")
        self.assertFalse(TrainingOrder.objects.exists())

    def test_group_application_male_and_selection_cannot_be_bypassed(self):
        self.assertRedirects(self.client.get(reverse("training_application")), reverse("training_shop"))
        self.client.post(reverse("training_shop"), {"training": "course", "term": "1", "city": "Durban"})
        response = self.client.post(reverse("training_application"), self.application_data(
            gender="male", dress_size="10", skirt_size="10",
        ))
        self.assertRedirects(response, reverse("training_cart"))
        applicant = Application.objects.get()
        self.assertEqual((applicant.dress_size, applicant.skirt_size), ("", ""))
        applicant.delete()
        response = self.client.post(reverse("training_checkout"), follow=True)
        self.assertContains(response, "needs an application")
        self.assertFalse(TrainingOrder.objects.exists())

    @patch("agency.shop.TrainingApplicationForm.save", side_effect=OSError("Disk unavailable"))
    def test_group_application_storage_failure_does_not_add_to_cart(self, _save):
        self.client.post(reverse("training_shop"), {"training": "course", "term": "1", "city": "Durban"})
        response = self.client.post(reverse("training_application"), self.application_data())
        self.assertContains(response, "couldn&#x27;t save your application")
        self.assertEqual(self.client.session.get("training_cart", []), [])
        self.assertFalse(Application.objects.exists())

    def test_academy_rejects_missing_city_and_cart_limit(self):
        response = self.client.post(reverse("academy_opportunity"), {"city": " "})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "city", "This field is required.")
        self.assertContains(response, "This field is required.")
        session = self.client.session
        session["training_cart"] = [{"training": "course", "city": "Durban", "term": "1", "hours": 1}] * 100
        session.save()
        response = self.client.post(reverse("academy_opportunity"), {"city": "Pretoria"})
        self.assertContains(response, "at most 100 items")
        self.assertEqual(len(self.client.session["training_cart"]), 100)

    def test_cart_totals_and_order_handoff(self):
        self.assertEqual(self.add_item().status_code, 302)
        self.assertEqual(self.add_item(training="individual", term="4", city="Johannesburg", hours="2").status_code, 302)
        response = self.client.get(reverse("training_cart"))
        self.assertEqual(response.context["total"], Decimal("3500.00"))
        self.assertContains(response, "Term 4")
        self.assertContains(response, "remaining R2500.00")
        self.assertContains(response, "proof of payment")
        response = self.client.post(reverse("training_checkout"), {
            "first_name": "Alex", "last_name": "Example", "email": "alex@example.com",
            "total": "0.01",
        })
        order = TrainingOrder.objects.get()
        self.assertRedirects(response, reverse("training_payment", args=[order.token]), fetch_redirect_response=False)
        self.assertEqual(order.total, Decimal("3500.00"))
        self.assertEqual(order.items[0]["subtotal"], "500.00")
        self.assertEqual(order.items[0]["balance_due"], "2500.00")
        self.assertEqual(order.items[0]["city"], "Durban")
        self.assertEqual(order.items[1]["city"], "Johannesburg")
        response = self.client.get(response["Location"])
        self.assertContains(response, "sandbox.payfast.co.za/eng/process")
        self.assertContains(response, 'name="amount" value="3500.00"')
        self.assertContains(response, "data-payfast-handoff")
        self.assertNotContains(response, 'name="name_first"')
        self.assertNotContains(response, 'name="email_address"')
        self.assertContains(response, "proof of payment")
        self.assertContains(response, "remaining R2500.00")
        self.assertContains(self.client.get(reverse("training_payment_return", args=[order.token])), "remaining R2500.00")
        self.assertEqual(self.client.get(reverse("training_cart")).context["items"], [])

    def test_invalid_selection_and_remove(self):
        self.assertEqual(self.add_item(city="Pretoria").status_code, 200)
        for training in ("course", "individual"):
            for city in ("Pretoria", "other"):
                with self.subTest(training=training, city=city):
                    response = self.add_item(training=training, city=city, other_city="Pretoria")
                    self.assertFormError(response.context["form"], "city", "Select a valid choice. %(value)s is not one of the available choices." % {"value": city})
        self.assertEqual(self.add_item(training="individual", hours="0").status_code, 200)
        self.assertEqual(self.add_item(term="5").status_code, 200)
        self.assertEqual(self.client.get(reverse("training_cart")).context["items"], [])
        self.add_item()
        self.client.post(reverse("training_cart_remove", args=[0]))
        self.assertEqual(self.client.get(reverse("training_cart")).context["items"], [])
        self.assertEqual(self.client.post(reverse("training_cart_remove", args=[0])).status_code, 400)

    def test_select_city_and_add_group_course(self):
        response = self.client.get(reverse("training_shop"))
        self.assertContains(response, "Make your selection")
        self.assertContains(response, 'href="#training-information"')
        self.assertContains(response, 'id="training-information"')
        self.assertContains(response, 'data-training-details="course"')
        self.assertContains(response, 'data-training-details="individual"')
        self.assertContains(response, 'data-training-shop')
        self.assertContains(response, 'Group course - R500 non-refundable registration')
        self.assertContains(response, 'Group course: R500 non-refundable registration.')
        self.assertContains(response, '<select name="city"')
        self.assertNotContains(response, '>Other city</option>')
        for city in ("Durban", "Johannesburg", "Cape Town"):
            self.assertContains(response, f'value="{city}"')
            added = self.add_item(city=city, hours="")
            self.assertRedirects(added, reverse("training_cart"))
        cart = self.client.get(reverse("training_cart"))
        self.assertEqual(cart.context["total"], Decimal("1500.00"))
        self.assertEqual([item["city"] for item in cart.context["items"]], ["Durban", "Johannesburg", "Cape Town"])

    def test_outdated_other_city_selection_requires_reselection(self):
        session = self.client.session
        session["pending_training"] = {"training": "individual", "city": "Pretoria", "term": "1", "hours": 1}
        session.save()
        response = self.client.get(reverse("training_application"), follow=True)
        self.assertRedirects(response, reverse("training_shop"))
        self.assertContains(response, "Training is now available only in Durban, Johannesburg and Cape Town.")
        self.assertEqual(self.client.session.get("training_cart", []), [])

    def test_one_on_one_allows_three_cities(self):
        for city in ("Durban", "Johannesburg", "Cape Town"):
            with self.subTest(city=city):
                self.assertRedirects(self.add_item(training="individual", city=city, hours="1"), reverse("training_cart"))
        cart = self.client.get(reverse("training_cart"))
        self.assertEqual([item["city"] for item in cart.context["items"]], ["Durban", "Johannesburg", "Cape Town"])

    def test_registration_only_order_is_r500_and_discloses_balance(self):
        self.add_item(hours="")
        checkout = self.client.get(reverse("training_cart"))
        self.assertContains(checkout, "Total payable now: R500.00")
        self.assertContains(checkout, "remaining R2500.00")
        self.assertContains(checkout, "info@localfaces.co.za")
        self.assertContains(checkout, "name and surname")
        response = self.client.post(reverse("training_checkout"), {
            "first_name": "Alex", "last_name": "Example", "email": "alex@example.com"
        })
        order = TrainingOrder.objects.get()
        self.assertEqual(order.total, Decimal("500.00"))
        payment = self.client.get(response["Location"])
        self.assertContains(payment, 'name="amount" value="500.00"')
        self.assertContains(payment, "remaining R2500.00")

    def test_checkout_needs_no_customer_details_and_handoff_only_runs_once(self):
        self.add_item()
        response = self.client.post(reverse("training_checkout"))
        order = TrainingOrder.objects.get()
        self.assertEqual(order.first_name, "")
        self.assertEqual(order.last_name, "")
        self.assertEqual(order.email, "")
        payment = self.client.get(response["Location"])
        self.assertContains(payment, "data-payfast-handoff")
        self.assertContains(payment, "Pay with PayFast")
        self.assertNotContains(self.client.get(response["Location"]), "data-payfast-handoff")
        returned = self.client.get(reverse("training_payment_return", args=[order.token]))
        self.assertContains(returned, "proof of payment")
        self.assertContains(returned, "info@localfaces.co.za")
        self.assertContains(returned, "name and surname")
        self.assertContains(returned, str(order.token))
        order.refresh_from_db()
        self.assertEqual(order.status, TrainingOrder.Status.PENDING)
        cancelled = self.client.get(reverse("training_payment_cancel", args=[order.token]))
        self.assertNotContains(cancelled, "proof of payment")
        self.assertContains(cancelled, "Return to payment")

    def test_checkout_requires_post_and_nonempty_cart(self):
        self.assertEqual(self.client.get(reverse("training_checkout")).status_code, 405)
        response = self.client.post(reverse("training_checkout"))
        self.assertRedirects(response, reverse("training_cart"), fetch_redirect_response=False)
        self.assertFalse(TrainingOrder.objects.exists())

    def test_existing_full_price_order_keeps_original_amount(self):
        order = TrainingOrder.objects.create(
            first_name="Alex", last_name="Example", email="alex@example.com",
            total=Decimal("3000.00"),
            items=[{"training": "course", "term": "1", "city": "Durban", "subtotal": "3000.00"}],
        )
        response = self.client.get(reverse("training_payment", args=[order.token]))
        self.assertContains(response, 'name="amount" value="3000.00"')
        self.assertNotContains(response, "remaining R2500.00")

    def test_empty_submission_shows_errors(self):
        response = self.client.post(reverse("training_shop"), {})
        self.assertTrue(response.context["form"].errors)

    @override_settings(PAYFAST_MERCHANT_ID="")
    def test_unconfigured_checkout_keeps_cart(self):
        self.add_item()
        response = self.client.post(reverse("training_checkout"), {
            "first_name": "Alex", "last_name": "Example", "email": "alex@example.com"
        })
        self.assertRedirects(response, reverse("training_cart"), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse("training_cart")), "PayFast is not configured")
        self.assertEqual(TrainingOrder.objects.count(), 0)
        self.assertEqual(len(self.client.get(reverse("training_cart")).context["items"]), 1)

    @override_settings(DEBUG=True, PAYFAST_SITE_URL="http://127.0.0.1:8765")
    def test_local_sandbox_checkout_shows_payment_and_pending_warning(self):
        self.add_item()
        response = self.client.post(reverse("training_checkout"), {
            "first_name": "Alex", "last_name": "Example", "email": "alex@example.com"
        })
        order = TrainingOrder.objects.get()
        self.assertRedirects(response, reverse("training_payment", args=[order.token]), fetch_redirect_response=False)
        payment = self.client.get(response["Location"])
        self.assertContains(payment, "sandbox.payfast.co.za/eng/process")
        self.assertContains(payment, 'name="amount" value="500.00"')
        self.assertNotContains(payment, 'name="notify_url"')
        self.assertContains(payment, "Test orders will remain pending")
        self.assertContains(payment, "info@localfaces.co.za")
        returned = self.client.get(reverse("training_payment_return", args=[order.token]))
        self.assertContains(returned, "Test orders will remain pending")
        order.refresh_from_db()
        self.assertEqual(order.status, TrainingOrder.Status.PENDING)

    @override_settings(DEBUG=False, PAYFAST_SITE_URL="http://127.0.0.1:8765")
    def test_local_url_is_not_allowed_in_production(self):
        self.add_item()
        response = self.client.post(reverse("training_checkout"), {
            "first_name": "Alex", "last_name": "Example", "email": "alex@example.com"
        })
        self.assertRedirects(response, reverse("training_cart"), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse("training_cart")), "PayFast is not configured")
        self.assertFalse(TrainingOrder.objects.exists())

    @override_settings(DEBUG=True, PAYFAST_SANDBOX=False, PAYFAST_SITE_URL="http://127.0.0.1:8765")
    def test_local_url_is_not_allowed_for_live_payments(self):
        self.add_item()
        response = self.client.post(reverse("training_checkout"), {
            "first_name": "Alex", "last_name": "Example", "email": "alex@example.com"
        })
        self.assertRedirects(response, reverse("training_cart"), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse("training_cart")), "PayFast is not configured")
        self.assertFalse(TrainingOrder.objects.exists())

    def test_return_does_not_confirm_payment(self):
        order = self.create_order()
        response = self.client.get(reverse("training_payment_return", args=[order.token]))
        self.assertContains(response, "awaiting payment confirmation")
        order.refresh_from_db()
        self.assertEqual(order.status, TrainingOrder.Status.PENDING)

    @patch("agency.payfast.urlopen")
    def test_notification_requires_signature_server_validation_and_correct_amount(self, urlopen):
        order = self.create_order()
        fields = [
            ("m_payment_id", str(order.token)),
            ("pf_payment_id", "12345"),
            ("payment_status", "COMPLETE"),
            ("merchant_id", "10000100"),
            ("amount_gross", "3500.00"),
        ]
        urlopen.return_value.__enter__.return_value.read.return_value = b"VALID"
        payload = dict(fields + [("signature", signature(fields, "test passphrase"))])
        invalid = dict(payload, amount_gross="0.01")
        self.assertEqual(self.client.post(reverse("payfast_notify"), invalid).status_code, 400)
        invalid = dict(payload, signature="incorrect")
        self.assertEqual(self.client.post(reverse("payfast_notify"), invalid).status_code, 400)
        urlopen.return_value.__enter__.return_value.read.return_value = b"INVALID"
        self.assertEqual(self.client.post(reverse("payfast_notify"), payload).status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, TrainingOrder.Status.PENDING)
        urlopen.return_value.__enter__.return_value.read.return_value = b"VALID"
        self.assertEqual(self.client.post(reverse("payfast_notify"), payload).status_code, 200)
        self.assertEqual(self.client.post(reverse("payfast_notify"), payload).status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, TrainingOrder.Status.PAID)
        self.assertEqual(order.payfast_payment_id, "12345")

    @patch("agency.payfast.urlopen", side_effect=OSError("PayFast unavailable"))
    def test_notification_network_failure_does_not_confirm_payment(self, urlopen):
        order = self.create_order()
        fields = [
            ("m_payment_id", str(order.token)),
            ("pf_payment_id", "12345"),
            ("payment_status", "COMPLETE"),
            ("merchant_id", "10000100"),
            ("amount_gross", "3500.00"),
        ]
        response = self.client.post(reverse("payfast_notify"), dict(
            fields + [("signature", signature(fields, "test passphrase"))]
        ))
        self.assertEqual(response.status_code, 503)
        order.refresh_from_db()
        self.assertEqual(order.status, TrainingOrder.Status.PENDING)
