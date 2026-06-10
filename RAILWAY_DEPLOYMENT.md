# Railway Deployment Guide

This guide explains how to deploy the Research Intelligence Platform on Railway.

## 🚀 Quick Deploy

### Method 1: Deploy from GitHub

1. **Go to Railway**: https://railway.app/
2. **Click "New Project"**
3. **Select "Deploy from GitHub repo"**
4. **Connect your GitHub account** and select: `rahulprajapat123/research_project`
5. **Railway will auto-detect** the configuration and start deploying

### Method 2: Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy
railway up
```

---

## ⚙️ Configuration Files

Railway uses these files to configure deployment:

### `Procfile`
Tells Railway how to start the application:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### `runtime.txt`
Specifies Python version:
```
3.12
```

### `railway.json`
Railway-specific configuration:
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Railway auto-detects Python apps based on `requirements.txt` and uses the Python version from `runtime.txt`.

---

## 🔐 Environment Variables

After deploying, add these environment variables in Railway dashboard:

### Required Variables:

```bash
# OpenAI (Required)
OPENAI_API_KEY=sk-...

# Database (Neon PostgreSQL - Required)
DATABASE_CONNECTION_STRING=postgresql://user:pass@host/db?sslmode=require

# Email (Required for daily intelligence)
RESEND_API_KEY=re_...
EMAIL_PROVIDER=resend
EMAIL_FROM=onboarding@resend.dev

# App Config
ENVIRONMENT=production
LOG_LEVEL=INFO
ALLOWED_ORIGINS=*
```

### Optional Variables:

```bash
# Research Sources
SEMANTIC_SCHOLAR_API_KEY=your_key
OPENALEX_CONTACT_EMAIL=your@email.com
HUGGINGFACE_TOKEN=hf_...
GNEWS_API_KEY=your_key
NEWSAPI_KEY=your_key
GITHUB_TOKEN=github_pat_...
APIFY_API_TOKEN=apify_api_...

# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...

# Cache (Optional)
UPSTASH_REDIS_URL=your_url
UPSTASH_REDIS_TOKEN=your_token
```

---

## 🎯 How to Add Environment Variables

1. **Go to your Railway project dashboard**
2. **Click on your service**
3. **Click "Variables" tab**
4. **Click "New Variable"**
5. **Add each variable** (name and value)
6. **Click "Deploy"** to restart with new variables

Or use Railway CLI:
```bash
railway variables set OPENAI_API_KEY=sk-...
railway variables set DATABASE_CONNECTION_STRING=postgresql://...
```

---

## 📊 Verify Deployment

After deployment completes:

### 1. Get Your Railway URL
Railway will provide a URL like: `https://your-app.up.railway.app`

### 2. Test Endpoints

**Health Check:**
```bash
curl https://your-app.up.railway.app/api/v1/health
```
Expected: `{"status": "ok", "timestamp": "..."}`

**API Documentation:**
```
https://your-app.up.railway.app/docs
```

**Frontend:**
```
https://your-app.up.railway.app/
```

---

## 🔧 Railway Features

### Automatic Features:
✅ **Auto-scaling** - Scales based on traffic  
✅ **Persistent storage** - Files in logs/ and storage/ persist  
✅ **Background tasks** - Scheduler runs automatically  
✅ **Custom domain** - Add your own domain  
✅ **SSL certificates** - Automatic HTTPS  
✅ **Logs** - View real-time logs in dashboard  
✅ **Metrics** - CPU, memory, network usage  

### Storage:
- Railway provides **persistent volumes**
- Your `logs/` and `storage/` directories will persist across deploys
- No need for /tmp workarounds like Vercel

### Scheduler:
- Background scheduler runs automatically
- Fetches sources on schedule
- No need for external cron jobs

---

## 📈 Monitoring

### View Logs:
```bash
# Via CLI
railway logs

# Via Dashboard
Go to project → Deployments → Click deployment → View logs
```

