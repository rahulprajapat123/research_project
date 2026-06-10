# Vercel Deployment Guide - Research Intelligence System

## 🚀 **Can I Deploy Both Backend and Frontend on Vercel?**

### **YES! With Vercel Premium** ✅

With your **Vercel Premium subscription**, you can deploy BOTH:
- ✅ **FastAPI Backend** (Python serverless functions)
- ✅ **Frontend** (Static HTML/CSS/JS)

**All in ONE Vercel project!**

---

## 📊 **Deployment Architecture**

### **Option 1: Unified Vercel Deployment** (Recommended with Premium)

```
Vercel Project
├── Backend (FastAPI)
│   ├── Python serverless functions
│   ├── API routes: /api/*
│   └── Max duration: 60s (Premium: 900s)
│
└── Frontend
    ├── Static files
    ├── Routes: /frontend/*
    └── Served from Vercel CDN
```

**Benefits:**
- ✅ Single deployment
- ✅ No CORS issues
- ✅ Shared environment variables
- ✅ One domain for everything
- ✅ Premium features: longer timeouts, more memory

---

## 🎯 **Step-by-Step Deployment**

### **Step 1: Prepare Your GitHub Repository** ✅

Already done! Your code is at:
```
https://github.com/rahulprajapat123/research_project
```

---

### **Step 2: Import Project to Vercel**

1. **Go to Vercel Dashboard:**
   ```
   https://vercel.com/new
   ```

2. **Import Git Repository:**
   - Click "Import Project"
   - Select "Import Git Repository"
   - Choose: `rahulprajapat123/research_project`
   - Click "Import"

3. **Configure Project:**
   - **Framework Preset:** Other
   - **Root Directory:** `./` (leave as default)
   - **Build Command:** (leave empty, not needed for Python)
   - **Output Directory:** (leave empty)
   - **Install Command:** (leave empty)

4. **Click "Deploy"**

---

### **Step 3: Add Environment Variables**

After importing, go to:
```
Project Settings → Environment Variables
```

Add these **REQUIRED** variables:

#### **Essential Variables:**
```
OPENAI_API_KEY=sk-proj-YOUR_OPENAI_API_KEY_HERE

DATABASE_CONNECTION_STRING=postgresql://user:password@host/database?sslmode=require

RESEND_API_KEY=re_YOUR_RESEND_API_KEY_HERE

EMAIL_PROVIDER=resend
EMAIL_FROM=onboarding@resend.dev
```

#### **Optional but Recommended:**
```
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_key_here
OPENALEX_CONTACT_EMAIL=your-email@example.com
HUGGINGFACE_TOKEN=hf_YOUR_HUGGINGFACE_TOKEN_HERE
GNEWS_API_KEY=your_gnews_api_key_here
NEWSAPI_KEY=your_newsapi_key_here
GITHUB_TOKEN=ghp_YOUR_GITHUB_TOKEN_HERE
APIFY_API_TOKEN=apify_api_YOUR_APIFY_TOKEN_HERE
```

**Important:** Make sure to select **"Production, Preview, and Development"** for each variable.

---

### **Step 4: Configure vercel.json** ✅

Already created! Your `vercel.json` configures:

- ✅ Python runtime for FastAPI
- ✅ Static file serving for frontend
- ✅ Proper routing (API + frontend)
- ✅ Function memory: 1024MB
- ✅ Function timeout: 60s (increase with Premium)

---

### **Step 5: Deploy!**

Click **"Deploy"** and wait 2-3 minutes.

Vercel will:
1. ✅ Install Python dependencies from `requirements.txt`
2. ✅ Set up serverless functions for FastAPI
3. ✅ Deploy static frontend files
4. ✅ Configure routing
5. ✅ Assign production URL

---

### **Step 6: Test Your Deployment**

Once deployed, you'll get a URL like:
```
https://research-project-xxxx.vercel.app
```

**Test these endpoints:**

1. **Backend API:**
   ```
   https://your-app.vercel.app/api/v1/health
   https://your-app.vercel.app/docs
   ```

2. **Frontend:**
   ```
   https://your-app.vercel.app/frontend/copilot.html
   ```

---

## ⚙️ **Vercel Premium Features for Your Project**

With **Vercel Premium**, you get:

### **1. Increased Function Limits**
```
Free:    60s timeout, 1024MB RAM
Premium: 900s timeout, 3008MB RAM  ← Much better for AI workloads!
```

**Update `vercel.json` for Premium:**
```json
{
  "functions": {
    "main.py": {
      "memory": 3008,
      "maxDuration": 900
    }
  }
}
```

### **2. More Build Minutes**
```
Free:    6,000 build minutes/month
Premium: Unlimited build minutes
```

### **3. Edge Network**
```
Premium: Global edge caching
         Faster API responses worldwide
```

### **4. Team Collaboration**
```
Premium: Multiple team members
         Access controls
         Audit logs
```

---

## 🔧 **Optimizing for Vercel**

### **1. Update main.py for Serverless**

Your FastAPI app is already compatible! But ensure:

```python
# main.py
from fastapi import FastAPI

app = FastAPI()

# All your routes...

# For Vercel serverless
handler = app  # This is what Vercel calls
```

### **2. Update vercel.json for Premium**

