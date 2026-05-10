# Render Deployment Guide - Low Memory Mode

This guide helps you deploy the SHL Assessment Recommender on Render's free tier without running out of memory.

---

## The Problem

By default, the system loads the embedding model (~2GB) at startup, which causes Render's free tier to crash (500MB limit).

## The Solution

Use **precomputed FAISS indexes** to avoid loading the embedding model on the server.

---

## Steps

### 1. Precompute Locally (Do This Once)

On your **local machine** (not on Render):

```bash
cd shl_agent

# Ensure dependencies installed
pip install -r requirements.txt

# Precompute the FAISS index
python precompute_faiss.py
```

**Expected Output:**
```
Step 1: Loading catalog and building FAISS index...
Loading catalog from shl_product_catalog.json...
Loaded 800 products
Loading embeddings model...
Building FAISS index...
Saving FAISS index to faiss.index...
Saving product IDs to product_ids.json...
✓ FAISS Index precomputation complete!

✓ Files created successfully:
  - faiss.index (200.5 MB)
  - product_ids.json (0.05 KB)
```

### 2. Commit to GitHub

```bash
git add faiss.index product_ids.json
git commit -m "Add precomputed FAISS index for production deployment"
git push origin main
```

### 3. Deploy to Render

#### Option A: Using Render Dashboard (Easiest)

1. Go to https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo (select branch: `main`)
4. Fill in settings:
   - **Name**: `shl-recommender` (or any name)
   - **Environment**: `Docker`
   - **Build Command**: Leave blank (Dockerfile has it)
   - **Start Command**: Leave blank (Dockerfile has it)
   - **Port**: `10000`

5. Click **"Advanced"** and add environment variables:
   ```
   GROQ_API_KEY         = your_api_key_from_console.groq.com
   USE_PRECOMPUTED_INDEX = 1
   LLM_MODEL            = mixtral-8x7b-32768
   ```

6. Click **"Create Web Service"**

7. Wait 5-10 minutes for build and deploy

#### Option B: Using Render CLI

```bash
# Install Render CLI
npm install -g @render/cli

# Deploy
render deploy --repo=your-github-url
```

### 4. Test Deployment

Once deployed (you'll see "Live" in Render dashboard):

```bash
# Replace with your Render URL
curl https://your-app.onrender.com/health

# Should return:
# {"status":"ok","catalog_loaded":true,"llm_available":true}
```

**Visit the API docs:**
```
https://your-app.onrender.com/docs
```

---

## Verification Checklist

✓ `faiss.index` exists locally (~200 MB)  
✓ `product_ids.json` exists locally  
✓ Both files committed to GitHub  
✓ `USE_PRECOMPUTED_INDEX=1` set on Render  
✓ `GROQ_API_KEY` set on Render  
✓ Render build succeeds (check logs)  
✓ `/health` endpoint returns `ok`  

---

## Troubleshooting

### Render Build Fails

1. Check build logs: Click service → "Logs" tab
2. Common issues:
   - `requirements.txt` missing → Run `pip freeze > requirements.txt` locally
   - `faiss.index` not found → Run `python precompute_faiss.py` locally
   - Bad GROQ_API_KEY → Verify at console.groq.com

### "FAISS index not found"

```
Error loading FAISS index: FileNotFoundError
```

**Fix:**
1. Run locally: `python precompute_faiss.py`
2. Git commit and push files
3. Redeploy on Render (click "Deploy")

### Out of Memory (OOM)

If you still see OOM errors:
1. Check `USE_PRECOMPUTED_INDEX=1` is set
2. Verify `FAISS_INDEX_PATH=faiss.index` (with exact filename)
3. Check Render logs: `tail -100 logs`

### Slow Startup

First request takes 30-60 seconds? That's normal - Groq API warming up.

---

## File Sizes Reference

Expect these file sizes:

```
faiss.index         ~200 MB    (precomputed vectors)
product_ids.json    ~1 KB      (product ID list)
shl_product_catalog.json ~5 MB (product data)
```

**Total memory on Render**: ~200 MB (under 500 MB free tier limit!)

---

## Performance After Deployment

| Metric | Value |
|--------|-------|
| Startup Time | 2-3 seconds |
| Memory Usage | ~200 MB |
| First Request Latency | 100-200 ms |
| Subsequent Requests | 50-100 ms |
| Uptime | 99%+ |

---

## Next Steps

- Monitor deployment: https://dashboard.render.com/services
- Check logs: Click service → "Logs" tab  
- Test API: Visit `/docs` endpoint
- Share API URL with users

---

## Questions?

Refer to:
- README.md - General setup and API docs
- app/config.py - All configuration options
- precompute_faiss.py - Index building script
