# 📱 SMS Assistant - Personal SMS Bot

A personal SMS assistant built with Flask, Twilio, and NLP that helps you track food, water, gym workouts, reminders, and todos via text messages.

## 🎯 Features

- **Water Logging**: "drank a bottle" → logs water intake
- **Food Logging**: "ate chicken sandwich" → logs food with macros
- **Gym Workouts**: "did bench press 135x5" → logs workout
- **Reminders**: "remind me to call mom at 3pm" → sets reminder
- **Todos**: "todo buy groceries" → adds to todo list
- **Scheduled Reminders**: Automatic SMS reminders at set times
- **Morning Check-ins**: Daily morning SMS with todos and stats

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Twilio account (free trial available)
- ngrok (for local testing)

### Installation

1. **Clone and setup:**
```bash
cd sms_assistant
./install.sh  # Creates venv and installs dependencies
source venv/bin/activate
```

2. **Configure environment:**
```bash
cp config/env_template.txt .env
# Edit .env with your Twilio credentials
```

3. **Get Twilio credentials:**
   - Sign up at [twilio.com](https://www.twilio.com) (free $15.50 credit)
   - Get Account SID and Auth Token from Console Dashboard
   - Buy a **toll-free number** (~$2-3/month) - No A2P 10DLC registration required!

4. **Set up webhook:**
   - In Twilio Console → Phone Numbers → Your Number
   - Set "A message comes in" to: `https://your-url.com/webhook/twilio`
   - For local testing, use ngrok: `ngrok http 5001`

5. **Run the bot:**
```bash
python app.py
```

## 📋 Environment Variables

Create a `.env` file with:

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Your phone number (for scheduled reminders)
YOUR_PHONE_NUMBER=+1234567890

# Communication Mode
COMMUNICATION_MODE=sms

# App Settings
MORNING_CHECKIN_HOUR=8
EVENING_REMINDER_HOUR=20

# Water Bottle Size (milliliters)
# Default: 500ml (standard water bottle)
WATER_BOTTLE_SIZE_ML=500

# Google Gemini API (for NLP processing)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

## 💰 Cost

- **Toll-Free Number**: ~$2-3/month (no A2P 10DLC registration needed!)
- **SMS**: $0.0075 per message
- **Estimated monthly** (300-600 messages): $4-7/month
- **Trial account**: $15.50 free credit (~2,000 SMS)
- **Why toll-free?** Cheaper than local + A2P 10DLC fees ($8 registration + $1.50/month)

## 📱 How It Works

### Incoming SMS (TwiML)
1. User texts your Twilio number
2. Twilio sends POST to `/webhook/twilio`
3. Bot processes message with NLP
4. Returns TwiML XML response
5. Twilio automatically sends SMS reply

### Scheduled Reminders (REST API)
1. Background scheduler checks reminders every minute
2. Uses Twilio REST API to send proactive SMS
3. Requires `YOUR_PHONE_NUMBER` in config

## 🧪 Testing

**See `TESTING_GUIDE.md` for complete testing instructions.**

### Local Testing with ngrok

1. **Start the app:**
```bash
python app.py
```

2. **Start ngrok:**
```bash
ngrok http 5001
```

3. **Update Twilio webhook:**
   - Copy ngrok HTTPS URL (e.g., `https://abc123.ngrok.io`)
   - Set webhook to: `https://abc123.ngrok.io/webhook/twilio`

4. **Test:**
   - Text your Twilio number: "Hello"
   - Should receive a response

### Health Check

```bash
curl http://localhost:5001/health
```

## 🚀 Deployment (Render)

**Cost**: $7/month (Starter plan - required for 24/7 operation)

1. **Create Render account** at [render.com](https://render.com)

2. **New Web Service:**
   - Connect GitHub repository
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
   - **Plan: Starter** ($7/month) - ⚠️ Free tier sleeps (not suitable for webhooks)

3. **Set Environment Variables:**
   - Add all variables from `.env` file (see `DEPLOYMENT.md` for list)

4. **Update Twilio Webhook:**
   - Set to: `https://your-app.onrender.com/webhook/twilio`

5. **Deploy:**
   - Render will build and deploy automatically
   - Check logs for any errors

**See `docs/DEPLOYMENT_GUIDE.md` for detailed instructions.**

## 📊 Database

The bot uses **CSV files** to store all data (simple, portable, human-readable):
- `data/logs/food_logs.csv` - Food logs with macros
- `data/logs/water_logs.csv` - Water intake logs
- `data/logs/gym_logs.csv` - Gym workout logs
- `data/logs/reminders_todos.csv` - Reminders and todos

**Benefits:**
- ✅ Easy to view/edit in Excel, Google Sheets, or any text editor
- ✅ No database dependencies
- ✅ Portable and simple
- ✅ CSV files are created automatically on first use

**Food Database:**
- Edit `data/wu_foods.json` to add your custom foods with macros
- Foods are organized by restaurant (e.g., `sazon`, `krafthouse`, `gsoy`)
- Same food from different restaurants can have different macros
- See `data/FOOD_DATABASE_GUIDE.md` for detailed instructions

## 🔧 Troubleshooting

### "Twilio client not initialized"
- Check `.env` file has correct credentials
- Verify Account SID and Auth Token
- Ensure phone number is in E.164 format (+1XXXXXXXXXX)

### "Webhook not receiving messages"
- Verify webhook URL in Twilio Console
- Check app is accessible (use ngrok for local)
- Test webhook endpoint manually

### "SMS not sending"
- Check account has credits
- Verify phone number format
- Check Twilio Console logs

## 📝 Example Commands

- `"drank 16oz water"` → Logs water
- `"ate sazon quesedilla"` → Logs food with macros from sazon restaurant
- `"ate krafthouse quesedilla"` → Logs same food but different macros from krafthouse
- `"did bench press 135x5"` → Logs workout
- `"remind me to call mom at 5pm tomorrow"` → Sets reminder
- `"todo buy groceries"` → Adds todo

## 🎉 Success Indicators

✅ App starts without errors  
✅ Health endpoint responds  
✅ Twilio webhook receives messages  
✅ SMS responses sent automatically  
✅ Scheduled reminders work  

---

**Need help?** Check [Twilio docs](https://www.twilio.com/docs) or open an issue!

