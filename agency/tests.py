from html.parser import HTMLParser
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

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

    def test_training_links_go_to_shop(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("training_shop")}"')
        self.assertNotContains(response, "Apply for 2027 training")
        self.assertNotContains(response, f'href="{reverse("camp:apply")}"')

    def test_academy_opportunity_is_accessible_from_home(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("academy_opportunity"))
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
    def add_item(self, **overrides):
        data = {"training": "course", "term": "2", "city": "Durban", "hours": "1"}
        data.update(overrides)
        return self.client.post(reverse("training_shop"), data)

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
        payment = self.client.get(response["Location"])
        self.assertContains(payment, 'name="amount" value="2166.67"')
        self.assertContains(payment, "month two")
        self.assertContains(payment, "month three")
        self.assertContains(self.client.get(reverse("training_payment_return", args=[order.token])), "month three")

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