```json
{
  "version": 2,
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "50mb"
      }
    },
    {
      "src": "frontend/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/frontend/(.*)",
      "dest": "/frontend/$1"
    },
    {
      "src": "/(.*)",
      "dest": "main.py"
    }
  ],
  "functions": {
    "main.py": {
      "memory": 3008,
      "maxDuration": 900
    }
  }
}
```

### **3. Handle Cold Starts**

FastAPI on Vercel has ~1-3s cold start. To minimize:

```python
# Add to main.py
@app.on_event("startup")
async def startup():
    # Warm up connections
    logger.info("FastAPI starting up on Vercel")
    
@app.get("/")
async def root():
    return {"status": "ok", "message": "Research Intelligence API"}
```

---

## 🌐 **Custom Domain (Optional)**

1. **Go to:** Project Settings → Domains
2. **Add domain:** research-intelligence.yourdomain.com
3. **Update DNS:**
   ```
   Type: CNAME
   Name: research-intelligence
   Value: cname.vercel-dns.com
   ```
4. **SSL:** Auto-provisioned by Vercel

---

## 📊 **Monitoring Your Deployment**

### **Vercel Analytics Dashboard**

View in real-time:
- ✅ Function invocations
- ✅ Response times
- ✅ Error rates
- ✅ Bandwidth usage
- ✅ Build logs

### **Function Logs**

```python
# Add logging to your functions
from loguru import logger

logger.info(f"Request received: {request.url}")
```

View logs in: **Vercel Dashboard → Project → Functions**

---

## ⚠️ **Important Considerations for Vercel**

### **1. Stateless Functions**

Vercel functions are **stateless**. Your app handles this well with:
- ✅ Neon PostgreSQL (external state)
- ✅ Redis (optional caching)
- ✅ No local file writes (except temporary)

### **2. File System (Read-Only)**

You can't write to `/storage/` on Vercel. Solutions:

**Option A:** Use database only (recommended)
```python
# Already implemented in your code
# Falls back to database when storage fails
```

**Option B:** Use Vercel Blob Storage
```bash
npm install @vercel/blob
```

### **3. Background Tasks**

Vercel functions timeout after execution. For background tasks:

**Option A:** Use Vercel Cron Jobs
```json
// vercel.json
{
  "crons": [
    {
      "path": "/api/v1/sources/fetch-latest",
      "schedule": "0 2 * * *"
    }
  ]
}
```

**Option B:** Use external scheduler (Upstash, AWS EventBridge)

---

## 🚀 **Deployment Checklist**

Before deploying, verify:

- [ ] Code pushed to GitHub
- [ ] `vercel.json` configured
- [ ] `.gitignore` excludes `.env`
- [ ] `requirements.txt` updated
- [ ] Database (Neon) accessible from internet
- [ ] API keys ready for Vercel
- [ ] Test locally: `python main.py`

---

## 🔄 **Continuous Deployment**

Once deployed, Vercel auto-deploys on:

```
git push → GitHub → Vercel automatically deploys
```

**Branches:**
- `main` → Production deployment
- Other branches → Preview deployments

---

## 📈 **Scaling on Vercel Premium**

Your app can handle:

```
Concurrent requests: 1000+ (Premium)
Function memory: 3008MB
Function timeout: 15 minutes
Monthly bandwidth: Unlimited
Edge locations: 100+ globally
```

---

## 🆘 **Troubleshooting**

### **Build Fails**

1. Check build logs in Vercel dashboard
2. Verify `requirements.txt` is complete
3. Ensure Python 3.12 compatible

### **Function Timeout**

1. Increase timeout in `vercel.json`
2. Optimize slow queries
3. Use async functions

### **Environment Variables Not Working**

1. Verify variables in Vercel dashboard
2. Check variable names match exactly
3. Redeploy after adding variables

### **Database Connection Issues**

1. Verify Neon database is accessible
2. Check connection string format
3. Ensure Neon allows connections from Vercel IPs

---

## 🎯 **Final Deployment URLs**

After deployment:

```
Backend API:
https://your-app.vercel.app/api/v1/health
https://your-app.vercel.app/docs

Frontend:
https://your-app.vercel.app/frontend/copilot.html

Direct API Access:
https://your-app.vercel.app/api/v1/copilot/upload-brief
```

---

## 💡 **Best Practices**

1. **Use Premium features:**
   - Set timeout to 900s
   - Use 3008MB memory
   - Enable edge caching

2. **Monitor performance:**
   - Check function logs regularly
   - Set up alerts for errors
   - Monitor API response times

3. **Optimize costs:**
   - Cache frequently accessed data
   - Use database connection pooling
   - Minimize external API calls

4. **Security:**
   - Never commit `.env` to git
   - Use Vercel environment variables
   - Enable rate limiting

---

## 🎉 **You're Ready!**

Your project is:
- ✅ Pushed to GitHub
- ✅ Configured for Vercel
- ✅ Ready for one-click deployment
- ✅ Optimized for Vercel Premium

**Next step:** Import project in Vercel and deploy!

**Estimated deployment time:** 2-3 minutes

---

**Questions?** Check Vercel docs: https://vercel.com/docs/functions/serverless-functions/runtimes/python
