# VeriPay Bot - Comprehensive Testing Checklist
**Date:** 2025-01-08
**All 4 Tasks Complete - Final Testing**

## ✅ Test Status Legend
- ⏳ Pending
- ✅ Passed
- ❌ Failed

---

## 1. BASIC FUNCTIONALITY

### 1.1 Bot Start & Language Selection
- [ ] Send `/start` command
- [ ] Verify language selection menu appears (English/Amharic)
- [ ] Select English
- [ ] Verify main menu appears with:
  - 🔑 Login
  - Register as Restaurant Admin
  - Register as Waiter
  - Help
  - Change Language

### 1.2 Login/Logout (Task 1)
- [ ] Click "🔑 Login" without account → Should show "No account found"
- [ ] After registration, click Logout
- [ ] Click "🔑 Login" → Should restore session
- [ ] Verify correct dashboard appears based on role
- [ ] Verify all previous data is intact

---

## 2. SUPER ADMIN FEATURES

### 2.1 Super Admin Access
- [ ] Start bot with SUPER_ADMIN_ID
- [ ] Verify Super Admin dashboard appears automatically
- [ ] Verify menu shows:
  - Pending Restaurant Approvals
  - Pending Waiter Approvals
  - View Statistics
  - Logout

### 2.2 Restaurant Approval
- [ ] View pending restaurants
- [ ] Approve a restaurant
- [ ] Verify restaurant admin gets notification
- [ ] Reject a restaurant
- [ ] Verify rejection notification

### 2.3 Waiter Approval
- [ ] View pending waiters
- [ ] Approve a waiter
- [ ] Verify waiter gets notification
- [ ] Reject a waiter
- [ ] Verify rejection notification

### 2.4 Statistics
- [ ] View system statistics
- [ ] Verify counts for:
  - Total transactions
  - Total restaurants
  - Total waiters
  - Pending approvals

---

## 3. RESTAURANT ADMIN FEATURES

### 3.1 Registration
- [ ] Click "Register as Restaurant Admin"
- [ ] Enter restaurant name
- [ ] Enter phone number
- [ ] Submit registration
- [ ] Verify "pending approval" message
- [ ] Wait for Super Admin approval
- [ ] Verify dashboard appears after approval

### 3.2 Restaurant Admin Dashboard
- [ ] Verify menu shows:
  - Manage Waiters
  - View Transactions
  - Reconciliation
  - Settings
  - Logout

### 3.3 Transaction History with Pagination (Task 2)
- [ ] Click "View Transactions"
- [ ] Verify page shows "Page X of Y"
- [ ] Verify shows "Total: N transactions"
- [ ] Verify shows up to 20 transactions per page
- [ ] Click "➡️ Next" → Should go to page 2
- [ ] Click "⬅️ Prev" → Should go back to page 1
- [ ] Verify each transaction shows:
  - Amount
  - Bank
  - Waiter ID
  - Date

### 3.4 Reconciliation
- [ ] Click "Reconciliation"
- [ ] Upload bank statement (PDF/CSV)
- [ ] Verify statement parsed successfully
- [ ] Run reconciliation
- [ ] Download reconciliation report
- [ ] Open PDF and verify:
  - **Waiter column shows waiter names/IDs** (Task 3)
  - Transaction numbers listed
  - Matched vs Unmatched status
  - All transactions included

### 3.5 Weekly Report Download (Task 4)
- [ ] Click "Download Weekly Report" (in reconciliation menu)
- [ ] Verify PDF generated with:
  - Restaurant name
  - Generated timestamp
  - Total transaction count
  - **Total amount in ETB**
  - Table with: Date, Tx Number, Amount, **Waiter**, Bank
  - All waiter names/IDs shown correctly
- [ ] Verify success message shows:
  - "X transactions exported"
  - "Y transactions archived"
  - "Start fresh for new week" message

### 3.6 Verify Archiving (Task 4)
- [ ] After weekly report download, go to "View Transactions"
- [ ] Verify previously shown transactions are now GONE
- [ ] Verify page shows empty or only new transactions
- [ ] Add a new transaction (via waiter)
- [ ] Verify new transaction appears
- [ ] Verify old archived transactions don't appear

---

## 4. WAITER FEATURES

### 4.1 Registration
- [ ] Click "Register as Waiter"
- [ ] Enter restaurant code/name
- [ ] Submit registration
- [ ] Verify "pending approval" message
- [ ] Wait for approval
- [ ] Verify waiter dashboard appears

### 4.2 Waiter Dashboard
- [ ] Verify menu shows:
  - 📸 Capture Payment
  - 📒 My Transactions
  - Help
  - Logout

### 4.3 Payment Capture with OCR
- [ ] Click "📸 Capture Payment"
- [ ] Select bank (CBE, Telebirr, Dashen, Abyssinia)
- [ ] Upload receipt photo
- [ ] Verify OCR processing message
- [ ] Verify extracted data shows:
  - Transaction ID/Reference
  - Amount
  - Date
  - Time
  - Payer
  - Receiver
