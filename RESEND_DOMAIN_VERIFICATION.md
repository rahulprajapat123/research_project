# Domain Verification Guide for Resend
## Send emails to @bridgeaitech.com addresses

---

## 📋 **Prerequisites**

Before starting, make sure you have:
- ✅ Access to Resend account (https://resend.com)
- ✅ Access to DNS settings for `bridgeaitech.com` domain
  - This could be through: GoDaddy, Namecheap, Cloudflare, Google Domains, etc.
- ✅ Account credentials for your DNS provider

---

## 🚀 **Step-by-Step Domain Verification**

### **Step 1: Login to Resend Dashboard**

1. Go to: **https://resend.com/login**
2. Login with your credentials
3. You should see the main dashboard

---

### **Step 2: Navigate to Domains Section**

1. Click on **"Domains"** in the left sidebar
   - Or go directly to: https://resend.com/domains
2. You'll see a list of your domains (currently only `onboarding@resend.dev` if this is new)

---

### **Step 3: Add Your Domain**

1. Click the **"Add Domain"** button (top right)
2. Enter your domain: **`bridgeaitech.com`**
   - ⚠️ Enter ONLY the domain, not email address
   - ✅ Correct: `bridgeaitech.com`
   - ❌ Wrong: `rahul.prajapat@bridgeaitech.com`
3. Click **"Add"**

---

### **Step 4: Get DNS Records**

After adding the domain, Resend will show you **DNS records to add**. You'll typically see:

#### **A. SPF Record (Type: TXT)**
```
Name: @
Type: TXT
Value: v=spf1 include:_spf.resend.com ~all
```

#### **B. DKIM Record (Type: TXT)**
```
Name: resend._domainkey
Type: TXT
Value: [Long string starting with "v=DKIM1; k=rsa; p=..."]
```
*Note: The actual value will be provided by Resend - copy it exactly*

#### **C. DMARC Record (Type: TXT)** - Optional but recommended
```
Name: _dmarc
Type: TXT
Value: v=DMARC1; p=none; rua=mailto:dmarc@bridgeaitech.com
```

**📸 Screenshot what Resend shows you - you'll need these exact values**

---

### **Step 5: Add DNS Records to Your Domain**

Now you need to add these records to your DNS provider. Instructions for common providers:

---

#### **5A. If using Cloudflare:**

1. Login to Cloudflare: https://dash.cloudflare.com
2. Select your domain: **bridgeaitech.com**
3. Click **"DNS"** in the top menu
4. Click **"Add record"** button

**For SPF Record:**
- Type: `TXT`
- Name: `@`
- Content: `v=spf1 include:_spf.resend.com ~all`
- TTL: `Auto`
- Click **"Save"**

**For DKIM Record:**
- Type: `TXT`
- Name: `resend._domainkey`
- Content: `[paste the long value from Resend]`
- TTL: `Auto`
- Click **"Save"**

**For DMARC Record (Optional):**
- Type: `TXT`
- Name: `_dmarc`
- Content: `v=DMARC1; p=none; rua=mailto:dmarc@bridgeaitech.com`
- TTL: `Auto`
- Click **"Save"**

---

#### **5B. If using GoDaddy:**

1. Login to GoDaddy: https://account.godaddy.com
2. Go to **"My Products"** → **"DNS"**
3. Find **bridgeaitech.com** and click **"DNS"**
4. Scroll to **"Records"** section
5. Click **"Add"** button

**For SPF Record:**
- Type: `TXT`
- Name: `@`
- Value: `v=spf1 include:_spf.resend.com ~all`
- TTL: `1 hour`
- Click **"Save"**

**For DKIM Record:**
- Type: `TXT`
- Name: `resend._domainkey`
- Value: `[paste from Resend]`
- TTL: `1 hour`
- Click **"Save"**

**For DMARC Record:**
- Type: `TXT`
- Name: `_dmarc`
- Value: `v=DMARC1; p=none; rua=mailto:dmarc@bridgeaitech.com`
- TTL: `1 hour`
- Click **"Save"**

---

#### **5C. If using Namecheap:**

1. Login to Namecheap: https://www.namecheap.com
2. Go to **"Domain List"** → Select **bridgeaitech.com**
3. Click **"Manage"** → **"Advanced DNS"** tab
4. Scroll to **"Host Records"**
5. Click **"Add New Record"**

**For SPF Record:**
- Type: `TXT Record`
- Host: `@`
- Value: `v=spf1 include:_spf.resend.com ~all`
- TTL: `Automatic`
- Click **green checkmark** to save

**For DKIM Record:**
- Type: `TXT Record`
- Host: `resend._domainkey`
- Value: `[paste from Resend]`
- TTL: `Automatic`
- Click **green checkmark**

**For DMARC Record:**
- Type: `TXT Record`
- Host: `_dmarc`
- Value: `v=DMARC1; p=none; rua=mailto:dmarc@bridgeaitech.com`
- TTL: `Automatic`
- Click **green checkmark**

---

#### **5D. If using Google Domains:**

1. Login to Google Domains: https://domains.google.com
2. Click on **bridgeaitech.com**
3. Click **"DNS"** in the left menu
4. Scroll to **"Custom records"**
5. Click **"Manage custom records"**

**For SPF Record:**
- Host name: Leave blank (for @)
- Type: `TXT`
- TTL: `3600`
- Data: `v=spf1 include:_spf.resend.com ~all`
- Click **"Add"**

**For DKIM Record:**
- Host name: `resend._domainkey`
- Type: `TXT`
- TTL: `3600`
- Data: `[paste from Resend]`
- Click **"Add"**

**For DMARC Record:**
- Host name: `_dmarc`
- Type: `TXT`
- TTL: `3600`
- Data: `v=DMARC1; p=none; rua=mailto:dmarc@bridgeaitech.com`
- Click **"Add"**

---

### **Step 6: Wait for DNS Propagation**

⏰ **DNS changes can take time to propagate:**
- Minimum: 5-10 minutes
- Typical: 30 minutes to 1 hour
- Maximum: 24-48 hours (rare)

**💡 Tip:** Cloudflare is usually fastest (5-10 minutes)

---

### **Step 7: Verify Domain in Resend**

1. Go back to Resend Dashboard: https://resend.com/domains
2. Find **bridgeaitech.com** in your domains list
3. Click **"Verify"** button
   - If DNS records are found, you'll see ✅ **"Verified"** status
   - If not ready yet, wait 10-15 more minutes and try again

**Status meanings:**
- 🟡 **Pending** - DNS records not found yet (wait longer)
- ✅ **Verified** - Domain ready! You can send emails
- ❌ **Failed** - DNS records incorrect (double-check values)

---

### **Step 8: Test Domain Verification**

You can check if DNS records are propagated using online tools:

**Check DNS Records:**
1. Go to: https://mxtoolbox.com/SuperTool.aspx
2. Enter: `bridgeaitech.com`
3. Select: `TXT Lookup`
4. Click **"TXT Lookup"**
5. You should see your SPF record

**Check DKIM Record:**
1. Go to: https://mxtoolbox.com/SuperTool.aspx
2. Enter: `resend._domainkey.bridgeaitech.com`
3. Select: `TXT Lookup`
4. You should see the DKIM record

---

### **Step 9: Update Email Configuration**

Once verified in Resend:

#### **Option A: Via Frontend (Recommended)**

1. Open: http://localhost:8000 (or http://0.0.0.0:8000)
2. Go to **"Daily Intelligence"** tab
3. Click **"Configure Email Settings"**
4. Change **Team Email** from:
   - ❌ `rahulprajapat.tech123@gmail.com`
   - ✅ `rahul.prajapat@bridgeaitech.com`
5. Click **"Save Settings"**

#### **Option B: Via Database Update Script**

Run this script:

```powershell
cd C:\Users\praja\Desktop\research-agent-main\research-agent-main
python update_team_email.py
```

Create the script if needed - I can generate it for you.

---

### **Step 10: Test Email Sending**

Test that emails work to the new address:

```powershell
# Test email delivery
python test_email_sending.py
```

You should see:
```
✅ Status: sent
✅ Recipient: rahul.prajapat@bridgeaitech.com
✅ Provider: resend
```

**Check inbox at `rahul.prajapat@bridgeaitech.com`** for the test email!

---

## 🔍 **Troubleshooting**

### **Problem: DNS Records Not Found After 1 Hour**

**Solution:**
1. Check the record names are EXACT:
   - SPF: Must be `@` or empty (not `bridgeaitech.com`)
   - DKIM: Must be `resend._domainkey` (not `resend._domainkey.bridgeaitech.com`)
2. Remove any duplicate TXT records for the same name
3. Make sure values are enclosed in quotes if DNS provider requires it
4. Try removing and re-adding the records

---

### **Problem: Verification Failed**

**Common Causes:**
1. **Wrong record name** - Double-check spelling
2. **Extra spaces** in the value - Copy-paste carefully
3. **Missing the @ symbol** - SPF must be on root domain
4. **DNS not propagated yet** - Wait longer (up to 24 hours)

**Fix:**
- Use https://dnschecker.org to see if records are propagated globally
- Enter `bridgeaitech.com` and select `TXT` type
- Check if your records appear in multiple locations

---

### **Problem: Emails Still Failing After Verification**

**Check:**
1. Resend domain shows ✅ **Verified** status
2. Email address matches domain: `@bridgeaitech.com`
3. Server restarted after domain verification
4. `.env` file still has correct `RESEND_API_KEY`

---

## 📊 **DNS Record Verification Checklist**

Before clicking "Verify" in Resend, confirm:

- [ ] SPF record added (Name: `@`, Value: `v=spf1 include:_spf.resend.com ~all`)
- [ ] DKIM record added (Name: `resend._domainkey`, Value: provided by Resend)
- [ ] DMARC record added (Name: `_dmarc`, Value: `v=DMARC1; p=none...`)
- [ ] Waited at least 15-30 minutes for propagation
- [ ] Checked records with https://mxtoolbox.com
- [ ] No duplicate TXT records for same name
- [ ] Values copied exactly from Resend (no extra spaces)

---

## 🎯 **After Verification Success**

Once domain is verified:

✅ **You can send to ANY email at `@bridgeaitech.com`:**
- `rahul.prajapat@bridgeaitech.com`
- `team@bridgeaitech.com`
- `support@bridgeaitech.com`
- Any address you want!

✅ **No sandbox restrictions:**
- Send to unlimited recipients
- No verification needed for individual addresses
- Professional sender domain

✅ **Better email deliverability:**
- Emails less likely to go to spam
- Professional appearance (from `@bridgeaitech.com` instead of `@resend.dev`)

---

## 📧 **Alternative: Quick Fix (No Domain Verification)**

If domain verification is too complex, you have simpler options:

### **Option 1: Keep Current Setup**
- Continue using `rahulprajapat.tech123@gmail.com`
- Already working, no changes needed
- Just accept that you can only send to this one address

### **Option 2: Switch to Gmail SMTP**
- No domain verification needed
- Send to ANY email address
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for Gmail SMTP setup

---

## 🆘 **Need Help?**

**I'm ready to assist with:**
1. Creating the database update script
2. Checking your DNS records
3. Troubleshooting verification issues
4. Setting up Gmail SMTP as alternative
5. Testing email delivery after verification

**Just let me know which DNS provider you use (Cloudflare, GoDaddy, Namecheap, etc.) and I can provide more specific instructions!**

---

## 📝 **Quick Reference - DNS Records Template**

Copy these to your DNS provider (replace placeholders):

```
Record 1:
Type: TXT
Name: @
Value: v=spf1 include:_spf.resend.com ~all
TTL: 3600

Record 2:
Type: TXT
Name: resend._domainkey
Value: [COPY FROM RESEND - starts with "v=DKIM1; k=rsa; p="]
TTL: 3600

Record 3:
Type: TXT
Name: _dmarc
Value: v=DMARC1; p=none; rua=mailto:dmarc@bridgeaitech.com
TTL: 3600
```

---

**Total Time:** 5-10 minutes (setup) + 15-60 minutes (DNS propagation)
**Difficulty:** ⭐⭐⭐ Moderate (requires DNS access)
**Result:** Send emails to any `@bridgeaitech.com` address! 🎉
