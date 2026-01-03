# Local Testing Guide - Complete Instructions

## Overview

This guide walks you through testing your SMS Assistant locally using ngrok to create a public URL that Twilio can reach. Once your toll-free number is verified, you'll be able to test all features via SMS before deploying to production.

## Prerequisites

Before starting, ensure you have:
- ✅ Toll-free number verified in Twilio Console
- ✅ Flask app runs locally (`python app.py` works)
- ✅ `.env` file configured with all credentials
- ✅ ngrok installed and authenticated

## Step 1: Verify Your Setup

### 1.1 Check Your `.env` File

Open your `.env` file and verify all required variables are set:

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=AC7d0c5be2fb1a4237abdede7afd90a6aa
TWILIO_AUTH_TOKEN=e7f12c899af2b0297866e7c3cb2f6786
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX  # Your toll-free number
YOUR_PHONE_NUMBER=+1XXXXXXXXXX     # Your personal phone number

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash  # or gemma-3-12b-it

# Communication Settings
COMMUNICATION_MODE=sms
NLP_ENGINE=gemini

# App Settings
MORNING_CHECKIN_HOUR=8
EVENING_REMINDER_HOUR=20
WATER_BOTTLE_SIZE_ML=500
```

**Important**: 
- Replace all placeholder values with your actual credentials
- Never commit `.env` to GitHub (it's in `.gitignore`)

### 1.2 Test Flask App Locally

1. **Open Terminal** and navigate to project directory:
   ```bash
   cd "/Users/sarthak/Desktop/App Projects/sms_assistant"
   ```

2. **Activate Virtual Environment**:
   ```bash
   source sms_venv/bin/activate
   ```
   You should see `(sms_venv)` in your terminal prompt.

3. **Start Flask App**:
   ```bash
   python app.py
   ```

4. **Expected Output**:
   ```
   ✅ Configuration validated successfully
   ✅ Twilio REST client initialized successfully (for scheduled messages)
   ✅ Database directory ensured: /Users/sarthak/Desktop/App Projects/sms_assistant/data/logs
   ✅ Food database exists: /Users/sarthak/Desktop/App Projects/sms_assistant/data/wu_foods.json
   🚀 Starting Alfred the Butler on localhost:5001
   🌐 Health check: http://localhost:5001/health
   📱 Twilio webhook: http://localhost:5001/webhook/twilio or /sms
   ⏰ Background scheduler started
   * Running on http://127.0.0.1:5001
   ```

5. **Test Health Endpoint** (in a new terminal):
   ```bash
   curl http://localhost:5001/health
   ```
   
   **Expected Response**:
   ```json
   {
     "status": "healthy",
     "service": "Alfred the Butler (Local)",
     "environment": "development",
     "communication": {
       "mode": "sms",
       "twilio_available": true
     },
     "database_stats": {
       "food_logs": 0,
       "water_logs": 0,
       "gym_logs": 0,
       "reminders_todos": 0
     }
   }
   ```

6. **Stop Flask App**: Press `Ctrl+C` in the terminal running the app

## Step 2: Set Up ngrok

### 2.1 Install ngrok (if not already installed)

**On macOS**:
```bash
brew install ngrok
```

**Or download from**: https://ngrok.com/download

### 2.2 Authenticate ngrok (One-Time Setup)

1. **Get Your Authtoken**:
   - Go to https://dashboard.ngrok.com/get-started/your-authtoken
   - Sign up or log in
   - Copy your authtoken (looks like: `2abc123def456ghi789jkl012mno345pq_6r7s8t9u0v1w2x3y4z5`)

2. **Configure ngrok**:
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
   ```
   Replace `YOUR_AUTHTOKEN_HERE` with your actual authtoken.

3. **Verify Configuration**:
   ```bash
   ngrok config check
   ```
   Should show: "Valid configuration file"

### 2.3 Start ngrok Tunnel

1. **Start Flask App** (in first terminal):
   ```bash
   cd "/Users/sarthak/Desktop/App Projects/sms_assistant"
   source sms_venv/bin/activate
   python app.py
   ```
   Keep this terminal open and running.