- [ ] Verify "View Full OCR" option works
- [ ] Confirm transaction
- [ ] Verify success message

### 4.4 Transaction History with Pagination (Task 2)
- [ ] Click "📒 My Transactions"
- [ ] Verify page shows "Page X of Y"
- [ ] Verify shows "Total: N transactions"
- [ ] Verify shows up to 20 transactions per page
- [ ] Verify each transaction shows:
  - Amount (ETB)
  - Bank
  - Date
  - Reference number
- [ ] If more than 20 transactions:
  - [ ] Click "➡️ Next" → Should go to page 2
  - [ ] Click "⬅️ Prev" → Should go back to page 1
  - [ ] Verify navigation buttons only show when needed

---

## 5. EDGE CASES & ERROR HANDLING

### 5.1 Login Edge Cases
- [ ] Try login before registration → Should show error
- [ ] Try login with NEW_USER role → Should show "complete registration first"
- [ ] Login after bot restart → Should restore correctly

### 5.2 Pagination Edge Cases
- [ ] Test with exactly 20 transactions → No "Next" button
- [ ] Test with 0 transactions → Shows "No transactions" message
- [ ] Test with 1 transaction → No pagination buttons
- [ ] Test with 21 transactions → "Next" button appears

### 5.3 Archiving Edge Cases
- [ ] Try weekly report with 0 transactions → Should show error
- [ ] Download report twice in a row → Second download should show 0 transactions
- [ ] Verify counts are correct after archiving

### 5.4 Role Permissions
- [ ] Waiter tries to access Restaurant Admin menu → Should deny
- [ ] Restaurant Admin tries to access Super Admin menu → Should deny
- [ ] Verify logout removes access immediately

---

## 6. DATA INTEGRITY

### 6.1 Database Consistency
- [ ] Verify transactions have waiter_id set
- [ ] Verify archived flag is 0 for new transactions
- [ ] Verify archived flag is 1 after weekly report
- [ ] Verify archived_at timestamp is set
- [ ] Verify no transactions are deleted (data preserved)

### 6.2 Count Accuracy
- [ ] Count active transactions in UI
- [ ] Count archived transactions in DB
- [ ] Verify total = active + archived
- [ ] Verify pagination total matches actual count

---

## 7. CRITICAL FEATURES VERIFICATION

### ✅ Task 1: Login Button
- [ ] Login button appears on main menu (top position)
- [ ] Login works for all roles (Super Admin, Restaurant Admin, Waiter)
- [ ] Session restored correctly
- [ ] All data preserved after logout/login
- [ ] Success message shows correct role

### ✅ Task 2: Pagination
- [ ] Waiter transactions paginated (20/page)
- [ ] Restaurant transactions paginated (20/page)
- [ ] Page numbers display correctly (Page X of Y)
- [ ] Total count displays correctly
- [ ] Prev/Next buttons work
- [ ] Buttons hide when not needed

### ✅ Task 3: Waiter ID in Reconciliation
- [ ] Reconciliation report has "Waiter" column
- [ ] Shows waiter full name (if available)
- [ ] Shows waiter username (fallback)
- [ ] Shows "W{id}" (final fallback)
- [ ] Works for matched transactions
- [ ] Works for unmatched transactions
- [ ] Easy to identify problematic transaction sources

### ✅ Task 4: Weekly Reset
- [ ] Weekly report generates PDF successfully
- [ ] Report includes all active transactions
- [ ] Report shows waiter for each transaction
- [ ] Total amount calculates correctly
- [ ] Transactions archived after download
- [ ] Archived transactions don't show in active views
- [ ] New transactions after archiving work correctly
- [ ] Old data preserved in database

---

## 8. DEPLOYMENT VERIFICATION

- [ ] Bot responds on Telegram
- [ ] OCR works with Google Cloud Vision
- [ ] Database persists correctly
- [ ] Webhook functioning (if enabled)
- [ ] No crashes or errors in logs
- [ ] All features work in production

---

## ✅ FINAL CHECKLIST

- [ ] All 4 tasks implemented
- [ ] All features tested manually
- [ ] No existing functionality broken
- [ ] Database migrations successful
- [ ] Archived column added successfully
- [ ] All queries exclude archived by default
- [ ] Pagination works both directions
- [ ] Login/Logout cycle works
- [ ] PDFs generate correctly
- [ ] Waiter identification shows everywhere needed

---

## 📝 NOTES & ISSUES

*Add any issues found during testing here:*

- 

---

## 🎯 SUCCESS CRITERIA

All tests must pass for production readiness:
- ✅ Login functionality works
- ✅ Pagination shows correct data
- ✅ Waiter names appear in reconciliation
- ✅ Weekly report downloads and archives
- ✅ No data loss
- ✅ No broken features

---

**Tester:** _____________  
**Date:** _____________  
**Status:** ⏳ In Progress / ✅ Passed / ❌ Failed

