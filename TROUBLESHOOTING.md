# Troubleshooting Guide

## Issue 1: Email Sending Fails with 403 Error

### Problem
```
Resend failed with 403: "You can only send testing emails to your own email address"
```

### Root Cause
Resend API is in **sandbox/test mode** and requires domain verification to send to other recipients.

### Solutions

#### Option A: Use Verified Email Only (Quick Fix)
In the Daily Intelligence settings, use only your verified email:
```
rahulprajapat.tech123@gmail.com
```

#### Option B: Verify Your Domain (Recommended)
1. Go to [Resend Dashboard](https://resend.com/domains)
2. Add your domain (e.g., `bridgeaitech.com`)
3. Add DNS records to verify ownership
4. Update email settings to use `@bridgeaitech.com` addresses

#### Option C: Use Different Email Provider
Configure SMTP in your `.env`:
```bash
# Use Gmail, Outlook, or other SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## Issue 2: Brief Analysis Returns "No Recommendations"

### Problem
- Papers are not being fetched from arXiv
- Error logs show: `429 Unknown Error` (rate limiting)
- Found 0 papers in searches

### Root Causes
1. **arXiv rate limiting**: Too many requests in short time
2. **Missing delay between requests**: arXiv requires 3-second delays
3. **Timeout issues**: 90-second timeout may be too short
4. **Empty search results**: Some keywords don't match papers

### Solutions

#### Fix 1: Check Your .env Configuration
Create a `.env` file (copy from `.env.example`):
```bash
# Required
OPENAI_API_KEY=sk-...

# Recommended for better rate limits
SEMANTIC_SCHOLAR_API_KEY=your_key
OPENALEX_CONTACT_EMAIL=your-email@example.com
HUGGINGFACE_TOKEN=your_token

# Optional but helpful
GNEWS_API_KEY=your_key
NEWSAPI_KEY=your_key
GITHUB_TOKEN=your_github_pat
```

#### Fix 2: Wait Between Brief Analyses
arXiv blocks rapid requests. **Wait 5+ minutes between analyses** to avoid 429 errors.

#### Fix 3: Use Better Keywords
The system extracts keywords from your brief. Make sure your brief mentions:
- Specific technologies (FastAPI, React, PostgreSQL, etc.)
- Technical terms (RAG, vector embeddings, semantic search, etc.)
- Clear technical requirements

#### Fix 4: Try Manual Source Fetch
1. Go to **Sources** tab
2. Click **"Fetch Latest Sources"**
3. Wait for completion
4. Then analyze your brief

---

## Issue 3: arXiv 429 Rate Limit Errors

### Problem
```
ERROR: arXiv search failed: Client error '429 Unknown Error'
```

### Understanding arXiv Rate Limits
- **Limit**: 1 request per 3 seconds per IP
- **Daily limit**: ~300-500 requests per day
- **Triggers**: Multiple rapid analyses, copilot searches

### Solutions

1. **Reduce Request Frequency**
   - Wait 5+ minutes between brief analyses
   - Avoid running multiple analyses simultaneously
   - Use cached results when possible

2. **Use Alternative Sources**
   arXiv is just one source. The system also uses:
   - ✅ OpenAlex (no key, good rate limits)
   - ✅ Semantic Scholar (with API key)
   - ✅ RSS feeds (news sources)
   - ✅ Hacker News
   - ✅ GitHub repositories

3. **Optimize Search Terms**
   - Fewer, more specific keywords = fewer API calls
   - The system limits to 5 keywords automatically

4. **Wait for Rate Limit Reset**
   - arXiv resets every 3-5 minutes
   - Check logs for "Fetched X papers from arXiv"

---

## Issue 4: No Papers Found / Empty Results

### Checklist

✅ **Verify Search Terms Are Generated**
Check logs for: `🎯 Keywords: ...`

✅ **Check Source Fetch Status**
Look for logs like:
```
INFO: Fetched 162 unique papers from arXiv
INFO: Fetched 60 papers from OpenAlex
```

✅ **Verify Technology Matching**
Papers must mention technologies from `TECHNOLOGY_CATALOG` in `scoring.py`

✅ **Check Timeout**
If seeing timeout errors, increase in `brief_service.py`:
```python
timeout=120  # Increase from 90s
```

---

## Issue 5: Database Unavailable Warnings

### Problem
```
DEBUG: Postgres intelligence store unavailable, using local fallback
```

### This is EXPECTED!
The system works **completely without PostgreSQL** using local JSON storage.

If you want to use PostgreSQL:
1. Install PostgreSQL
2. Create database
3. Configure in `.env`:
```bash
DATABASE_CONNECTION_STRING=postgresql://user:pass@localhost:5432/dbname
```
4. Run migrations (if needed)

---

## Quick Diagnostic Checklist

### For Email Issues:
- [ ] Is `RESEND_API_KEY` set in `.env`?
- [ ] Is recipient email verified in Resend?
- [ ] Is domain verified (for non-owner emails)?

### For Brief Analysis Issues:
- [ ] Is `OPENAI_API_KEY` set in `.env`?
- [ ] Did you wait 5+ minutes since last arXiv request?
- [ ] Does brief contain technical keywords?
- [ ] Check server logs for "Fetched X papers"

### For Source Fetch Issues:
- [ ] Check `storage/fetched_sources.json` exists
- [ ] Verify network connectivity
- [ ] Check rate limit status in logs
- [ ] Try manual fetch from Sources tab

---

## Getting Better Results

### Write Better Project Briefs
Include:
- **Specific technologies**: "FastAPI, PostgreSQL, React"
- **Technical requirements**: "Real-time search", "Vector embeddings"
- **Clear goals**: "Build a RAG system for medical queries"
- **Constraints**: "Sub-second latency", "HIPAA compliant"

### Example Good Brief:
```
Project: AI-Powered Customer Support

We need to build a RAG-based customer support system using:
- LangChain for orchestration
- pgvector for semantic search
- FastAPI backend
- React frontend

Technical Requirements:
- Handle 1000+ concurrent users
- Sub-200ms query response time
- Citation-backed answers from knowledge base
```

### Example Poor Brief:
```
Build an AI thing for customers
```

---

## Need More Help?

Check logs in terminal for detailed error messages:
- API errors (rate limits, auth failures)
- Source fetch status
- Recommendation generation details

Common log patterns to search for:
- `ERROR` - Critical failures
- `WARNING` - Non-critical issues
- `Fetched X papers` - Source fetch success
- `Found 0 papers` - No results (check keywords)
- `429` - Rate limiting
- `403` - Authentication/permission issues
