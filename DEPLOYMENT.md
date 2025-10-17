# Chat Service Deployment Guide

This guide covers multiple deployment options for the NERA Chat Service.

## Prerequisites

- Your `DEEPSEEK_API_KEY` environment variable
- Git repository with the code pushed

## Deployment Options

### Option 1: Render (Recommended - Free Tier Available)

1. **Sign up/Login to Render**: https://render.com

2. **Create a New Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `backend/chat_service` directory

3. **Configure the service**:
   - **Name**: `nera-chat-service`
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: `backend/chat_service`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. **Add Environment Variables**:
   - Click "Environment" tab
   - Add: `DEEPSEEK_API_KEY` = `your-api-key`

5. **Deploy**: Click "Create Web Service"

6. **Get your URL**: After deployment, you'll get a URL like `https://nera-chat-service.onrender.com`

---

### Option 2: Railway (Easy & Fast)

1. **Sign up/Login to Railway**: https://railway.app

2. **Deploy from GitHub**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will auto-detect the Dockerfile

3. **Configure Environment Variables**:
   - Go to "Variables" tab
   - Add: `DEEPSEEK_API_KEY` = `your-api-key`
   - Add: `PORT` = `8001`

4. **Deploy**: Railway will automatically deploy

5. **Generate Domain**:
   - Go to "Settings" → "Networking"
   - Click "Generate Domain"

---

### Option 3: Fly.io (Global Edge Network)

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login to Fly**:
   ```bash
   fly auth login
   ```

3. **Launch the app** (from chat_service directory):
   ```bash
   cd /home/henshawmikel/Nera-ai/backend/chat_service
   fly launch
   ```
   - Choose app name: `nera-chat-service` (or your preference)
   - Choose region
   - Don't deploy yet (we need to set secrets first)

4. **Set secrets**:
   ```bash
   fly secrets set DEEPSEEK_API_KEY=your-api-key
   ```

5. **Deploy**:
   ```bash
   fly deploy
   ```

6. **Get your URL**:
   ```bash
   fly status
   ```

---

### Option 4: Docker (Self-Hosted)

1. **Build the Docker image**:
   ```bash
   cd /home/henshawmikel/Nera-ai/backend/chat_service
   docker build -t nera-chat-service .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     -p 8001:8001 \
     -e DEEPSEEK_API_KEY=your-api-key \
     --name nera-chat \
     nera-chat-service
   ```

3. **Check logs**:
   ```bash
   docker logs nera-chat
   ```

---

### Option 5: Heroku

1. **Install Heroku CLI**: https://devcenter.heroku.com/articles/heroku-cli

2. **Login**:
   ```bash
   heroku login
   ```

3. **Create app**:
   ```bash
   cd /home/henshawmikel/Nera-ai/backend/chat_service
   heroku create nera-chat-service
   ```

4. **Set environment variables**:
   ```bash
   heroku config:set DEEPSEEK_API_KEY=your-api-key
   ```

5. **Deploy**:
   ```bash
   git push heroku main
   ```

---

## Post-Deployment Steps

### 1. Test Your Deployment

```bash
# Health check
curl https://your-service-url.com/health

# Test chat endpoint
curl -X POST https://your-service-url.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Hello, what can you help me with?"
      }
    ]
  }'
```

### 2. Update Frontend Configuration

Update your frontend environment variables to point to the deployed service:

```env
VITE_CHAT_SERVICE_URL=https://your-service-url.com
```

### 3. Monitor Your Service

- Check logs regularly
- Set up uptime monitoring (e.g., UptimeRobot, Pingdom)
- Monitor API usage and costs

---

## Troubleshooting

### CORS Issues
If you get CORS errors, ensure your frontend URL is added to the `allow_origins` list in `main.py`.

### Environment Variables Not Loading
- Verify the variable name is exactly `DEEPSEEK_API_KEY`
- Check deployment platform's environment variable settings
- Restart the service after adding variables

### Port Issues
- Most platforms automatically set the `PORT` environment variable
- The service uses port 8001 by default but will use `$PORT` if available

### Memory Issues
- If the service crashes due to memory, upgrade your plan
- Consider implementing request queuing for high traffic

---

## Cost Estimates

- **Render Free Tier**: Free (with limitations)
- **Railway**: ~$5/month for basic usage
- **Fly.io**: Free tier available, ~$2-5/month for basic usage
- **Heroku**: ~$7/month (Eco dyno)

---

## Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Use environment variables** for all secrets
3. **Enable HTTPS** - Most platforms do this automatically
4. **Rate limiting** - Consider adding rate limiting for production
5. **API key rotation** - Regularly rotate your DeepSeek API key

---

## Need Help?

- Check service logs for errors
- Review the platform's documentation
- Ensure all environment variables are set correctly
