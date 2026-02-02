## Stripe setup checklist (what you need to do)

This repo now includes the Stripe endpoints + Pricing page wiring. To get it working end-to-end, do the steps below.

---

## 1) Supabase (DB) — add billing columns

Run this SQL in Supabase SQL editor:
- `supabase_schema_stripe_billing.sql`

---

## 2) Stripe Dashboard — create Products + Prices

Create two products:
- **Alfred Core**
- **Alfred Pro**

Create 4 recurring prices:
- Core: **$12/month** and **$120/year**
- Pro: **$20/month** and **$200/year**

Copy the 4 **Price IDs** (`price_...`).

---

## 3) Stripe Dashboard — add webhook

Create a webhook endpoint:
- URL: `POST https://<your-domain>/stripe/webhook`
- Events:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`

Copy the webhook signing secret (`whsec_...`).

---

## 4) Environment variables — set Stripe keys + price IDs

In your server `.env` (and in production env vars), set:

```env
BASE_URL=https://<your-domain>

STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

STRIPE_PRICE_CORE_MONTHLY=price_...
STRIPE_PRICE_CORE_ANNUAL=price_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_ANNUAL=price_...
```

Notes:
- `BASE_URL` must match where your app is reachable (used for Stripe success/cancel URLs).
- Free tier does **not** require a card.

---

## 5) Local testing (recommended)

Install Stripe CLI, then run:

```bash
stripe login
stripe listen --forward-to localhost:5001/stripe/webhook
```

Use the webhook secret printed by Stripe CLI for local `.env`.

---

## 6) Verify it works

1. Start the app with Stripe env vars set.
2. Go to `/dashboard/pricing`
3. Click **Choose Core** → you should be redirected to Stripe Checkout.
4. Complete checkout in test mode → Stripe calls webhook → your `public.users` row should update:
   - `plan` = `core` (or `pro`)
   - `stripe_subscription_status` = `active`


