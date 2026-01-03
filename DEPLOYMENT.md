# 🚀 Deployment Guide - Quick Reference

## Render Deployment (Recommended)

**Cost**: $7/month (Starter plan - always-on)

### Quick Steps:

1. **Push code to GitHub**
2. **Create Render account**: [render.com](https://render.com)
3. **New Web Service**:
   - Connect GitHub repo
   - Name: `sms-assistant`
   - Build: `pip install -r requirements.txt`
   - Start: `python app.py`
   - Plan: **Starter** ($7/month)
4. **Add environment variables** (from your `.env` file)
5. **Deploy** and get URL: `https://sms-assistant.onrender.com`
6. **Update Twilio webhook** to: `https://sms-assistant.onrender.com/webhook/twilio`

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
```

### Why Starter Plan?

- Free tier sleeps after 15 minutes → webhooks won't work
- Starter plan keeps app always-on → reliable SMS handling
- $7/month is cheapest always-on option

See `docs/DEPLOYMENT_GUIDE.md` for detailed instructions.

