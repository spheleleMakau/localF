# Local Faces

The initial Local Faces Talent Agency & Entertainment website, built with Django and a custom editorial-style responsive homepage.

## Current stage

This first stage establishes the Django project, base template, responsive navigation and homepage sections for services, training, talent categories, photography, merchandise, the founder and the main call to action. The provided workspace did not contain the Local Faces logo, approved photographs or confirmed contact details. Image areas and contact details are therefore visibly identified as pending; no talent profiles, products, prices or agency achievements have been invented.

Registration forms, content administration beyond Django's built-in admin, image uploads and the remaining dedicated pages are not implemented in this stage. The talent application flow must not be used until server-side validation, private file storage and explicit success/error handling are added.

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

Uploaded media is not part of this initial stage. Before enabling uploads in production, configure durable private object storage or a persistent disk, access controls and retention rules. Do not serve private applicant files as public static content.
