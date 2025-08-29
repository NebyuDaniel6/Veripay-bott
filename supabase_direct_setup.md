# Supabase Database Setup - Direct Method

Since the direct connection is timing out, let's set up the database tables directly in your Supabase dashboard.

## 🔧 **Step 1: Set Up Tables in Supabase Dashboard**

1. **Go to your Supabase Dashboard:**
   - Visit: https://supabase.com/dashboard
   - Select your project: `mnxschqpuppxlcmstvke`

2. **Go to SQL Editor:**
   - Click on "SQL Editor" in the left sidebar
   - Click "New query"

3. **Run the SQL Script:**
   - Copy the contents of `supabase_setup.sql`
   - Paste it into the SQL Editor
   - Click "Run" to execute

## 🔧 **Step 2: Verify Tables Created**

1. **Go to Table Editor:**
   - Click on "Table Editor" in the left sidebar
   - You should see these tables created:
     - `users`
     - `restaurants`
     - `tables`
     - `table_assignments`
     - `transactions`
     - `bank_statements`
     - `reconciliation_reports`
     - `system_logs`

## 🔧 **Step 3: Test Connection**

Once the tables are created, we can test the connection with a simpler approach.

## 🔧 **Alternative: Use Connection Pooling**

If direct connection doesn't work, try the connection pooling URL from your Supabase dashboard:

1. **Go to Settings → Database**
2. **Look for "Connection pooling"**
3. **Use the pooler connection string instead**

## 🔧 **Next Steps**

After setting up the tables in the dashboard, we'll:
1. Test the connection
2. Deploy to Railway
3. Get your bot live!

**Please set up the tables in your Supabase dashboard first, then let me know when you're ready to proceed.** 