2. **Start ngrok** (in second terminal):
   ```bash
   ngrok http 5001
   ```

3. **Expected ngrok Output**:
   ```
   ngrok                                                                      
                                                                              
   Session Status                online                                      
   Account                       your-email@example.com (Plan: Free)        
   Version                       3.x.x                                      
   Region                        Europe (eu)                                 
   Forwarding                    https://abc123-def456.ngrok-free.app -> http://localhost:5001
                                                                              
   Connections                   ttl     opn     rt1     rt5     p50     p90  
                                 0       0       0.00    0.00    0.00    0.00
   ```

4. **Copy Your ngrok URL**:
   - Look for the line: `Forwarding https://abc123-def456.ngrok-free.app -> http://localhost:5001`
   - Copy the HTTPS URL: `https://abc123-def456.ngrok-free.app`
   - **Important**: This URL changes every time you restart ngrok (unless you have a paid plan)

5. **Access ngrok Web Interface** (Optional):
   - Open browser to: http://localhost:4040
   - This shows all incoming requests in real-time
   - Useful for debugging webhook calls

## Step 3: Configure Twilio Webhook

### 3.1 Get Your ngrok URL

From Step 2.3, you should have your ngrok URL. It looks like:
```
https://abc123-def456.ngrok-free.app
```

### 3.2 Update Twilio Webhook

1. **Go to Twilio Console**:
   - Visit https://console.twilio.com
   - Log in to your account

2. **Navigate to Phone Numbers**:
   - Click "Phone Numbers" in left sidebar
   - Click "Manage" → "Active Numbers"
   - Find and click on your **toll-free phone number**

3. **Configure Messaging Webhook**:
   - Scroll down to **"Messaging Configuration"** section
   - Find **"A message comes in"** field
   - Select **"Webhook"** from dropdown (not "TwiML Bin" or "TwiML App")
   - Enter your webhook URL:
     ```
     https://abc123-def456.ngrok-free.app/webhook/twilio
     ```
     Replace `abc123-def456.ngrok-free.app` with your actual ngrok URL
   - **HTTP Method**: Select **POST**
   - Click **"Save"** or **"Save Configuration"**

4. **Verify Configuration**:
   - The webhook URL should now show in the "A message comes in" field
   - Make sure it's the full URL including `/webhook/twilio`

### 3.3 Test Webhook Endpoint (Optional)

Before testing with SMS, verify the webhook endpoint works:

```bash
curl -X POST http://localhost:5001/webhook/twilio \
  -d "From=%2B1234567890&Body=test&To=%2B1234567890"
```

**Expected**: TwiML XML response like:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>Hello! I'm Alfred, your personal assistant...</Message>
</Response>
```

## Step 4: Test All Features via SMS

Now that everything is configured, test each feature by sending SMS to your toll-free number.

### 4.1 Test Water Logging

**Send SMS**: `drank a bottle`

**Expected Response**: 
```
✅ Logged 500ml of water! (1 bottle)
```

**Alternative Tests**:
- `drank 16oz`
- `drank 500ml`
- `had a bottle of water`

**Verify in Logs**:
- Check `data/logs/water_logs.csv` file
- Should see new entry with timestamp and amount

### 4.2 Test Food Logging

**Send SMS**: `ate sazon quesedilla`

**Expected Response**:
```
✅ Logged: Sazon Quesedilla
📊 Macros:
   Calories: XXX
   Protein: XXg
   Carbs: XXg
   Fat: XXg
