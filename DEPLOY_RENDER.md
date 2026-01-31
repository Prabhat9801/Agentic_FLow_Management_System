# 🚀 Render Deployment Guide

Step-by-step guide to deploy FMS on Render.

---

## 📋 Pre-Deployment Checklist

- ✅ Code pushed to GitHub
- ✅ `.env` file NOT committed (it's in `.gitignore`)
- ✅ Google OAuth credentials file ready
- ✅ OpenAI API key ready
- ✅ `requirements.txt` up to date

---

## 🔧 Step 1: Prepare Google OAuth for Production

### Option A: Service Account (Recommended for Production)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project
3. Go to "IAM & Admin" → "Service Accounts"
4. Click "Create Service Account"
5. Give it a name (e.g., "fms-agent")
6. Grant roles: "Editor" (or specific Drive/Sheets permissions)
7. Create and download JSON key
8. Share your Google Sheets folder with the service account email

### Option B: OAuth Token (Simpler)

1. Run locally first:
   ```bash
   python main_cli.py "test"
   ```
2. This creates `token.json` after OAuth flow
3. Upload `token.json` to Render as environment file

---

## 📦 Step 2: Deploy to Render

### 1. Create Web Service

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure service:

```
Name: fms-agent
Environment: Python 3
Branch: main
Root Directory: (leave empty)

Build Command:
pip install -r requirements.txt

Start Command:
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 2. Set Environment Variables

Add these in Render dashboard under "Environment":

```env
OPENAI_API_KEY=sk-...your-key...
OPENAI_MODEL=gpt-4o
TEMPERATURE=1.0
PROJECT_BASE_DIR=/opt/render/project/src/projects
PYTHON_VERSION=3.11.0
```

### 3. Add Google Credentials

**Option A: Environment Variable (Service Account)**

1. Base64 encode your service account JSON:
   ```bash
   # Linux/Mac
   base64 -i service-account.json
   
   # Windows PowerShell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("service-account.json"))
   ```

2. Add environment variable:
   ```env
   GOOGLE_APPLICATION_CREDENTIALS_JSON=<base64-encoded-json>
   ```

3. Update `backend/fms_agent.py` to decode on startup:
   ```python
   import base64
   import json
   
   creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
   if creds_json:
       creds_data = json.loads(base64.b64decode(creds_json))
       # Use for authentication
   ```

**Option B: Secret Files**

1. In Render dashboard, go to "Environment" → "Secret Files"
2. Add file:
   - Filename: `token.json` or `credentials.json`
   - Contents: Paste JSON content
3. File will be available at `/etc/secrets/token.json`

### 4. Configure Persistent Storage (Optional)

To keep project files across redeploys:

1. Go to "Disks" tab
2. Add disk:
   - Name: `projects`
   - Mount Path: `/opt/render/project/src/projects`
   - Size: 1 GB (or as needed)

### 5. Deploy!

1. Click "Create Web Service"
2. Render will build and deploy
3. Wait for "Live" status
4. Access at: `https://fms-agent.onrender.com` (or your service URL)

---

## 🔒 Security Considerations

### ⚠️ Important Security Notes

1. **Never commit secrets:**
   - `.env` file
   - `token.json`
   - `credentials.json`
   - API keys

2. **Protect your endpoint:**
   ```python
   # Add authentication middleware
   from fastapi import Header, HTTPException
   
   async def verify_token(x_api_key: str = Header(None)):
       if x_api_key != os.getenv("API_SECRET_KEY"):
           raise HTTPException(status_code=401)
   ```

3. **Use environment-specific configs:**
   ```python
   ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
   
   if ENVIRONMENT == "production":
       # Stricter settings
       CORS_ORIGINS = ["https://yourdomain.com"]
   else:
       CORS_ORIGINS = ["*"]
   ```

---

## 📊 Monitoring & Logs

### View Logs in Render

1. Go to your service dashboard
2. Click "Logs" tab
3. See real-time application logs

### Check Health

```bash
curl https://your-service.onrender.com/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "FMS Backend",
  "version": "2.0.0",
  "timestamp": "2026-01-30T10:00:00"
}
```

---

## 🐛 Troubleshooting

### Build Fails

**Issue:** "Requirements installation failed"

**Solution:**
- Check `requirements.txt` has correct package names
- Verify Python version compatibility
- Check Render build logs for specific error

### Application Crashes on Start

**Issue:** "Application failed to start"

**Solutions:**
1. Check environment variables are set
2. Verify start command is correct
3. Check logs for detailed error
4. Test locally first: `cd backend && uvicorn main:app`

### WebSocket Connection Issues

**Issue:** "WebSocket closed immediately"

**Solution:**
- Render supports WebSockets on paid plans
- Free tier might have limitations
- Check Render plan features

### Google OAuth Fails

**Issue:** "Authentication error"

**Solutions:**
1. Verify credentials/token file is accessible
2. Check file path in code matches Render environment
3. For service accounts, ensure proper permissions
4. Check Google Cloud Console for API errors

### Projects Not Persisting

**Issue:** "Projects disappear after redeploy"

**Solution:**
- Add Render Disk for persistent storage
- Mount at `/opt/render/project/src/projects`
- Or use external storage (S3, Google Cloud Storage)

---

## 🔄 Updates & CI/CD

### Automatic Deploys

Render auto-deploys when you push to main branch:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

Render detects push → builds → deploys automatically!

### Manual Deploy

In Render dashboard:
1. Go to your service
2. Click "Manual Deploy" → "Deploy latest commit"

---

## 💰 Cost Optimization

### Free Tier Limitations

- Services spin down after 15 mins of inactivity
- First request after sleep takes ~30 seconds
- 750 hours/month free (enough for 1 service)

### Upgrade to Paid

For production use, consider:
- **Starter**: $7/month - always on, no spin down
- **Standard**: $25/month - more resources, better performance
- **Pro**: $85/month - high performance, priority support

### Cost Reduction Tips

1. Use lightweight models for testing:
   ```env
   OPENAI_MODEL=gpt-4o-mini  # Cheaper than gpt-4o
   ```

2. Optimize LLM calls:
   - Cache common responses
   - Reduce temperature for consistency
   - Use fewer retries

3. Monitor usage:
   - Check Render metrics
   - Monitor OpenAI usage dashboard
   - Set budget alerts

---

## ✅ Post-Deployment Checklist

- ✅ Health endpoint responding
- ✅ WebSocket connects successfully
- ✅ Can create test workflow
- ✅ Projects saved correctly
- ✅ Google Sheets created successfully
- ✅ Logs visible in dashboard
- ✅ Custom domain configured (if applicable)
- ✅ SSL certificate active
- ✅ Monitoring/alerts set up

---

## 🎉 You're Live!

Your FMS is now production-ready and accessible worldwide!

**Share your URL:** `https://your-service.onrender.com`

**Test it:**
1. Open URL in browser
2. Type a workflow prompt
3. Watch real-time agent decisions
4. Get Google Sheets link instantly!

---

## 📚 Additional Resources

- [Render Documentation](https://render.com/docs)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [OpenAI API](https://platform.openai.com/docs)

---

**Questions?** Check the main [README.md](README.md) or open an issue!
