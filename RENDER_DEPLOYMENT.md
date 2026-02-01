# Render Deployment Guide for Fractured Survival

## Quick Deploy (2 minutes)

### Option A: Blueprint Deploy (Recommended)
1. Push your code to GitHub
2. Go to https://dashboard.render.com/
3. Click **"New" → "Blueprint"**
4. Connect your GitHub repo
5. Select the repo with `render.yaml`
6. Render will auto-detect and create both services
7. Add environment variables when prompted

### Option B: Manual Deploy

#### Deploy NPC Service First
1. Go to https://dashboard.render.com/
2. Click **"New" → "Web Service"**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `fractured-survival-npc`
   - **Root Directory**: `npc_system`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn npc_service:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (see below)
6. Click **"Create Web Service"**

#### Deploy Backend Service
1. Click **"New" → "Web Service"** again
2. Configure:
   - **Name**: `fractured-survival-backend`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
3. Add environment variables including `NPC_SERVICE_URL` pointing to your NPC service URL
4. Click **"Create Web Service"**

---

## Environment Variables

### For NPC Service (`fractured-survival-npc`)
| Variable | Value |
|----------|-------|
| `OPENAI_API_KEY` | `sk-proj-QMM9t...` (your key) |
| `ELEVENLABS_API_KEY` | `sk_0b9a17...` (your key) |
| `MONGO_URL` | `mongodb+srv://fracturedsurvival_db_user:6bsaG52zfBGEtov9@fracturedsurvival.mk3tvkc.mongodb.net/?retryWrites=true&w=majority` |
| `DB_NAME` | `fractured_survival` |

### For Backend (`fractured-survival-backend`)
| Variable | Value |
|----------|-------|
| `NPC_SERVICE_URL` | `https://fractured-survival-npc.onrender.com` (your NPC service URL) |
| `OPENAI_API_KEY` | Same as above |
| `MONGO_URL` | Same as above |
| `DB_NAME` | `fractured_survival` |

---

## After Deployment

Your services will be available at:
- **NPC Service**: `https://fractured-survival-npc.onrender.com`
- **Backend**: `https://fractured-survival-backend.onrender.com`

### Update Unreal Engine
In your Unreal project, update the API endpoint to:
```
https://fractured-survival-backend.onrender.com
```

### Update Frontend
In `frontend/.env`:
```
REACT_APP_BACKEND_URL=https://fractured-survival-backend.onrender.com
```

---

## Free Tier Notes

⚠️ **Render free tier spins down after 15 minutes of inactivity**
- First request after sleep takes ~30 seconds to wake up
- For a game, you may want to upgrade to paid ($7/month) for always-on

To keep services awake (free workaround):
- Use a free cron service like https://cron-job.org to ping your `/health` endpoint every 14 minutes

---

## Troubleshooting

### "ModuleNotFoundError"
Check that all dependencies are in `requirements.txt`

### "Connection refused to NPC service"
Make sure `NPC_SERVICE_URL` is set correctly in the backend service environment variables

### Logs
View logs in Render dashboard → Your Service → Logs