```

**Alternative Tests**:
- `had krafthouse quesedilla`
- `ate gsoy chicken teriyaki`
- `had a sazon quesedilla`

**Verify in Logs**:
- Check `data/logs/food_logs.csv`
- Should see entry with food name, restaurant, and macros

**Test Unknown Food with Macros**:
- Send: `ate pizza 500 cal 20g protein 60g carbs 20g fat`
- Should log with provided macros even if not in database

### 4.3 Test Gym Workouts

**Send SMS**: `did bench press 135x5`

**Expected Response**:
```
✅ Logged workout: Bench Press
💪 Primary: Chest
📝 Sets: 5 reps at 135 lbs
```

**Alternative Tests**:
- `hit chest today`
- `squats 225x3`
- `did pullups 3 sets of 10`
- `leg day`

**Verify in Logs**:
- Check `data/logs/gym_logs.csv`
- Should see workout type, muscle groups, and details

### 4.4 Test Reminders

**Send SMS**: `remind me to test in 1 minute`

**Expected Response**:
```
✅ Reminder set: "test"
⏰ Time: [current time + 1 minute]
```

**Wait 1 Minute**:
- You should receive a reminder SMS at the scheduled time
- SMS will say: "⏰ Reminder: test"

**Alternative Tests**:
- `remind me to call mom at 5pm tomorrow`
- `remind me to buy groceries at 3pm`
- `set reminder for 2pm to take medicine`

**Verify in Logs**:
- Check `data/logs/reminders_todos.csv`
- Should see reminder entry with time and message

### 4.5 Test Todos

**Send SMS**: `todo buy groceries`

**Expected Response**:
```
✅ Todo added: "buy groceries"
📋 You have 1 active todo(s)
```

**Alternative Tests**:
- `I need to call mama` (should be todo, not reminder if no time specified)
- `add todo finish homework`
- `todo list` (should show all todos)

**Verify in Logs**:
- Check `data/logs/reminders_todos.csv`
- Should see todo entry with status "pending"

### 4.6 Test Intent Classification

**Test Reminder vs Todo**:
- `I need to call mama at 5pm tomorrow` → Should be **reminder** (has time)
- `I need to call mama` → Should be **todo** (no time)

**Test Food Variations**:
- `sazon quesedilla` → Should match Sazon restaurant
- `quesedilla from sazon` → Should match Sazon restaurant
- `ate a sazon quesedilla` → Should match Sazon restaurant

## Step 5: Monitor and Debug

### 5.1 Check Flask App Logs

In the terminal running `python app.py`, you'll see:
- Incoming webhook requests
- NLP processing results
- Database operations
- Any errors

**Example Output**:
```
📱 Received SMS from +1234567890: "drank a bottle"
🧠 Intent: water_log
💧 Parsed: 500ml (1 bottle)
✅ Logged to database
📤 Sending TwiML response
```

### 5.2 Check ngrok Web Interface

1. **Open Browser**: http://localhost:4040
2. **View Requests**: See all incoming requests in real-time
3. **Inspect Requests**: Click on any request to see:
   - Request headers
   - Request body (Twilio webhook data)
   - Response from your app
   - Response time

### 5.3 Check CSV Logs

**View Logs**:
```bash
# Water logs
cat data/logs/water_logs.csv

# Food logs
cat data/logs/food_logs.csv

# Gym logs
cat data/logs/gym_logs.csv

# Reminders and todos
cat data/logs/reminders_todos.csv
```

**Expected Format**:
- CSV files with headers
- One row per entry
- Timestamps in ISO format

### 5.4 Check Twilio Console Logs

1. **Go to Twilio Console**: https://console.twilio.com
2. **Navigate to**: Monitor → Logs → Messaging
3. **View**:
   - All incoming SMS
   - All outgoing SMS
   - Webhook delivery status
   - Any errors

## Step 6: Troubleshooting

### Issue: Flask App Won't Start

**Symptoms**:
- Error when running `python app.py`
- Port 5001 already in use

**Solutions**:
1. **Check if another instance is running**:
   ```bash
   lsof -i :5001
   ```
   Kill any processes using port 5001

2. **Check `.env` file**:
   - Ensure all required variables are set
   - No typos in variable names

3. **Check virtual environment**:
   ```bash
   source sms_venv/bin/activate
   pip install -r requirements.txt
   ```

### Issue: ngrok Not Working

**Symptoms**:
- `ngrok http 5001` fails
- Authentication error

**Solutions**:
1. **Re-authenticate ngrok**:
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```

2. **Check ngrok version**:
   ```bash
   ngrok version
   ```
   Update if outdated: `brew upgrade ngrok`

3. **Verify Flask is running**:
   - Flask app must be running on port 5001
   - Check: `curl http://localhost:5001/health`

### Issue: SMS Not Received

**Symptoms**:
- Send SMS but no response
- Twilio shows webhook delivery failed

