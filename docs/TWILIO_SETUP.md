# 📱 Twilio Setup Guide for Alfred the Butler

## **🎯 What We're Building**

A personal SMS assistant that:
- **Receives SMS** via Twilio webhook (TwiML responses)
- **Sends scheduled reminders** via Twilio REST API
- **Cost**: ~$1-2/month for your usage

## **🚀 Step-by-Step Setup**

### **Step 1: Create Twilio Account**

1. Go to [twilio.com](https://www.twilio.com)
2. Click "Get a free API key" or "Sign Up"
3. Create your account with email/password
4. Verify your email address and phone number

### **Step 2: Get Your Credentials**

1. **Account SID**: Found on your Twilio Console Dashboard
2. **Auth Token**: Click "Show" next to Auth Token (keep this secret!)
3. Copy both values - you'll need them for your `.env` file

### **Step 3: Buy a Toll-Free Number**

1. **Phone Numbers**: Click "Phone Numbers" → "Manage" → "Buy a number"
2. **Select**: Choose a **toll-free number** (800, 888, 877, 866, 855, 844, or 833)
3. **Capabilities**: Make sure SMS is enabled
4. **Cost**: ~$2-3/month + $0.0075 per SMS (trial accounts get $15.50 free credit)
5. **Why toll-free?** 
   - No A2P 10DLC registration required (saves $8 registration + $1.50/month)
   - Can start sending SMS immediately
   - Perfect for personal projects and students

### **Step 4: Configure Webhook**

1. **Phone Numbers**: Click on your purchased number
2. **Messaging**: Find "A message comes in"
3. **Webhook URL**: Set to `https://your-app.com/webhook/twilio` or `https://your-app.com/sms`
4. **HTTP Method**: POST
5. **Save**: Click "Save Configuration"

**Note**: For local testing, use ngrok:
```bash
ngrok http 5001
# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Use: https://abc123.ngrok.io/webhook/twilio
```

### **Step 5: Update Environment Variables**

Add these to your `.env` file:

```bash
# Communication Mode
COMMUNICATION_MODE=sms

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Your phone number (for scheduled reminders)
YOUR_PHONE_NUMBER=+1234567890
```

### **Step 6: Test the System**

1. **Start the app**: `python app.py`
2. **Check health**: Visit `http://localhost:5001/health`
3. **Send SMS**: Text your Twilio number
4. **Receive response**: Get SMS back from Alfred!

## **💰 Cost Breakdown**

### **Monthly Costs (Toll-Free Number):**
- **Toll-Free Number**: ~$2-3/month
- **SMS (100 messages)**: $0.75
- **Total**: ~$2.75-3.75/month

### **For Your Usage (10-20 messages/day):**
- **300-600 messages/month**
- **SMS cost**: $2.25 - $4.50
- **Total monthly**: $4.25 - $7.50

### **Why Toll-Free is Better:**
- **No A2P 10DLC registration**: Saves $8 one-time + $1.50/month = $9.50 first month, $1.50/month ongoing
- **Toll-free cost**: $2-3/month
- **Net savings**: Actually cheaper for personal projects!

**Note**: Twilio trial accounts get $15.50 free credit, which covers ~2,000 SMS messages!

## **📱 How It Works**

### **Incoming SMS Flow (TwiML):**
1. **User texts** your Twilio number
2. **Twilio webhook** sends POST to `/webhook/twilio` or `/sms`
3. **Alfred processes** the message using NLP
4. **TwiML response** returned (Twilio automatically sends SMS)
5. **User receives** SMS from Alfred the Butler

### **Scheduled Reminders Flow (REST API):**
1. **Reminder due** (checked every minute)
2. **Twilio REST API** sends SMS proactively
3. **User receives** reminder SMS

## **🔧 Configuration Options**

### **Communication Modes:**

#### **1. SMS Only (`COMMUNICATION_MODE=sms`) - RECOMMENDED**
- Uses TwiML for incoming SMS responses
- Uses REST API for scheduled reminders
- Most reliable option

#### **2. Push Only (`COMMUNICATION_MODE=push`)**
- Only push notifications
- No SMS capability
- Free (Pushover)

#### **3. Hybrid (`COMMUNICATION_MODE=hybrid`)**
- Tries SMS first
- Falls back to push notifications if SMS fails
- Best reliability

## **🧪 Testing Your Setup**

### **1. Check Communication Status:**
```bash
curl http://localhost:5001/health
```

Look for:
```json
{
  "communication": {
    "mode": "sms",
    "twilio_available": true,
    "pushover_available": false
  }
}
```

### **2. Test SMS:**
1. Text your Twilio number: "Hello Alfred"
2. You should receive a response
3. Check app logs for success/failure

### **3. Test Scheduled Reminder:**
1. Send: "remind me to test in 1 minute"
2. Wait 1 minute
3. Should receive reminder SMS

## **🚨 Troubleshooting**

### **Common Issues:**

#### **1. "Twilio client not initialized"**
- Check your credentials in `.env`
- Verify Account SID and Auth Token
- Ensure phone number is in E.164 format (+1XXXXXXXXXX)

#### **2. "Webhook not receiving messages"**
- Verify webhook URL in Twilio dashboard
- Check if your app is accessible from internet
- For local testing, use ngrok
- Test webhook endpoint manually

#### **3. "SMS not sending"**
- Check phone number format (+1XXXXXXXXXX)
- Verify account has sufficient credits
- Check Twilio logs in Console
- Ensure webhook returns valid TwiML

#### **4. "TwiML response not working"**
- Ensure you're returning `str(response)` not JSON
- Check Content-Type header (should be `text/xml`)
- Verify MessagingResponse is imported correctly

### **Debug Commands:**
```bash
# Check communication service status
curl http://localhost:5001/health

# Test webhook manually
curl -X POST http://localhost:5001/webhook/twilio \
  -d "From=%2B1234567890&Body=test&To=%2B1234567890"
```

## **🎉 Success Indicators**

✅ **Twilio REST client initialized successfully** in app logs  
✅ **Health endpoint shows** `"twilio_available": true`  
✅ **SMS received** when you text the number  
✅ **TwiML response sent** back via SMS automatically  
✅ **Scheduled reminders work** via REST API  

## **🚀 Next Steps**

1. **Deploy to cloud** (Render/Railway) for 24/7 availability
2. **Set up webhook** to point to your cloud URL
3. **Test thoroughly** with various message types
4. **Monitor costs** in Twilio Console
5. **Enjoy texting** Alfred the Butler directly! 📱✨

---

**Need help? Check [Twilio docs](https://www.twilio.com/docs) or create an issue in the repository!**

