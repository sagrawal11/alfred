# Koyeb Deployment Guide - Complete Instructions

## Overview

This guide provides step-by-step instructions for deploying your SMS Assistant to Koyeb's free tier. Koyeb is a serverless platform that automatically builds and deploys your application from GitHub, providing a free hosting solution perfect for personal projects.

## What is Koyeb?

### Platform Overview

**Koyeb** is a serverless platform that:
- Automatically builds your code from GitHub
- Deploys and runs your application
- Provides a public HTTPS URL
- Handles all infrastructure (servers, networking, SSL)
- Offers a free tier perfect for personal projects

### How Koyeb Works

1. **Git-Driven Deployment**:
   - You push code to GitHub
   - Koyeb watches your repository
   - On every push, Koyeb automatically:
     - Clones your code
     - Detects language (Python)
     - Runs build commands
     - Starts your app
     - Exposes it on the internet

2. **Serverless Architecture**:
   - Your app runs on Koyeb's shared infrastructure
   - Scales automatically based on traffic
   - Free tier: Scales to zero after 1 hour of inactivity
   - Wakes up automatically when requests arrive

3. **Free Tier Specifications**:
   - **vCPU**: 0.1 (10% of one CPU core)
   - **RAM**: 512MB
   - **Storage**: 2GB SSD
   - **Regions**: Frankfurt (Germany) or Washington D.C. (USA)
   - **Cost**: $0/month (completely free!)

### Important: "Scales to Zero" Limitation

- After 1 hour of no requests, Koyeb puts your app to sleep
- When a new request arrives, Koyeb wakes it up (called "cold start")
- Cold start takes 5-30 seconds (app needs to boot up)
- **For SMS webhooks**: This works fine! Twilio waits up to 15 seconds
- If you text your app daily, it stays warm and responds instantly

## Prerequisites

Before starting deployment, ensure you have:

