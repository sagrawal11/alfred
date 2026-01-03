# 🚀 Deploy SMS Assistant to Render

## **🎯 What We're Deploying:**

- **Flask App**: SMS Assistant backend
- **Twilio Integration**: SMS handling (TwiML + REST API)
- **NLP Processing**: Google Gemini API
- **Database**: CSV files (simple, portable storage)

## **💰 Pricing:**

- **Starter Plan**: $7/month (512MB RAM, 0.5 CPU, always-on)
- **Bandwidth**: $15 per 100 GB (minimal for SMS webhooks)
- **Total**: ~$7/month for 24/7 operation

## **🌐 Render Setup Steps:**

### **Step 1: Create Render Account**
1. Go to [render.com](https://render.com)
2. Click "Get Started" → Sign up with GitHub
3. Verify your email

### **Step 2: Connect GitHub Repository**
1. **Dashboard**: Click "New +" → "Web Service"
2. **Connect**: Your GitHub repository
3. **Repository**: Select `sms_assistant` (or your repo name)

### **Step 3: Configure Web Service**
1. **Name**: `sms-assistant` (or your preferred name)
2. **Environment**: `Python 3`
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `python app.py`
5. **Plan**: **Starter** ($7/month) - Required for 24/7 operation
   - ⚠️ Free tier sleeps after 15 minutes (not suitable for webhooks)

### **Step 4: Set Environment Variables**
Click "Environment" tab and add all variables from your `.env` file:

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX (your toll-free number)
YOUR_PHONE_NUMBER=+1XXXXXXXXXX (your personal number)

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash (or gemma-3-12b-it)

# Communication
COMMUNICATION_MODE=sms
NLP_ENGINE=gemini

# App Settings
MORNING_CHECKIN_HOUR=8
EVENING_REMINDER_HOUR=20
WATER_BOTTLE_SIZE_ML=500

# Render automatically sets these:
PORT=10000
RENDER=true
```

### **Step 5: Deploy**
1. **Click**: "Create Web Service"
2. **Wait**: Build completes (5-10 minutes)
3. **Get URL**: Your app will be at `https://sms-assistant.onrender.com` (or your chosen name)

## **🔧 Update Twilio Webhook:**

1. **Twilio Console**: Go to Phone Numbers → Manage → Active Numbers
2. **Click**: Your toll-free phone number
3. **Messaging**: Find "A message comes in"
4. **Webhook URL**: Update to your Render URL
   - **URL**: `https://sms-assistant.onrender.com/webhook/twilio`
   - **HTTP Method**: POST
5. **Save**: Configuration

**Important**: Replace `sms-assistant` with your actual Render service name if different.

## **🧪 Test Your Deployment:**

### **1. Health Check:**
```bash
curl https://sms-assistant.onrender.com/health
```

**Expected**: JSON response with `"status": "healthy"`

### **2. Test SMS:**
1. **Text your toll-free number**: Your Twilio number
2. **Message**: "drank a bottle"
3. **Expected**: Response confirming water logged
4. **Check logs**: View in Render dashboard to see processing

## **📊 Monitoring:**

- **Logs**: View in Render dashboard
- **Health**: `/health` endpoint
- **Uptime**: Render monitors automatically
- **Scaling**: Auto-scales based on traffic

## **💰 Cost Breakdown:**

- **Render Starter Plan**: $7/month (always-on, 512MB RAM, 0.5 CPU)
- **Twilio Toll-Free Number**: ~$2-3/month
- **Twilio SMS**: $0.0075 per message (~$0.23/month for 30 messages)
- **Bandwidth**: Minimal (SMS webhooks are tiny)
- **Total**: ~$9-10/month for 24/7 operation

**Why Starter Plan?**
- Free tier sleeps after 15 minutes (webhooks won't work)
- Starter plan keeps your app always-on for reliable SMS handling

## **🚨 Troubleshooting:**

### **Build Fails:**
- Check requirements.txt
- Verify Python version (3.12)
- Check build logs

### **App Won't Start:**
- Check environment variables
- Verify start command
- Check app logs

### **SMS Not Working:**
- Verify webhook URL in Twilio Console
- Check app logs for errors
- Test webhook endpoint manually
- Ensure TwiML response is returned correctly

## **🎉 Success Indicators:**

✅ **App deploys** without errors
✅ **Health endpoint** responds
✅ **Twilio webhook** receives messages
✅ **TwiML responses** sent back automatically
✅ **Scheduled reminders** work via REST API
✅ **Gemini NLP** processing messages correctly

---

**Need help? Check Render logs or create an issue in the repository!**
