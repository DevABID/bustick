# BusTick: bus ticket booking (React + Django)

Online bus ticket booking: search routes, pick seats on a live seat map, pay online
(SSLCommerz or Stripe), and get an instant e-ticket with PDF and email.

```
ticket_system/   Django REST API + admin dashboard
ticket-ui/       React frontend
```

## Features

- Route search with seats-left count, sorting, and past departures hidden
- Live seat map (Business 1+2 / Economy 2+2), up to 4 seats per booking
- **Seat holds**: seats are reserved for 10 minutes while the customer pays and released automatically if they don't
- **Real payments**:
  - **SSLCommerz**: BDT; bKash, Nagad, Rocket, cards, net banking. Every payment is checked with SSLCommerz's validation API, plus IPN.
  - **Stripe Checkout**: cards, Apple Pay, Google Pay. Signed webhook, plus status polling.
  - **Demo**: no keys needed, local development only (refused when `DEBUG=False`)
- E-ticket page, downloadable PDF ticket, and HTML confirmation email
- Find ticket / return ticket with PNR **and** email. Returns are allowed up to 12 hours before departure.
- Help page contact form emailed to your support inbox, with spam protection
- Admin dashboard: today's revenue, seats sold, 7-day revenue chart, top routes, and payments that need a refund
- Secrets in `.env`, rate-limited lookups, production security settings
- Automated tests for booking, double-booking, seat holds, payments and returns

## 1. Backend setup

```bash
cd ticket_system
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then edit .env
python manage.py migrate
python manage.py seed_demo        # optional: demo routes, buses and 14 days of trips
python manage.py createsuperuser
python manage.py test booking     # optional: run the tests
python manage.py runserver
```

Admin: http://127.0.0.1:8000/admin/

**Upgrading an existing database:** `python manage.py migrate` applies
`0012_payments_and_seat_holds`. It also converts old seat types (`ECONOMY40`,
`BUSINESS_26`, …) to `ECONOMY` / `BUSINESS`.

## 2. Frontend setup

```bash
cd ticket-ui
npm install
cp .env.example .env              # REACT_APP_API_URL=http://127.0.0.1:8000
npm start
```

Open http://localhost:3000

## 3. Turn on real payments

### SSLCommerz (recommended for Bangladesh)
1. Create a free sandbox store at https://developer.sslcommerz.com/registration/
2. In `ticket_system/.env`:
   ```
   PAYMENT_PROVIDER=sslcommerz
   SSLCOMMERZ_STORE_ID=your_store_id
   SSLCOMMERZ_STORE_PASSWORD=your_store_password
   SSLCOMMERZ_SANDBOX=True
   BACKEND_URL=https://your-api-domain.com
   ```
3. SSLCommerz posts back to `BACKEND_URL/api/gateway/sslcommerz/...`, so that address must be publicly
   reachable. For local testing, expose port 8000 with a tunnel such as `ngrok http 8000` and use that
   URL as `BACKEND_URL`.
4. In the SSLCommerz merchant panel, set the IPN URL to `BACKEND_URL/api/gateway/sslcommerz/ipn/`.
5. Go live: use your live store credentials and set `SSLCOMMERZ_SANDBOX=False`.

### Stripe
1. Get test keys at https://dashboard.stripe.com/test/apikeys
2. In `.env`: `PAYMENT_PROVIDER=stripe` and `STRIPE_SECRET_KEY=sk_test_...`
3. Add a webhook endpoint `BACKEND_URL/api/gateway/stripe/webhook/` for the events
   `checkout.session.completed`, `checkout.session.expired` and `checkout.session.async_payment_succeeded`.
   Put its signing secret in `STRIPE_WEBHOOK_SECRET`.
   Locally you can skip the webhook. The confirmation page asks Stripe for the status directly.
4. Test card: `4242 4242 4242 4242`, any future date, any CVC.

Check that Stripe supports your account country and currency before using it in production.

## 4. Email (tickets and the support form)

On Render's free plan use Brevo instead of Gmail SMTP (see section 6).

Messages from the Help page contact form are saved in the admin (**Support messages**)
and emailed to `SUPPORT_EMAIL` (default `arabid8427@gmail.com`). Hitting "Reply" in your
inbox goes straight to the customer.


**Emails only print in the terminal until you set up SMTP below.** To send real emails with Gmail, create an App Password
(Google Account → Security → App passwords) and set in `.env`:
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
DEFAULT_FROM_EMAIL=BusTick <you@gmail.com>
```

## 5. Keeping buses on sale

Searches only show trips that exist in **Admin → Schedules** for that date. If you see
"No buses", that route has no schedule on that day.

- Quick demo data: `python manage.py seed_demo`
- Repeat your real daily departures forward: `python manage.py extend_schedules --days 30`
  This copies each bus + route + departure time to every upcoming day that doesn't have one yet.
  Run it once a day (Linux cron: `0 1 * * * cd /path/ticket_system && venv/bin/python manage.py extend_schedules`,
  Windows: Task Scheduler) and schedules never run out.

When a date has no buses, the results page suggests the next dates that do.

## 6. Deploy on Render

The repo includes `render.yaml`, which creates the Django API and the React site in one go.
You provide the Postgres database URL yourself, because Render allows only **one free database per account**.

### Get a database URL (pick one)
- **A. Reuse your existing free Render database.** Open it in the Render dashboard and copy the **Internal Database URL**.
  Use this only if no other Django project uses that database, because the tables would clash.
  If the old project is finished, the cleanest option is to delete it and its database, then
  create a new free Postgres called `bustick-db` and copy its Internal URL.
  Deleting a database deletes its data for good.
- **B. Use a separate free Postgres provider**, such as Neon or Supabase. Create a project, copy the connection string
  (`postgresql://…`), and add `?sslmode=require` at the end if it isn't there already.

