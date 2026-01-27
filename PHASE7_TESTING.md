# Phase 7 Testing Guide

## Quick Checklist

### Step 1: Set Up Fitbit Developer App
**Important**: You need the **Fitbit Web API**, not the SDK. The SDK is for building apps that run ON Fitbit devices.

1. **Create a Fitbit Developer Account** (if you don't have one):
   - Go to [accounts.fitbit.com/signup](https://accounts.fitbit.com/signup)
   - Sign up with a Google account (Gmail or custom domain - Google Workspace accounts are NOT supported)
   - Log in to [dev.fitbit.com/apps](https://dev.fitbit.com/apps)

2. **Register Your Application**:
   - Go to [dev.fitbit.com/apps](https://dev.fitbit.com/apps)
   - Click **"Register a New App"** (upper right corner)
   - Fill in:
     - **Application Name**: e.g., "SMS Assistant"
     - **Description**: "Personal productivity assistant"
     - **Application Website**: Your deployment URL (or `http://localhost:5001` for testing)
     - **OAuth 2.0 Application Type**: **Personal**
     - **Callback URL**: `http://localhost:5001/dashboard/integrations/fitbit/callback` (or your production URL)
     - **Default Access Type**: **Read Only**
   - **Save** and note your **OAuth 2.0 Client ID** and **Client Secret**

3. **Add credentials to `.env`**:
   ```bash
   FITBIT_CLIENT_ID=your_client_id_here
   FITBIT_CLIENT_SECRET=your_client_secret_here
   ```

**Reference**: [Fitbit Web API Getting Started Guide](https://dev.fitbit.com/build/reference/web-api/developer-guide/getting-started)

### Step 2: Set Up Google Cloud Project
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable APIs:
   - Go to **APIs & Services** → **Library**
   - Search for "Google Calendar API" → **Enable**
   - (Optional) Search for "Google Fit API" → **Enable**
4. Create OAuth 2.0 credentials:
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - Application type: **Web application**
   - Name: "SMS Assistant"
   - **Authorized redirect URIs**: 
     - `http://localhost:5001/dashboard/integrations/google_calendar/callback`
     - (Add your production URL when deploying)
5. **Save** and note your **Client ID** and **Client Secret**
6. Add to `.env` (if not already there):
   ```bash
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   ```

### Step 3: Generate Encryption Key
1. Run this command:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. Copy the output and add to `.env`:
   ```bash
   ENCRYPTION_KEY=your_generated_key_here
   ```

### Step 4: Set Base URL
Add to `.env`:
```bash
BASE_URL=http://localhost:5001
```
(Use your production URL when deploying)

### Step 5: Test the Integration System

#### Test 1: Web Dashboard Integration Page
1. Start the app: `python app.py`
2. Log in to dashboard: `http://localhost:5001/` (homepage) or `http://localhost:5001/dashboard/login`
3. Click **🔗 Integrations** in the header
4. You should see:
   - Fitbit (with "Connect Fitbit" button)
   - Google Calendar (with "Connect Google Calendar" button)
   - Google Fit (marked "Coming Soon")

#### Test 2: Connect Fitbit
1. On integrations page, click **"Connect Fitbit"**
2. You'll be redirected to Fitbit's authorization page
3. Log in to Fitbit and click **"Allow"**
4. You'll be redirected back to your dashboard
5. Should see: "✓ Connected" and "Sync Now" button
6. Click **"Sync Now"** → Should sync workouts and sleep data
7. Check your database (via Supabase dashboard) → Should see gym_logs and sleep_logs from Fitbit

#### Test 3: Connect Google Calendar
1. On integrations page, click **"Connect Google Calendar"**
2. You'll be redirected to Google's authorization page
3. Select your Google account and click **"Allow"**
4. You'll be redirected back to your dashboard
5. Should see: "✓ Connected"
6. Calendar events are used for context (not stored as logs)

#### Test 4: SMS Commands
1. Send SMS: **"connect fitbit"**
   - Should respond with link to connect
2. Send SMS: **"sync my calendar"**
   - Should sync calendar events
3. Send SMS: **"list integrations"**
   - Should show connected integrations
4. Send SMS: **"disconnect fitbit"**
   - Should disconnect Fitbit

#### Test 5: Verify Data Sync
1. After connecting Fitbit, check your dashboard
2. Click a date on the calendar
3. If Fitbit synced workouts, they should appear in the stats
4. Check Supabase dashboard → `gym_logs` and `sleep_logs` tables
5. Should see entries with `notes` like "Synced from Fitbit: ..."

### Step 6: Test Webhooks (Optional - for production)
1. In Fitbit developer console, set webhook URL:
   - `https://your-domain.com/webhook/fitbit`
2. Fitbit will send a GET request to verify
3. After verification, Fitbit will POST webhooks when data changes
4. Check sync history in database → `sync_history` table

## Troubleshooting

### "Integration not available" error
- Check that `FITBIT_CLIENT_ID` and `FITBIT_CLIENT_SECRET` are set in `.env`
- Restart the app after adding credentials

### OAuth redirect fails
- Make sure redirect URI in `.env` matches exactly what you set in Fitbit/Google console
- For localhost: `http://localhost:5001/dashboard/integrations/fitbit/callback`
- No trailing slashes!

### "Failed to get valid access token"
- Token might be expired
- Try disconnecting and reconnecting
- Check that `ENCRYPTION_KEY` is set correctly

### Sync returns 0 items
- Check that you have data in Fitbit (workouts, sleep logs)
- Fitbit syncs last 30 days by default
- Try manual sync via dashboard

## What's Working

✅ **OAuth flows** - Connect/disconnect integrations  
✅ **Data syncing** - Fitbit workouts & sleep → database  
✅ **Token management** - Encryption, refresh, expiration  
✅ **Web dashboard** - Integration management UI  
✅ **SMS commands** - "connect fitbit", "sync calendar", etc.  
✅ **Sync history** - Track all sync operations  
✅ **Deduplication** - Avoids double-logging same data  

## Next Steps After Testing

Once Phase 7 is tested and working:
- Phase 8: Background Jobs & Services (scheduled syncs, reminders, etc.)
- Or continue with other features