**Solutions**:
1. **Check ngrok is running**:
   - Verify ngrok terminal shows "online"
   - Check URL matches Twilio webhook

2. **Check Flask app is running**:
   - Verify app is running in terminal
   - Check for errors in logs

3. **Check Twilio webhook URL**:
   - Go to Twilio Console → Phone Numbers
   - Verify webhook URL matches ngrok URL
   - Must include `/webhook/twilio`

4. **Check ngrok web interface**:
   - Open http://localhost:4040
   - See if requests are coming through
   - Check response status codes

5. **Check Twilio logs**:
   - Twilio Console → Monitor → Logs
   - Look for webhook delivery errors
   - Check error messages

### Issue: Wrong Intent Classification

**Symptoms**:
- "I need to call mama at 5pm" classified as todo instead of reminder

**Solutions**:
1. **Check Gemini API key**:
   - Verify `GEMINI_API_KEY` in `.env`
   - Check API quota (free tier: 20 requests/day for Gemini)

2. **Check model selection**:
   - Try `GEMINI_MODEL=gemma-3-12b-it` for higher quota
   - Or `GEMINI_MODEL=gemini-2.5-flash` for better accuracy

3. **Check rate limiting**:
   - Code has built-in delays (12s for Gemini, 2s for Gemma)
   - Wait between test messages

### Issue: Food Not Matching

**Symptoms**:
- "ate sazon quesedilla" not recognized
- Response says food not found

**Solutions**:
1. **Check food database**:
   ```bash
   cat data/wu_foods.json
   ```
   - Verify food exists in database
   - Check restaurant name matches exactly

2. **Test variations**:
   - Try: "sazon quesedilla"
   - Try: "quesedilla from sazon"
   - Try: "ate a sazon quesedilla" (typo)

3. **Check NLP logs**:
   - Look in Flask app terminal
   - See what Gemini parsed from message

### Issue: CSV Files Not Created

**Symptoms**:
- No CSV files in `data/logs/`
- App says files don't exist

**Solutions**:
1. **Check directory exists**:
   ```bash
   ls -la data/logs/
   ```
   Directory should exist (created automatically)

2. **Check permissions**:
   ```bash
   chmod -R 755 data/logs/
   ```

3. **Check app logs**:
   - Look for "Database directory ensured" message
   - Check for any permission errors

## Step 7: Clean Up After Testing

### 7.1 Stop Services

1. **Stop Flask App**: 
   - In terminal running app, press `Ctrl+C`

2. **Stop ngrok**:
   - In terminal running ngrok, press `Ctrl+C`

### 7.2 Update Twilio Webhook (Before Deployment)

When you're ready to deploy to production:
1. Deploy to Koyeb (see `KOYEB_DEPLOYMENT.md`)
2. Get your Koyeb URL
3. Update Twilio webhook to point to Koyeb URL instead of ngrok

### 7.3 Keep ngrok Running During Testing

**Important**: 
- Keep both Flask app and ngrok running while testing
- If you close either, SMS won't work
- ngrok URL changes each restart (unless paid plan)

## Success Checklist

Before moving to production deployment, verify:

- ✅ Flask app starts without errors
- ✅ Health endpoint returns 200 OK
- ✅ ngrok tunnel is active and forwarding
- ✅ Twilio webhook configured correctly
- ✅ Water logging works via SMS
- ✅ Food logging works (with restaurant matching)
- ✅ Gym workouts are logged correctly
- ✅ Reminders send SMS at scheduled time
- ✅ Todos are added and can be listed
- ✅ CSV files are created in `data/logs/`
- ✅ All features work as expected

## Next Steps

Once local testing is complete and all features work:

1. **Review** `INSTRUCTIONS/KOYEB_DEPLOYMENT.md` for production deployment
2. **Prepare** GitHub repository (push code to GitHub)
3. **Deploy** to Koyeb using the deployment guide
4. **Update** Twilio webhook to point to production URL
5. **Test** all features in production

---

**Need Help?**
- Check Flask app logs for errors
- Check ngrok web interface (http://localhost:4040) for request details
- Check Twilio Console logs for webhook delivery status
- Review troubleshooting section above