### Know the free-plan limits first
- **The server sleeps** after 15 minutes without visitors. The next visit takes about a minute to load,
  and the site shows a "Connecting to the server…" message while it waits. The paid Starter instance ($7/month) never sleeps.
- **Free Postgres expires after 30 days**, then gets deleted after a 14-day grace period. Upgrade the database
  (from about $6/month) before then if the data matters.
- **Email via SMTP (Gmail) is blocked** on free services. The blueprint uses **Brevo**, which sends email over HTTPS.
  On a paid instance you can switch back to Gmail SMTP.
- Files on the server are wiped on every deploy, which is why it uses Postgres and not SQLite.

### Steps
1. **Push the project to GitHub** (from the folder that contains `render.yaml`):
   ```bash
   git init
   git add .
   git commit -m "BusTick"
   git branch -M main
   git remote add origin https://github.com/<your-username>/bustick.git
   git push -u origin main
   ```
   On Windows, also run `git update-index --chmod=+x ticket_system/build.sh` before committing.
2. **Set up email (free):** create a Brevo account at https://www.brevo.com, verify a sender
   (Senders & IPs → add your Gmail address), then create an API key (SMTP & API → API keys).
3. **Create the Blueprint:** Render dashboard → **New → Blueprint** → choose your repo.
   Render will ask for the `sync: false` values. Your two sites will be at
   `https://bustick.onrender.com` and `https://bustick-api.onrender.com`; the names may differ if
   they're taken, so check the dashboard.
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the database URL from above |
   | `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | your React site URL, e.g. `https://bustick.onrender.com` |
   | `REACT_APP_API_URL` | your API URL, e.g. `https://bustick-api.onrender.com` |
   | `BREVO_API_KEY` | from step 2 |
   | `DEFAULT_FROM_EMAIL` | `BusTick <the-sender-you-verified@gmail.com>` |
   | `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` | your admin login |
   | `SSLCOMMERZ_STORE_ID` / `PASSWORD` | leave empty while using demo payments |
4. Click **Apply** and wait for all three to show **Live**. The first build takes a few minutes.
   If you guessed a URL wrong, fix it under the service's **Environment** tab and redeploy.
   After changing `REACT_APP_API_URL`, the React site must be redeployed because the value is built in.
5. **Admin login and data:** these are created automatically on deploy from the values you entered
   for `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD`.
   `SEED_DEMO=True` adds demo routes and trips. Set it to `False` once you add your real buses in the admin.
   Admin: `https://bustick-api.onrender.com/admin/`
6. Every `git push` redeploys automatically. Each deploy also runs `extend_schedules`, so trips keep going.

### Going from demo to real payments
Set `PAYMENT_PROVIDER=sslcommerz`, fill in the SSLCommerz keys, and delete `ALLOW_DEMO_PAYMENTS`.
SSLCommerz can reach Render directly, so you don't need ngrok. Set the IPN URL in the SSLCommerz panel to
`https://bustick-api.onrender.com/api/gateway/sslcommerz/ipn/`. For a real business, use paid instances
so the site doesn't sleep in the middle of a customer's payment.

### Other hosts
Any host works: set the same environment variables, run `build.sh`, and start with
`gunicorn ticket_system.wsgi`. The React `build/` folder can go on Netlify, Vercel or Nginx,
with every route falling back to `index.html`.

## API overview

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/routes/` | All routes, with lowest upcoming fare and next date |
| GET | `/api/schedules/next-dates/?from=&to=` | Next 5 dates with buses |
| GET | `/api/schedules/?from=&to=&date=&sort=` | Search trips |
| GET | `/api/schedules/<id>/` | Trip with seat layout and booked seats |
| POST | `/api/bookings/` | Hold seats → returns a pending payment |
| GET | `/api/payments/<tran_id>/` | Payment status and tickets |
| POST | `/api/payments/<tran_id>/checkout/` | Get the gateway redirect URL |
| POST | `/api/payments/<tran_id>/cancel/` | Release held seats |
| GET | `/api/payments/<tran_id>/ticket.pdf` | E-ticket PDF |
| GET | `/api/tickets/lookup/?pnr=&email=` | Find a ticket |
| POST | `/api/tickets/return/` | Return a ticket |
| POST | `/api/support/` | Help page contact form (emails `SUPPORT_EMAIL`) |
