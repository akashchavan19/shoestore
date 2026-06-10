# Onistuka — Deployment Guide

This guide deploys Onistuka to **Railway.app** — the easiest and most
beginner-friendly option. Free tier available. PostgreSQL and Redis included.

---

## Prerequisites

- GitHub account
- Railway account (railway.app — sign up with GitHub)
- Your Razorpay LIVE keys (from Razorpay Dashboard)
- A SendGrid account for emails (free tier: 100 emails/day)

---

## Step 1 — Push to GitHub

In your terminal (inside the onistuka_v2 folder):

```bash
git init
git add .
git commit -m "Initial commit — Onistuka e-commerce"
```

Create a new repository on github.com, then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/onistuka.git
git branch -M main
git push -u origin main
```

---

## Step 2 — Create Railway Project

1. Go to **railway.app** and sign in with GitHub
2. Click **New Project**
3. Select **Deploy from GitHub repo**
4. Select your `onistuka` repository
5. Railway will detect it's a Python project

---

## Step 3 — Add PostgreSQL

1. Inside your Railway project, click **+ New**
2. Select **Database → PostgreSQL**
3. Railway creates a PostgreSQL instance automatically
4. Click on the PostgreSQL service → **Variables** tab
5. Copy the `DATABASE_URL` value — you'll need it in Step 5

---

## Step 4 — Add Redis

1. Inside your Railway project, click **+ New**
2. Select **Database → Redis**
3. Railway creates a Redis instance automatically
4. Click on the Redis service → **Variables** tab
5. Copy the `REDIS_URL` value — you'll need it in Step 5

---

## Step 5 — Set Environment Variables

Click on your **web service** (the Django app) → **Variables** tab.
Add ALL of these:

```
DJANGO_SETTINGS_MODULE = onistuka.settings.prod
SECRET_KEY             = (generate with command below)
DEBUG                  = False
ALLOWED_HOSTS          = your-app.railway.app
DATABASE_URL           = (paste from Step 3)
REDIS_URL              = (paste from Step 4)
CORS_ALLOWED_ORIGINS   = https://your-app.railway.app
EMAIL_HOST             = smtp.sendgrid.net
EMAIL_PORT             = 587
EMAIL_HOST_USER        = apikey
EMAIL_HOST_PASSWORD    = (your SendGrid API key)
DEFAULT_FROM_EMAIL     = noreply@onistuka.com
RAZORPAY_KEY_ID        = rzp_live_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET    = (your live secret)
RAZORPAY_WEBHOOK_SECRET = (from Razorpay Dashboard → Webhooks)
```

**Generate SECRET_KEY** — run this locally and paste the output:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Step 6 — Set Start Command

In Railway → your web service → **Settings** tab:
- **Build Command:** `bash build.sh`
- **Start Command:** `gunicorn onistuka.wsgi:application --workers 4 --threads 2 --bind 0.0.0.0:$PORT`

---

## Step 7 — Deploy

1. Railway auto-deploys when you push to GitHub
2. Watch the **Deploy Logs** — you should see:
   ```
   === Installing dependencies ===
   === Collecting static files ===
   === Running migrations ===
   === Build complete ===
   ```
3. Once done, click **Generate Domain** to get your public URL

---

## Step 8 — Create Superuser

Railway lets you run one-off commands:
1. Go to your web service → **Settings** → **Deploy** section
2. Click **New Run** and enter:
   ```
   python manage.py createsuperuser
   ```
3. Follow the prompts

---

## Step 9 — Set Up Razorpay Webhook

1. Go to **Razorpay Dashboard → Webhooks → Add New Webhook**
2. URL: `https://your-app.railway.app/orders/webhook/razorpay/`
3. Events: tick `payment.captured`
4. Copy the webhook secret → paste into Railway env as `RAZORPAY_WEBHOOK_SECRET`

---

## Step 10 — Verify Everything Works

Visit these URLs on your live site:

| URL | Expected |
|---|---|
| `https://your-app.railway.app/` | Home page loads |
| `https://your-app.railway.app/admin/` | Admin login |
| `https://your-app.railway.app/api/v1/products/` | JSON response |
| `https://your-app.railway.app/accounts/register/` | Register page |

---

## After Deployment — First Things To Do

1. **Log into admin** → add your first few shoe products with images
2. **Create a test coupon** → Admin → Coupons → Add Coupon → code `WELCOME10`
3. **Test a full order** → register → add to cart → checkout → pay with Razorpay test card
4. **Switch Razorpay to LIVE mode** → update `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in Railway

---

## Scaling Beyond 1000 Users

When traffic grows, this is the order of things to do:

1. **Upgrade Railway plan** — more RAM, more CPU (one click)
2. **Increase Gunicorn workers** — change `--workers 4` to `--workers 8`
3. **Add read replica** — Railway PostgreSQL supports this
4. **CDN for media files** — move product images to Cloudflare R2 or AWS S3
5. **Celery workers** — add a separate Railway service running Celery

---

## Common Issues

**Static files not loading:**
```bash
python manage.py collectstatic --noinput
```

**Migrations not applied:**
```bash
python manage.py migrate --noinput
```

**500 errors in prod:**
- Check Railway deploy logs
- Make sure all env variables are set
- `DEBUG=False` must be set — never `True` in prod

**Razorpay payment failing:**
- Make sure you're using LIVE keys, not test keys
- Make sure `ALLOWED_HOSTS` includes your domain
- Make sure webhook URL is correct in Razorpay dashboard
