# 🚀 Deployment Guide - Quick Reference

## Koyeb Deployment

**Current Deployment**: Working on Koyeb at `https://objective-almeria-sarthakagrawal-a8b1c327.koyeb.app`

**Homepage (landing + login):** `https://objective-almeria-sarthakagrawal-a8b1c327.koyeb.app/`  
`/dashboard/login` redirects to the homepage.

### Quick Steps:

1. **Push code to GitHub**
2. **Create Koyeb account**: [koyeb.com](https://koyeb.com)
3. **New Web Service**:
   - Connect GitHub repo
   - Name: `sms-assistant`
   - Build: `pip install -r requirements.txt`
   - Start: `python app.py`
   - Add environment variables (from your `.env` file)
4. **Deploy** and get URL: `https://your-app.koyeb.app`
5. **Update Twilio webhook** to: `https://your-app.koyeb.app/webhook/twilio`

### Environment Variables Needed:

```
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX (your toll-free number)
YOUR_PHONE_NUMBER=+1XXXXXXXXXX (your personal number)
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
COMMUNICATION_MODE=sms
NLP_ENGINE=gemini
MORNING_CHECKIN_HOUR=8
WATER_BOTTLE_SIZE_ML=500
SUPABASE_URL=...
SUPABASE_KEY=...
DASHBOARD_PASSWORD=...

# Optional: Nutrition APIs (for generalized calorie/macro lookup)
USDA_FDC_API_KEY=...
OPENFOODFACTS_BASE_URL=https://world.openfoodfacts.org
NUTRITIONIX_APP_ID=...
NUTRITIONIX_API_KEY=...
NUTRITION_CACHE_TTL_DAYS=30

# Dashboard image uploads (requires Supabase Storage bucket)
FOOD_IMAGE_BUCKET=food-uploads
FOOD_IMAGE_MAX_BYTES=6000000
KOYEB=true (automatically set by Koyeb)
PORT=10000 (automatically set by Koyeb)
```

### Koyeb Benefits:

- Always-on deployment (no cold starts)
- Automatic HTTPS and custom domains
- Simple deployment from GitHub
- Free tier available with limitations

See `docs/DEPLOYMENT_GUIDE.md` for detailed instructions.

