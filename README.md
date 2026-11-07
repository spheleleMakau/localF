# Local Faces

The initial Local Faces Talent Agency & Entertainment website, built with Django and a custom editorial-style responsive homepage.

## Current stage

The site includes a responsive homepage, model applications, training information and a training cart. Merchandise details remain pending.

The model application collects details and photographs and uses a WhatsApp handoff. Other talent categories are not yet accepting applications. The old training application has been replaced by training details and the shop; existing application records remain available to staff. The 2027 training shop offers terms 1–4, a R3,000 group course in Durban, Johannesburg or Cape Town, and one-on-one training with Semu in all cities at R1,500 per hour. Only the R500 non-refundable group-course registration fee is paid online; the remaining R2,500 course fee is arranged separately with Local Faces. For another city, select “Other city” for one-on-one training and enter its name. Actual dates and arrangements are confirmed separately.

The academy business opportunity costs R5,000: R1,666.67 is payable through the cart, and the remaining R1,666.67 and R1,666.66 are arranged separately for months two and three. The proposed city and remaining instalments are recorded in the order. Staff must discuss availability and operating terms with the customer and track later payments separately; an online payment does not automatically grant exclusivity or approve a location.

Each group-course and one-on-one booking requires an applicant form, sizes and two photographs before it can be added to the cart. The one-on-one form follows the talent-pool application, while the group form includes course availability questions. Applications are stored when submitted, even if the cart is abandoned or the item is removed; staff can find the application number in the order's item snapshot and review it in Django admin. Existing training cart items without an application must be removed and added again.

## PayFast checkout

Set the following environment variables before accepting payments:

- `PAYFAST_MERCHANT_ID` and `PAYFAST_MERCHANT_KEY`: your PayFast merchant credentials.
- `PAYFAST_PASSPHRASE`: the passphrase configured in the PayFast account, if used. Keep it secret.
- `PAYFAST_SITE_URL`: the public HTTPS origin of the site, e.g. `https://example.com`, without a path. PayFast must be able to reach it for notifications.
- `PAYFAST_SANDBOX`: defaults to `True`; set to `False` only after testing with live merchant credentials. Test mode is labelled in checkout.

Set these in Render's environment, not in source control. Configure the corresponding merchant account and passphrase in PayFast. The hosted PayFast form uses the site's return, cancel, and notification URLs. Verify a complete transaction and notification using the PayFast sandbox on a publicly reachable deployment before going live. Missing configuration prevents checkout rather than creating a payable order.

For local sandbox testing only, set `DEBUG=True`, `PAYFAST_SANDBOX=True`, the PayFast sandbox merchant credentials and passphrase, and `PAYFAST_SITE_URL=http://127.0.0.1:8765` before starting the server on that port. PayFast cannot reach a local notification URL, so this mode omits it and test orders stay pending; a browser return is not proof of payment. Real payment and notification testing requires a publicly reachable HTTPS deployment and the appropriate merchant configuration.

The cart is session-based. Checkout creates an order without asking for contact details and sends the customer to PayFast; orders are visible in Django admin under Training orders. Customers should include their order reference with their proof of payment so staff can identify their booking and obtain any required contact details. The group-course balance is recorded in each new order's item snapshot and must be collected and tracked separately; a paid order confirms only the amount charged through that order. Existing orders retain their original amounts. An order remains pending until a signed, matching notification is confirmed with PayFast. Returning from PayFast alone does not confirm payment. Customers are asked to email proof of payment to info@localfaces.co.za with their name and surname as reference; staff should reconcile payments and contact customers about dates and availability.

## Run locally

Requires Python 3.12 or newer.

1. Create and activate a virtual environment.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Apply migrations and start the development server:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

4. Open `http://127.0.0.1:8000/`.

The local default is SQLite. For local work, Django uses a development-only fallback secret key; set `SECRET_KEY` to a private value for any shared or deployed environment.

## Deploy to Render

### Blueprint (recommended)

Push the repository to GitHub, then in Render choose **New → Blueprint** and select it. `render.yaml` provisions the web service and a PostgreSQL database, generates `SECRET_KEY`, wires `DATABASE_URL`, runs `build.sh` (install, `collectstatic`, `migrate`) and starts Gunicorn. `RENDER_EXTERNAL_HOSTNAME` is added to the allowed hosts and CSRF trusted origins automatically; add custom domains through `ALLOWED_HOSTS`. After the first deploy, create an admin user from the Render shell with `python manage.py createsuperuser`.

Free Render plans have an ephemeral disk and a short-lived database; upgrade before real use.

### Manual setup

Alternatively, create a Web Service and a PostgreSQL database by hand and set the following environment variables in the Render dashboard (the app refuses to start with `DEBUG=False` and no `SECRET_KEY`):

- `SECRET_KEY`: a long, unique secret value.
- `DEBUG`: `False`.
- `ALLOWED_HOSTS`: the Render hostname (and any custom domains), comma-separated.
- `DATABASE_URL`: the Render PostgreSQL connection string.
- `SECURE_SSL_REDIRECT`: `True` (the production default).

Use the following build command:

```text
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

Set the start command to `gunicorn localfaces.wsgi:application` (also defined in `Procfile`). Static files are served through WhiteNoise. Run migrations during deployment or as a Render pre-deploy command when available.

Applicant photos require durable private storage in production. The Render blueprint configures a persistent disk; other deployments must configure their own durable private storage, access controls and retention rules. Do not serve private applicant files as public static content.
