# Cloudflare Deployment Guide for Fractured Survival Brain

This guide explains how to deploy the Fractured Survival AI Brain system to Cloudflare Workers instead of Emergent.

## Architecture Overview

The system consists of:
1. **Backend API** (Python/FastAPI) → Cloudflare Workers
2. **Frontend** (React) → Cloudflare Pages
3. **Database** (MongoDB Atlas) → Keep using MongoDB Atlas
4. **Voice** (ElevenLabs) → Keep using ElevenLabs API
5. **LLM** (OpenAI) → Use OpenAI API directly (replaces Emergent)

## Prerequisites

1. [Cloudflare Account](https://dash.cloudflare.com/sign-up)
2. [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) installed
3. MongoDB Atlas account (existing)
4. OpenAI API key
5. ElevenLabs API key

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Database
MONGO_URL=mongodb+srv://your-connection-string
DB_NAME=survival-ai-2-base

# LLM - Use OpenAI directly (replaces EMERGENT_LLM_KEY)
OPENAI_API_KEY=sk-your-openai-api-key

# Voice
ELEVENLABS_API_KEY=sk_your-elevenlabs-key

# CORS
CORS_ORIGINS=*

# Frontend URL (update after deployment)
REACT_APP_BACKEND_URL=https://your-worker.your-subdomain.workers.dev
```

## Step 1: Deploy Backend to Cloudflare Workers

### Option A: Cloudflare Workers (Python - Beta)

Cloudflare Workers now supports Python (in beta). However, for full FastAPI compatibility, we recommend **Option B**.

### Option B: Cloudflare Workers with Docker (Recommended)

Since FastAPI uses features not fully supported in Workers Python runtime, deploy using Cloudflare's container support or use a VPS with Cloudflare Tunnel.

#### Using Cloudflare Tunnel (Recommended for FastAPI)

1. Install cloudflared:
```powershell
winget install Cloudflare.cloudflared
```

2. Authenticate:
```powershell
cloudflared tunnel login
```

3. Create a tunnel:
```powershell
cloudflared tunnel create fractured-survival
```

4. Configure the tunnel (create `config.yml`):
```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: C:\Users\YOUR_USER\.cloudflared\YOUR_TUNNEL_ID.json

ingress:
  - hostname: api.your-domain.com
    service: http://localhost:8001
  - hostname: npc.your-domain.com
    service: http://localhost:9000
  - service: http_status:404
```

5. Run your services locally and start the tunnel:
```powershell
# Terminal 1: Start backend
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001

# Terminal 2: Start NPC service
cd npc_system
python npc_service.py

# Terminal 3: Start tunnel
cloudflared tunnel run fractured-survival
```

### Option C: Deploy to Cloudflare Pages with Functions

For simpler APIs, you can use Cloudflare Pages Functions. Create a `functions` folder in your project.

## Step 2: Deploy Frontend to Cloudflare Pages

1. Build the frontend:
```powershell
cd frontend
npm install
npm run build
```

2. Deploy to Cloudflare Pages:
```powershell
# Install Wrangler if not already
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Deploy
wrangler pages deploy build --project-name fractured-survival-frontend
```

3. Set environment variables in Cloudflare Dashboard:
   - Go to Workers & Pages → Your Project → Settings → Environment Variables
   - Add `REACT_APP_BACKEND_URL` = `https://api.your-domain.com`

## Step 3: Set Up Secrets in Cloudflare

For Workers deployment, set secrets via Wrangler:

```powershell
cd backend
wrangler secret put MONGO_URL
wrangler secret put OPENAI_API_KEY
wrangler secret put ELEVENLABS_API_KEY
```

## Step 4: DNS Configuration

If using Cloudflare Tunnel:
1. Go to Cloudflare Dashboard → DNS
2. Add CNAME records pointing to your tunnel:
   - `api` → `YOUR_TUNNEL_ID.cfargotunnel.com`
   - `npc` → `YOUR_TUNNEL_ID.cfargotunnel.com`

## WebSocket Support

Cloudflare Workers and Tunnels support WebSockets. The existing WebSocket implementation in `websocket_handler.py` will work.

For Durable Objects (persistent WebSocket connections):
1. Enable Durable Objects in your Cloudflare account
2. Configure in `wrangler.toml`

## Migration Checklist

- [x] Replace `emergentintegrations` with `openai` SDK
- [x] Update `brain.py` to use LLM adapter
- [x] Update `conversation_groups.py` to use LLM adapter
- [x] Update `npc_service.py` for Speech-to-Text
- [x] Create `llm_adapter.py` for OpenAI compatibility
- [x] Update `requirements.txt` files
- [ ] Deploy backend to Cloudflare
- [ ] Deploy frontend to Cloudflare Pages
- [ ] Configure DNS and SSL
- [ ] Test all endpoints
- [ ] Update Unreal Engine connection URLs

## Environment Variable Mapping

| Old (Emergent)        | New (Cloudflare)    |
|-----------------------|---------------------|
| EMERGENT_LLM_KEY      | OPENAI_API_KEY      |
| REACT_APP_BACKEND_URL | REACT_APP_BACKEND_URL (update to Cloudflare URL) |

**Note**: The code now supports both `EMERGENT_LLM_KEY` and `OPENAI_API_KEY` for backwards compatibility.

## Testing

After deployment, test the following endpoints:

```bash
# Health check
curl https://api.your-domain.com/health

# API health
curl https://api.your-domain.com/api/health

# NPC service
curl https://api.your-domain.com/api/npc/list
```

## Troubleshooting

### WebSocket Connection Issues
- Ensure Cloudflare Tunnel or Worker is configured for WebSocket upgrade
- Check CORS settings

### LLM Not Responding
- Verify `OPENAI_API_KEY` is set correctly
- Check API quota on OpenAI dashboard

### MongoDB Connection Errors
- Whitelist Cloudflare IP ranges in MongoDB Atlas
- Or use `0.0.0.0/0` for testing (not recommended for production)

## Cost Comparison

| Service | Emergent | Cloudflare |
|---------|----------|------------|
| Backend Hosting | Included | Workers Free Tier: 100k req/day |
| LLM Calls | Through Emergent | Direct OpenAI pricing |
| CDN | Limited | Full Cloudflare CDN |
| WebSockets | Limited | Durable Objects pricing |

## Support

For issues specific to this migration, check:
- Cloudflare Workers docs: https://developers.cloudflare.com/workers/
- OpenAI API docs: https://platform.openai.com/docs/
- ElevenLabs docs: https://elevenlabs.io/docs
