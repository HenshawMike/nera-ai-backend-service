# NERA Chat Service - Render Deployment Guide

## Prerequisites
✅ Service is tested and ready for deployment (see LOCAL_TEST_RESULTS.md)
✅ GitHub repository with the code
✅ Render account (free tier available)
✅ OpenRouter API key

## Deployment Steps

### 1. Push Code to GitHub
Ensure your code is pushed to your GitHub repository:
```bash
cd /home/henshawmikel/Nera-ai/backend/chat_service
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### 2. Create New Web Service on Render

1. **Go to Render Dashboard**
   - Visit: https://dashboard.render.com/
   - Click "New +" → "Web Service"

2. **Connect Your Repository**
   - Select "Connect a repository"
   - Choose your GitHub account
   - Select repository: `HenshawMike/nera` (or your repo name)
   - Click "Connect"

3. **Configure Service (Option A: Using render.yaml)**
   - Render will auto-detect the `render.yaml` file
   - Click "Apply" to use the configuration
   - This will automatically set:
     - Name: `nera-chat-service`
     - Environment: Python
     - Region: Oregon
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. **Configure Service (Option B: Manual Setup)**
   If render.yaml is not detected, configure manually:
   - **Name:** `nera-chat-service`
   - **Region:** Oregon (or closest to your users)
   - **Branch:** `main`
   - **Root Directory:** `backend/chat_service`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. Set Environment Variables

In the Render dashboard, add these environment variables:

1. **OPENROUTER_API_KEY** (Required)
   - Click "Environment" tab
   - Click "Add Environment Variable"
   - Key: `OPENROUTER_API_KEY`
   - Value: Your OpenRouter API key from https://openrouter.ai/keys
   - Click "Save Changes"

2. **OPENROUTER_MODEL** (Optional - already set in render.yaml)
   - Key: `OPENROUTER_MODEL`
   - Value: `deepseek/deepseek-chat-v3.1:free`

3. **PYTHON_VERSION** (Optional - already set in render.yaml)
   - Key: `PYTHON_VERSION`
   - Value: `3.10.0`

### 4. Deploy

1. Click "Create Web Service" or "Manual Deploy"
2. Render will:
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Start the service with uvicorn
3. Wait for deployment to complete (usually 2-5 minutes)

### 5. Verify Deployment

Once deployed, you'll get a URL like: `https://nera-chat-service.onrender.com`

Test the endpoints:

1. **Health Check:**
   ```bash
   curl https://nera-chat-service.onrender.com/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "openrouter": {
       "status": "connected",
       "model": "deepseek/deepseek-chat-v3.1:free"
     }
   }
   ```

2. **API Documentation:**
   Visit: `https://nera-chat-service.onrender.com/docs`

3. **Test Chat:**
   ```bash
   curl -X POST https://nera-chat-service.onrender.com/api/chat \
     -H "Content-Type: application/json" \
     -d '{
       "messages": [
         {
           "role": "user",
           "content": "Hello! Tell me about real estate in Lagos."
         }
       ]
     }'
   ```

## Post-Deployment

### Update Frontend Configuration

Update your frontend `.env` file with the deployed service URL:

```env
VITE_CHAT_SERVICE_URL=https://nera-chat-service.onrender.com
```

### Monitor Service

1. **View Logs:**
   - Go to Render Dashboard → Your Service → "Logs" tab
   - Monitor for any errors or issues

2. **Check Metrics:**
   - Go to "Metrics" tab to see:
     - CPU usage
     - Memory usage
     - Request count
     - Response times

### Important Notes

⚠️ **Free Tier Limitations:**
- Service will spin down after 15 minutes of inactivity
- First request after spin-down may take 30-60 seconds (cold start)
- 750 hours/month of runtime (sufficient for most use cases)

💡 **To Avoid Cold Starts:**
- Upgrade to paid plan ($7/month for Starter)
- Or use a service like UptimeRobot to ping your health endpoint every 10 minutes

### CORS Configuration

The service is already configured to allow requests from:
- `https://nera-ai.netlify.app` (production)
- `http://localhost:5173` (local development)
- `http://localhost:3000` (alternative local)

If you need to add more origins, update the `allow_origins` list in `main.py`.

## Troubleshooting

### Issue: Service fails to start
**Solution:** Check logs for missing dependencies or environment variables

### Issue: Health check fails
**Solution:** Verify `OPENROUTER_API_KEY` is set correctly in environment variables

### Issue: CORS errors
**Solution:** Add your frontend URL to the `allow_origins` list in `main.py`

### Issue: Cold starts are too slow
**Solution:** 
- Upgrade to paid plan
- Use UptimeRobot to keep service warm
- Consider Railway or Fly.io as alternatives

## Alternative Deployment Options

If Render doesn't meet your needs, consider:

1. **Railway** (https://railway.app)
   - Similar to Render
   - $5/month for hobby plan
   - No cold starts

2. **Fly.io** (https://fly.io)
   - More control over infrastructure
   - Free tier available
   - Global edge deployment

3. **Google Cloud Run**
   - Pay per request
   - Auto-scaling
   - Free tier available

## Support

For issues or questions:
- Check the logs in Render Dashboard
- Review LOCAL_TEST_RESULTS.md for local testing
- Contact: Henshaw Michael Ewa

---

**Deployment Date:** 2025-10-17
**Service Version:** 1.0.0
**Status:** ✅ Ready for Production
