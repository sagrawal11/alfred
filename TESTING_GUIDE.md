# Testing Guide - Next Steps

## ✅ Completed Setup

1. **Environment Configuration** - `.env` file exists and is configured
2. **Food Database** - Restructured to be organized by restaurant (12 restaurants with sample foods)
3. **Code Updates** - NLP processor updated to handle restaurant-based food structure
4. **Documentation** - Food database guide updated

## 📋 Remaining Manual Steps

### Step 1: Start the Application

```bash
cd "/Users/sarthak/Desktop/App Projects/sms_assistant"
source sms_venv/bin/activate
python app.py
```

**Expected output:**
- ✅ Configuration validated successfully
- ✅ Twilio REST client initialized
- ✅ Database directory ensured
- 🚀 Starting Alfred the Butler on localhost:5001

### Step 2: Test Health Endpoint

In another terminal:
```bash
curl http://localhost:5001/health
```

**Expected:** JSON response with status "healthy" and database stats

### Step 3: Set Up ngrok

1. Install ngrok if not already installed: https://ngrok.com/download
2. In a new terminal, run:
```bash
ngrok http 5001
```
3. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### Step 4: Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to: Phone Numbers → Manage → Active Numbers → [Your Toll-Free Number]
3. Under "Messaging Configuration", find "A message comes in"
4. Set webhook URL to: `https://your-ngrok-url.ngrok.io/webhook/twilio`
5. Set HTTP method to: `POST`
6. Save

**Note**: Using a toll-free number means no A2P 10DLC registration required!

### Step 5: Test Each Feature via SMS

Send these test messages to your Twilio number:

#### Water Logging
- "drank a bottle"
- "drank 16oz"
- "drank 500ml"

**Expected:** Response confirming water logged

#### Food Logging
- "I ate a sazon quesedilla"
- "ate krafthouse quesedilla"
- "had gsoy chicken teriyaki"

**Expected:** Response with logged macros

#### Gym Workouts
- "did bench press 135x5"
- "hit chest today"
- "squats 225x3"

**Expected:** Response confirming workout logged

#### Reminders
- "remind me to call mom at 5pm tomorrow"
- "remind me to buy groceries at 3pm"

**Expected:** Response with reminder confirmation and time

#### Todos
- "todo buy groceries"
- "I need to call mama at 5pm tomorrow" (should be reminder, not todo)

**Expected:** Response confirming todo added

### Step 6: Verify Data Storage

Check CSV files are created:
```bash
ls -la data/logs/
```

Files should exist:
- `food_logs.csv`
- `water_logs.csv`
- `gym_logs.csv`
- `reminders_todos.csv`

View data:
```bash
cat data/logs/food_logs.csv
cat data/logs/water_logs.csv
```

### Step 7: Test Food Matching Variations

Try various phrasings for your foods:
- "sazon quesedilla"
- "quesedilla from sazon"
- "ate sazon quesedilla"
- "had a sazon quesedilla"

All should match the same food with correct macros.

## 🐛 Troubleshooting

### App won't start
- Check `.env` file has all required variables
- Verify virtual environment is activated
- Check port 5001 is not in use

### Health endpoint fails
- Check app is running
- Verify database directory permissions
- Check for error messages in app output

### SMS not received
- Verify ngrok is running
- Check Twilio webhook URL is correct
- Verify Twilio account has credits
- Check Twilio Console → Monitor → Logs for errors

### Food not matching
- Check food exists in `data/wu_foods.json`
- Verify restaurant name matches exactly (case-sensitive)
- Try different phrasings
- Check app logs for NLP processing errors

### Rate limiting errors
- Gemini API has rate limits (5 req/min for Gemini, 30 req/min for Gemma)
- Code has exponential backoff, but may need to wait between tests
- Consider using Gemma model for higher quotas

## 📊 Success Criteria

- ✅ App starts without errors
- ✅ Health endpoint returns 200
- ✅ All 5 features work via SMS
- ✅ Data is stored in CSV files
- ✅ Food matching works for restaurant-specific foods
- ✅ Reminders send SMS at scheduled times
- ✅ Morning check-in sends SMS

## 🚀 Optional: Deploy to Render

If you want to deploy:

1. Push code to GitHub
2. Create Render account at [render.com](https://render.com)
3. Create new Web Service
4. Connect GitHub repository
5. Set environment variables from `.env` file
6. Deploy
7. Update Twilio webhook to Render URL

See `docs/DEPLOYMENT_GUIDE.md` for detailed instructions.

