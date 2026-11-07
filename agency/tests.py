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
        self.assertContains(response, "LOCAL FACES ENTERTAINMENT")
        self.assertContains(response, "MODELLING ACADEMY")
        self.assertNotContains(response, "SUMMER MODELLING ACADEMY")
        self.assertContains(response, "Get Represented")
        self.assertContains(response, "agency/img/founder-portrait.jpg")
        for label in ("Home", "About", "Talent", "Training", "Photography", "Contact"):
            self.assertContains(response, f">{label}</a>")

    def test_model_slideshow_has_requested_images(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "data-model-slide", count=3)
        self.assertNotContains(response, "data-slideshow-control")
        self.assertNotContains(response, "agency/img/hero-smile.jpg")
        self.assertNotContains(response, "agency/img/hero-profile.jpg")
        self.assertContains(response, "agency/img/talent-models.jpg")
        self.assertContains(response, "agency/img/founder-portrait.jpg")

    def test_logos_use_entertainment_branding(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<span class="brand-tagline">Entertainment</span>', count=3)
        self.assertContains(response, 'aria-label="Local Faces Entertainment home"', count=2)
        self.assertContains(response, 'aria-label="Local Faces Entertainment"')
        self.assertNotContains(response, '<span class="brand-tagline">Talent Agency')

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
        for url in (reverse("home"), reverse("camp:apply"), reverse("camp:apply_form")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "2026 training is full.")
                self.assertContains(response, "Training is available for 2027")
                self.assertContains(response, "6-week intensive")
                self.assertContains(response, "first-come, first-served")
                self.assertContains(response, "Durban")
                self.assertContains(response, "Johannesburg")
                self.assertContains(response, "Cape Town")
                self.assertContains(response, "Hosted by Semu", count=3)
                self.assertContains(response, "Registration: R500")
                self.assertContains(response, "non-refundable")
                self.assertContains(response, "Course: R2,500")

    def test_training_links_go_to_details_and_shop(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("training_shop")}"')
        self.assertContains(
            response,
            f'href="{reverse("camp:apply")}">Explore training</a>',
        )
        self.assertNotContains(response, "Apply for 2027 training")

    def test_course_topics_appear_on_homepage_and_course_details(self):
        topics = (
            "Modelling &amp; Runway",
            "On-Camera &amp; Audition Skills",
            "Confidence &amp; Self-Esteem",
            "Branding &amp; Social Media",
            "Industry Knowledge &amp; Representation",
        )
        home = self.client.get(reverse("home"))
        for topic in topics:
            self.assertContains(home, topic, count=1)
        for url in (reverse("camp:apply"), reverse("camp:apply_form"), reverse("training_shop")):
            response = self.client.get(url)
            self.assertContains(response, "What the course covers")
            for topic in topics:
                self.assertContains(response, topic)

    def test_academy_opportunity_is_accessible_from_home(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("academy_opportunity"))
        self.assertContains(response, f'href="{reverse("academy_opportunity")}">Start your academy →</a>')
        response = self.client.get(reverse("academy_opportunity"))
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
        self.add_item(training="individual", term="4", city="other", other_city="Pretoria", hours="2")
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
            "training": "individual", "term": "4", "city": "other",
            "other_city": "Pretoria", "hours": "2",
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
        self.assertEqual(page.context["form"]["city"].value(), "Pretoria")

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
        self.assertEqual((application.city, application.dress_size, application.photos.count()), ("Pretoria", "10", 2))
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
        self.assertEqual(self.add_item(training="individual", term="4", city="other", other_city="Pretoria", hours="2").status_code, 302)
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
        self.assertEqual(order.items[1]["city"], "Pretoria")
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
        response = self.add_item(city="other", other_city="Pretoria")
        self.assertFormError(response.context["form"], "city", "Choose Durban, Johannesburg or Cape Town for the group course.")
        response = self.add_item(training="individual", city="other")
        self.assertFormError(response.context["form"], "other_city", "Enter your city for one-on-one training.")
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
        self.assertContains(response, '>Other city</option>')
        self.assertNotContains(response, "Other city (one-on-one only)")
        for city in ("Durban", "Johannesburg", "Cape Town"):
            self.assertContains(response, f'value="{city}"')
            added = self.add_item(city=city, hours="")
            self.assertRedirects(added, reverse("training_cart"))
        cart = self.client.get(reverse("training_cart"))
        self.assertEqual(cart.context["total"], Decimal("1500.00"))
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
