# Supabase Auth Migration Guide

## Overview

This migration implements a **hybrid Supabase Auth approach**:
- **Supabase Auth** handles authentication (phone OTP, email/password, sessions)
- **Custom users table** stores app-specific data (name, timezone, preferences)
- Linked via `auth_user_id` foreign key

## Step 1: Run Database Migration

1. Open Supabase Dashboard → SQL Editor
2. Run the migration file: `supabase_schema_auth_migration.sql`
3. This adds:
   - `auth_user_id` column to `users` table
   - Indexes for performance
   - Helper functions

## Step 2: Verify Supabase Auth Configuration

1. **Enable Phone Authentication:**
   - Go to Supabase Dashboard → Authentication → Providers
   - Enable "Phone" provider
   - Configure Twilio Messaging Service (already done)

2. **Enable Email Authentication:**
   - Go to Authentication → Providers
   - Ensure "Email" provider is enabled
   - Configure email settings if needed

3. **Verify Twilio Integration:**
   - Check that Twilio Messaging Service is connected
   - Test that OTP codes are being sent

## Step 3: Environment Variables

Make sure your `.env` has:
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_anon_key  # Anon key works for auth operations
```

**Note:** For admin operations, you might need `SUPABASE_SERVICE_ROLE_KEY`, but for standard auth (sign_up, sign_in), the anon key is sufficient.

## Step 4: Test the Migration

### Test Registration:
1. Go to landing page
2. Click "Sign Up"
3. Fill in: email, password, name, phone number
4. Submit
5. Should receive OTP via SMS
6. Enter OTP to verify

### Test Login:
1. Click "Login"
2. Enter email and password
3. Should log in successfully

## What Changed

### Backend:
- ✅ `AuthManager` now uses Supabase Auth
- ✅ Registration creates user in Supabase Auth + custom users table
- ✅ Login uses Supabase Auth email/password
- ✅ Phone OTP handled by Supabase Auth
- ✅ Session management uses Supabase JWT tokens (stored in Flask session)

### Database:
- ✅ Added `auth_user_id` column to `users` table
- ✅ All existing foreign keys still work (they reference `users.id`)

### Frontend:
- ✅ Modals handle JSON responses
- ✅ Proper error display
- ✅ Redirect handling

## Migration Notes

- **Existing Users:** Users created before this migration will have `auth_user_id = NULL`
- **Gradual Migration:** You can migrate existing users later by creating Supabase Auth accounts for them
- **Backward Compatibility:** Legacy methods still work but redirect to new Supabase Auth methods

## Troubleshooting

### "User already registered" error:
- Check if email/phone exists in Supabase Auth
- Check if email/phone exists in custom users table
- Both need to be unique

### OTP not sending:
- Verify Twilio Messaging Service is connected in Supabase
- Check phone number format (must be E.164: +1234567890)
- Check Supabase Auth logs for errors

### Login fails:
- Verify user exists in both Supabase Auth and custom users table
- Check that `auth_user_id` is properly linked
- Verify password is correct

## Next Steps

1. Test registration and login flows
2. Test phone OTP verification
3. Migrate existing users (if any) by creating Supabase Auth accounts
4. Consider adding password reset flow using Supabase Auth email links