### View Metrics:
- Dashboard shows CPU, Memory, Network usage
- Set up alerts for high resource usage

---

## 🐛 Troubleshooting

### Build Fails:

**Check Python version:**
```toml
# In nixpacks.toml
nixPkgs = ["python312"]  # Must be python312
```

**Check dependencies:**
```bash
# View build logs in Railway dashboard
# Look for failed pip installs
```

### Runtime Errors:

**Database connection:**
- Verify `DATABASE_CONNECTION_STRING` is set correctly
- Check Neon database is accessible
- Test connection locally first

**Missing API keys:**
- Check environment variables are set
- OPENAI_API_KEY is required
- Other keys are optional but recommended

### Port Issues:

**App not responding:**
- Railway sets `$PORT` environment variable
- App must listen on `0.0.0.0:$PORT`
- Already configured in Procfile and config.py

---

## 💰 Railway Pricing

### Hobby Plan (Free):
- $5 free credit/month
- Enough for testing
- Auto-sleeps after inactivity

### Pro Plan ($20/month):
- $20 credit included
- No sleep
- Priority support
- Custom domains

### Usage Pricing:
- ~$0.000231/GB RAM/min
- ~$0.000463/vCPU/min
- ~$0.10/GB bandwidth

**Estimated cost for this app:**
- ~$10-20/month for moderate usage
- Depends on traffic and resource usage

---

## 🔄 Updates & Redeployment

### Automatic:
Railway auto-deploys when you push to GitHub:
```bash
git add .
git commit -m "Update feature"
git push
```

### Manual:
```bash
# Via CLI
railway up

# Via Dashboard
Click "Deploy" button
```

---

## 🌐 Custom Domain

### Add Your Domain:

1. **Go to project settings**
2. **Click "Domains"**
3. **Click "Custom Domain"**
4. **Enter your domain**: `api.yourdomain.com`
5. **Add DNS records** as shown by Railway:
   ```
   CNAME api.yourdomain.com → your-app.up.railway.app
   ```
6. **Wait for DNS propagation** (5-30 minutes)

---

## 📦 Database Setup

### Using Neon (Recommended):

Your app is already configured with Neon PostgreSQL:
```bash
DATABASE_CONNECTION_STRING=postgresql://neondb_owner:npg_...@ep-still-violet-aooo7qxw.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

### Using Railway PostgreSQL:

1. **Add PostgreSQL service** in Railway
2. **Railway will set** `DATABASE_URL` automatically
3. **Copy value to** `DATABASE_CONNECTION_STRING`

---

## 🎉 Success Checklist

After deployment, verify:

- ✅ Build completed successfully
- ✅ Service is running (not crashed)
- ✅ `/api/v1/health` returns 200 OK
- ✅ `/docs` shows API documentation
- ✅ Frontend loads at `/`
- ✅ Can upload brief and get recommendations
- ✅ Logs show no critical errors

---

## 📞 Support

**Railway Documentation:** https://docs.railway.app/  
**Railway Discord:** https://discord.gg/railway  
**Railway Status:** https://status.railway.app/  

---

## 🔒 Security Notes

### Environment Variables:
- Never commit `.env` file to Git
- Use Railway's encrypted variable storage
- Rotate API keys regularly

### Database:
- Use SSL connections (already configured)
- Don't expose database publicly
- Regular backups recommended

### API Keys:
- Keep OPENAI_API_KEY secure
- Monitor usage to prevent abuse
- Set up rate limiting if needed

---

## 🚀 Next Steps

After successful deployment:

1. **Test all endpoints** thoroughly
2. **Set up monitoring** and alerts
3. **Configure custom domain** (optional)
4. **Enable auto-deployments** from GitHub
5. **Set up database backups**
6. **Monitor costs** in Railway dashboard

---

**Your app is now ready for Railway deployment!** 🎉