- ✅ GitHub account (free)
- ✅ Code pushed to GitHub repository
- ✅ Koyeb account (we'll create this)
- ✅ All environment variables ready (from your `.env` file)
- ✅ Toll-free number verified in Twilio

## Step 1: Prepare GitHub Repository

### 1.1 Verify Your Code is Ready

**Check Required Files Exist**:
```bash
cd "/Users/sarthak/Desktop/App Projects/sms_assistant"
ls -la
```

**Required Files**:
- ✅ `app.py` (main Flask application)
- ✅ `requirements.txt` (Python dependencies)
- ✅ `config.py` (configuration loader)
- ✅ `gemini_nlp.py` (NLP processor)
- ✅ `csv_database.py` (database manager)
- ✅ `communication_service.py` (Twilio service)
- ✅ `data/wu_foods.json` (food database)
- ✅ `data/gym_workouts.json` (gym database)
- ✅ `data/snacks.json` (snacks database)

### 1.2 Verify `.gitignore` is Correct

**Check `.gitignore` file**:
```bash
cat .gitignore
```

**Must Exclude**:
- `.env` (contains secrets - NEVER commit!)
- `sms_venv/` (virtual environment)
- `data/logs/*.csv` (local logs)
- `__pycache__/` (Python cache)

**Must Include** (in repository):
- `data/wu_foods.json` ✅
- `data/gym_workouts.json` ✅
- `data/snacks.json` ✅
- All source code files ✅

### 1.3 Initialize Git Repository (if not already done)

```bash
cd "/Users/sarthak/Desktop/App Projects/sms_assistant"

# Check if git is initialized
git status

# If not initialized, run:
git init
```

### 1.4 Create GitHub Repository

1. **Go to GitHub**: https://github.com
2. **Click**: "New repository" (green button)
3. **Repository Settings**:
   - **Name**: `sms-assistant` (or your preferred name)
   - **Description**: "Personal SMS Assistant using Twilio and Gemini AI"
   - **Visibility**: 
     - **Public** (required for Koyeb free tier)
     - OR **Private** (if you have GitHub Pro/paid account)
   - **DO NOT** check "Initialize with README" (you already have files)
   - **DO NOT** add .gitignore or license (you already have them)
4. **Click**: "Create repository"

### 1.5 Push Code to GitHub

```bash
cd "/Users/sarthak/Desktop/App Projects/sms_assistant"

# Add all files
git add .

# Commit
git commit -m "Initial commit: SMS Assistant ready for deployment"

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/sms-assistant.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Verify on GitHub**:
- Go to your repository on GitHub
- Check that all files are visible
- **CRITICAL**: Verify `.env` is NOT in the repository
- Verify `data/wu_foods.json`, `data/gym_workouts.json`, `data/snacks.json` ARE in the repository

## Step 2: Create Koyeb Account

### 2.1 Sign Up for Koyeb

1. **Go to Koyeb**: https://www.koyeb.com
2. **Click**: "Get Started" or "Sign Up" (top right)
3. **Sign Up Options**:
   - **Option A - GitHub** (Recommended):
     - Click "Sign up with GitHub"
     - Authorize Koyeb to access your GitHub
     - This automatically connects your GitHub account
   - **Option B - Email**:
     - Enter email and password
     - Verify email address
     - You'll connect GitHub later

### 2.2 Create Organization

After signup, Koyeb will prompt you to create an organization:

1. **Organization Name**: `sms-assistant` (or your preferred name)
2. **Click**: "Create Organization"
3. **Note**: Organizations are just containers for your services

### 2.3 Verify Account

- Check your email for verification (if using email signup)
- Click verification link if needed

## Step 3: Deploy to Koyeb

### 3.1 Create New Web Service

1. **In Koyeb Dashboard**:
   - Click "Create" button (top right)
   - OR click "Web Service" from dashboard

2. **Select Deployment Method**:
   - Choose **"GitHub"**
   - If not connected, click "Connect GitHub"
   - Authorize Koyeb to access your repositories

### 3.2 Select Repository

1. **Repository Selection**:
   - Koyeb shows your GitHub repositories
   - Find and select `sms-assistant` (or your repo name)
   - If not visible, click "Refresh" or check repository is public

2. **Branch Selection**:
   - Select branch: `main` (or `master` if that's your default)
   - This is the branch Koyeb will deploy from

3. **Click**: "Continue" or "Next"

### 3.3 Configure Service

#### 3.3.1 Basic Settings

1. **Service Name**:
   - Enter: `sms-assistant` (or your preferred name)
   - This becomes part of your URL: `sms-assistant-YOUR-ORG.koyeb.app`
   - Must be unique within your organization

2. **Instance Type**:
   - Select **"Free"** instance type
   - This gives you: 0.1 vCPU, 512MB RAM, 2GB storage
   - Perfect for our Flask app

3. **Region**:
   - Choose **"Washington, D.C."** (closest to US users)
   - OR **"Frankfurt"** (if you're in Europe)
   - Free tier only supports these two regions

#### 3.3.2 Build Settings

Koyeb auto-detects Python projects, but verify:

1. **Build Command**:
   - Should show: `pip install -r requirements.txt`
   - If not, enter it manually
   - This installs all Python dependencies

2. **Run Command**:
   - Should show: `python app.py`
   - If not, enter it manually
   - This starts your Flask application

3. **Port**:
   - Koyeb auto-detects from your app
   - Your app reads `PORT` from environment: `os.getenv('PORT', 5001)`
   - Koyeb automatically sets `PORT` environment variable
   - No manual configuration needed

#### 3.3.3 Environment Variables (CRITICAL)

**This is the most important step!**

1. **Click**: "Environment Variables" section
2. **Add Each Variable** (click "Add Variable" for each):

   **Twilio Configuration**:
   ```
   TWILIO_ACCOUNT_SID=AC7d0c5be2fb1a4237abdede7afd90a6aa
   TWILIO_AUTH_TOKEN=e7f12c899af2b0297866e7c3cb2f6786
   TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
   YOUR_PHONE_NUMBER=+1XXXXXXXXXX
   ```

   **Google Gemini API**:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

   **Communication Settings**:
   ```
   COMMUNICATION_MODE=sms
   NLP_ENGINE=gemini
   ```

   **App Settings**:
   ```
   MORNING_CHECKIN_HOUR=8
   EVENING_REMINDER_HOUR=20
   WATER_BOTTLE_SIZE_ML=500
   ```

3. **Important Notes**:
   - Copy values EXACTLY from your `.env` file
   - No spaces around the `=` sign
   - No quotes needed (Koyeb handles this)
   - Double-check each value for typos
   - These are secrets - Koyeb encrypts them

4. **Verify All Variables**:
   - Count: Should have 11 environment variables
   - Check each one is correct
   - Missing variables will cause app to fail

#### 3.3.4 Advanced Settings (Optional)

1. **Health Check Path**:
   - Enter: `/health`
   - Koyeb will check this endpoint to ensure app is running
   - Your app has this endpoint in `app.py`

2. **Auto-Deploy**:
   - Enable: "Auto-deploy on git push"
   - This automatically redeploys when you push to GitHub
   - Very convenient for updates

3. **Scaling**:
   - Leave default (free tier auto-scales, can't customize)
   - Scales to zero after 1 hour inactivity

### 3.4 Deploy

1. **Review**:
   - Service name is correct
   - Instance type is "Free"
   - Region is selected
   - Build command is correct
   - Run command is correct
   - All 11 environment variables are set

2. **Click**: "Deploy" or "Create Web Service"

3. **Monitor Build**:
   - Koyeb dashboard shows build logs in real-time
   - You'll see progress:
     ```
     Cloning repository...
     Installing dependencies...
     Building application...
     Starting application...
     Health check passing...
     ```

4. **Build Time**:
   - Typically takes 3-5 minutes
   - First deployment may take longer (installing dependencies)
   - Subsequent deployments are faster (cached dependencies)

5. **Watch for Errors**:
   - Red text indicates errors
   - Common issues:
     - Missing environment variable
     - Build command failed
     - App won't start
   - Check logs for specific error messages

### 3.5 Get Your URL

Once deployment succeeds:

1. **Service Status**:
   - Should show "Running" or "Live" (green indicator)
   - URL is displayed at top of service page

2. **Your Koyeb URL**:
   - Format: `https://sms-assistant-YOUR-ORG.koyeb.app`
   - This is your permanent URL (unless you change service name)
   - HTTPS is automatic (SSL certificate handled by Koyeb)

3. **Copy URL**:
   - You'll need this for Twilio webhook configuration
   - Save it somewhere safe

## Step 4: Verify Deployment

### 4.1 Check Service Status

1. **In Koyeb Dashboard**:
   - Service should show "Running" status
   - Green indicator means healthy
   - If red/yellow, check logs for errors

### 4.2 Test Health Endpoint

```bash
curl https://sms-assistant-YOUR-ORG.koyeb.app/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "service": "Alfred the Butler (Cloud)",
  "environment": "production",
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

**If Error**:
- Check Koyeb logs for startup errors
- Verify all environment variables are set
- Check app logs in Koyeb dashboard

### 4.3 Check Logs

1. **In Koyeb Dashboard**:
   - Click on your service
   - Click "Logs" tab
   - You should see:
     ```
     🚀 Starting Alfred the Butler on 0.0.0.0:PORT
     🌐 Health check: http://0.0.0.0:PORT/health
     ⏰ Background scheduler started
     ```

2. **Look for Errors**:
   - Red text indicates problems
   - Common errors:
     - Missing environment variable
     - Import errors
     - Database path issues

### 4.4 Test Webhook Endpoint (Optional)

```bash
curl -X POST https://sms-assistant-YOUR-ORG.koyeb.app/webhook/twilio \
  -d "From=%2B1234567890&Body=test&To=%2B1234567890"
```

**Expected**: TwiML XML response

**If Error**:
- Check Koyeb logs
- Verify app is running
- Check endpoint path is correct

## Step 5: Update Twilio Webhook

### 5.1 Get Your Koyeb URL

From Step 3.5, you should have your Koyeb URL:
```
https://sms-assistant-YOUR-ORG.koyeb.app
```

### 5.2 Update Twilio Configuration

1. **Go to Twilio Console**: https://console.twilio.com
2. **Navigate**: Phone Numbers → Manage → Active Numbers
3. **Click**: Your toll-free phone number
4. **Scroll**: To "Messaging Configuration" section
5. **Update Webhook**:
   - Find "A message comes in" field
   - **Old URL**: `https://your-ngrok-url.ngrok.io/webhook/twilio` (from local testing)
   - **New URL**: `https://sms-assistant-YOUR-ORG.koyeb.app/webhook/twilio`
   - Replace `sms-assistant-YOUR-ORG.koyeb.app` with your actual Koyeb URL
6. **HTTP Method**: Ensure it's set to **POST**
7. **Click**: "Save" or "Save Configuration"

### 5.3 Verify Configuration

- Webhook URL should now show your Koyeb URL
- Must include `/webhook/twilio` at the end
- HTTP method must be POST

## Step 6: Test Production Deployment

### 6.1 Test SMS (First Request)

**Important**: First request may take 5-30 seconds if app was sleeping (cold start)

1. **Send SMS**: Text your toll-free number: `Hello Alfred`
2. **Wait**: May take 5-30 seconds for first response (cold start)
3. **Expected**: Response from Alfred
4. **Subsequent Requests**: Will be instant (app stays warm)

### 6.2 Test All Features

**Water Logging**:
- Send: `drank a bottle`
- Expected: Confirmation with water logged

**Food Logging**:
- Send: `ate sazon quesedilla`
- Expected: Confirmation with macros

**Gym Workouts**:
- Send: `did bench press 135x5`
- Expected: Confirmation with workout logged

**Reminders**:
- Send: `remind me to test in 1 minute`
- Expected: Confirmation, then reminder SMS in 1 minute

**Todos**:
- Send: `todo buy groceries`
- Expected: Confirmation with todo added

### 6.3 Monitor Koyeb Logs

1. **In Koyeb Dashboard**:
   - Click on your service
   - Click "Logs" tab
   - Watch requests come in real-time
   - See processing steps:
     ```
     📱 Received SMS from +1234567890: "drank a bottle"
     🧠 Intent: water_log
     💧 Parsed: 500ml (1 bottle)
     ✅ Logged to database
     ```

### 6.4 Check Twilio Logs

1. **In Twilio Console**:
   - Monitor → Logs → Messaging
   - See all incoming/outgoing SMS
   - Check webhook delivery status
   - Verify no errors

## Step 7: Understanding Koyeb Behavior

### 7.1 Cold Starts

**What Happens**:
- App sleeps after 1 hour of inactivity
- First request wakes it up (5-30 second delay)
- Subsequent requests are instant

**For SMS Webhooks**:
- Twilio waits up to 15 seconds for response
- Cold start delay is acceptable
- If you use app daily, it stays warm

**Minimizing Cold Starts**:
- Use app daily (keeps it warm)
- Set up external cron to ping `/health` every 30 minutes
- Upgrade to paid tier for always-on service

### 7.2 Auto-Deployment

**How It Works**:
- Every git push to `main` branch triggers deployment
- Koyeb automatically:
  - Pulls latest code
  - Rebuilds application
  - Deploys new version
  - Health check ensures it works

**To Update Your App**:
1. Make changes locally
2. Commit: `git commit -am "Update feature"`
3. Push: `git push origin main`
4. Koyeb automatically deploys (watch dashboard)

### 7.3 Logs and Monitoring

**View Logs**:
- Koyeb dashboard → Service → Logs tab
- Real-time logs of all requests
- Search and filter capabilities

**Metrics**:
- Request count
- Response time
- CPU usage
- Memory usage
- Error rate

### 7.4 Storage (CSV Files)

**Understanding Storage**:
- CSV files stored in `data/logs/` directory
- Ephemeral storage (temporary)
- Persists during app runtime
- May be lost on redeploy (new container)

**For Production**:
- Consider backing up CSV files periodically
- Or upgrade to paid tier for persistent volumes
- Or use external database (PostgreSQL, etc.)

## Step 8: Troubleshooting

### Issue: Build Fails

**Symptoms**:
- Red error in build logs
- Deployment doesn't complete

**Common Causes**:
1. **Missing `requirements.txt`**:
   - Verify file exists in repository
   - Check all dependencies are listed

2. **Python Version**:
   - Koyeb uses Python 3.9+ by default
   - If you need specific version, add `runtime.txt`:
     ```
     python-3.9.16
     ```

3. **Build Command Error**:
   - Check `pip install -r requirements.txt` works locally
   - Verify all dependencies are available on PyPI

**Solutions**:
- Check build logs for specific error
- Test build locally: `pip install -r requirements.txt`
- Fix any dependency issues
- Push fix to GitHub

### Issue: App Won't Start

**Symptoms**:
- Build succeeds but app doesn't start
- Service shows "Error" status

**Common Causes**:
1. **Missing Environment Variable**:
   - Check all 11 variables are set
   - Verify no typos in variable names

2. **Port Configuration**:
   - App must read `PORT` from environment
   - Your code: `port = int(os.getenv('PORT', 5001))`
   - Koyeb sets `PORT` automatically

3. **Import Errors**:
   - Check all Python files are in repository
   - Verify imports work locally

**Solutions**:
- Check Koyeb logs for specific error
- Verify app runs locally: `python app.py`
- Fix any errors
- Push fix to GitHub (auto-redeploys)

### Issue: SMS Not Working

**Symptoms**:
- Send SMS but no response
- Twilio shows webhook delivery failed

**Common Causes**:
1. **Wrong Webhook URL**:
   - Verify URL in Twilio Console matches Koyeb URL
   - Must include `/webhook/twilio`

2. **App is Sleeping**:
   - First request after 1 hour takes 5-30 seconds
   - Twilio may timeout if delay is too long
   - Solution: Use app daily to keep warm

3. **Service Not Running**:
   - Check Koyeb dashboard - service should be "Running"
   - If "Error", check logs

**Solutions**:
- Verify webhook URL in Twilio Console
- Check Koyeb service status
- Check Koyeb logs for incoming requests
- Test webhook endpoint manually with curl
- Check Twilio logs for delivery errors

### Issue: Environment Variables Not Working

**Symptoms**:
- App starts but can't connect to Twilio/Gemini
- Errors about missing credentials

**Solutions**:
1. **Verify in Koyeb Dashboard**:
   - Service → Settings → Environment Variables
   - Check all 11 variables are present
   - Verify values are correct (no extra spaces)

2. **Check Variable Names**:
   - Must match exactly: `TWILIO_ACCOUNT_SID` (not `TWILIO_ACCOUNT_SID_`)
   - Case-sensitive

3. **Redeploy**:
   - After adding/changing variables, Koyeb auto-redeploys
   - Wait for deployment to complete
   - Test again

### Issue: Cold Start Timeouts

**Symptoms**:
- First SMS after inactivity times out
- Twilio shows webhook timeout error

**Solutions**:
1. **Keep App Warm**:
   - Use app daily
   - Or set up external cron to ping `/health` every 30 minutes

2. **External Cron Service**:
   - Use free service like cron-job.org
   - Set up job to ping: `https://your-app.koyeb.app/health`
   - Run every 30 minutes
   - Keeps app warm

3. **Upgrade to Paid Tier**:
   - Paid tier offers always-on service
   - No cold starts
   - Better for scheduled jobs

### Issue: Scheduled Jobs Not Running

**Symptoms**:
- Reminders not sending
- Morning check-in not working

**Cause**:
- App is sleeping, scheduler paused
- Scheduler only runs when app is active

**Solutions**:
1. **Keep App Warm** (see above)
2. **Use External Cron**:
   - Set up cron to ping `/health` every hour
   - Keeps app running
   - Scheduler stays active

3. **Upgrade to Paid Tier**:
   - Always-on service
   - Scheduler runs continuously

## Step 9: Updating Your Deployment

### 9.1 Making Code Changes

1. **Make Changes Locally**:
   ```bash
   # Edit files
   nano app.py
   # or use your editor
   ```

2. **Test Locally**:
   ```bash
   python app.py
   # Test changes work
   ```

3. **Commit and Push**:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin main
   ```

4. **Koyeb Auto-Deploys**:
   - Watch Koyeb dashboard
   - New deployment starts automatically
   - Takes 3-5 minutes
   - Service updates with new code

### 9.2 Updating Environment Variables

1. **In Koyeb Dashboard**:
   - Service → Settings → Environment Variables
   - Click variable to edit
   - Or add new variable
   - Click "Save"

2. **Auto-Redeploy**:
   - Koyeb automatically redeploys when variables change
   - Wait for deployment to complete
   - Test changes

### 9.3 Rolling Back

If something breaks:

1. **Revert Git Commit**:
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Koyeb Deploys Previous Version**:
   - Automatically redeploys with reverted code
   - Service returns to working state

## Step 10: Cost and Limits

### 10.1 Free Tier Limits

**Resources**:
- 0.1 vCPU (10% of one CPU core)
- 512MB RAM
- 2GB storage
- 1 free web service per organization

**Behavior**:
- Scales to zero after 1 hour inactivity
- Cold starts: 5-30 seconds
- Auto-deployment on git push

**Limitations**:
- Only 2 regions (Frankfurt, Washington D.C.)
- No custom scaling configuration
- No persistent volumes
- No worker services

### 10.2 When to Upgrade

**Consider Paid Tier If**:
- Need always-on service (no cold starts)
- Need more CPU/RAM
- Need persistent storage
- Need multiple services
- Need custom domains with better performance

**Paid Tier Pricing**:
- Starts at ~$7/month
- Always-on service
- More resources
- Better performance

### 10.3 Total Project Cost

**Free Tier (Koyeb)**:
- Hosting: $0/month
- Twilio number: ~$2-3/month
- Twilio SMS: ~$0.0075 per message
- **Total**: ~$4-5/month (light usage)

**Comparison to Render**:
- Render: $7/month + Twilio = ~$9-10/month
- Koyeb: $0/month + Twilio = ~$4-5/month
- **Savings**: ~$5/month with Koyeb!

## Success Checklist

Before considering deployment complete:

- ✅ Code pushed to GitHub
- ✅ Koyeb account created
- ✅ Service deployed successfully
- ✅ Health endpoint returns 200 OK
- ✅ All environment variables set correctly
- ✅ Twilio webhook updated to Koyeb URL
- ✅ SMS works (may have cold start delay)
- ✅ All features tested in production
- ✅ Logs show successful processing
- ✅ CSV files being created (check logs)

## Next Steps

After successful deployment:

1. **Monitor Usage**:
   - Check Koyeb dashboard regularly
   - Monitor logs for errors
   - Watch resource usage

2. **Keep App Warm** (Optional):
   - Set up external cron to ping `/health`
   - Or use app daily
   - Prevents cold starts

3. **Backup Data** (Optional):
   - Periodically backup CSV files
   - Or upgrade to paid tier for persistent storage

4. **Enjoy Your SMS Assistant!**:
   - Use it daily for tracking
   - All data stored in CSV files
   - Accessible via SMS anytime

---

**Need Help?**
- Check Koyeb logs for errors
- Verify all environment variables are set
- Test health endpoint: `curl https://your-app.koyeb.app/health`
- Review troubleshooting section above
- Check Twilio Console logs for webhook delivery status

