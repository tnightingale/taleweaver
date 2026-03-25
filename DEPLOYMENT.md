# Deploying Taleweaver with Once

This guide covers deploying Taleweaver using [Basecamp Once](https://github.com/basecamp/once), a platform for easy self-hosting of Docker-based web applications.

## Prerequisites

- A server running Linux or macOS (physical server, cloud VPS, Raspberry Pi, or laptop)
- Docker installed (Once can install this for you)
- A domain name pointing to your server's IP address (e.g., `stories.yourdomain.com`)
- API keys for:
  - One LLM provider (Groq, Anthropic, or OpenAI)
  - ElevenLabs (for text-to-speech)

## Building and Publishing the Docker Image

### Option 1: Automated (GitHub Actions) - Recommended

The repository includes a GitHub Actions workflow that automatically builds and publishes Docker images.

**One-time setup:**

1. Fork or push this repository to your GitHub account
2. The workflow runs automatically on:
   - Every push to `main` branch → tagged as `latest`
   - Every new tag (e.g., `v1.0.0`) → tagged with version number
   - Every pull request → tagged as `pr-N` (e.g., `pr-42`)
   - Manual trigger via GitHub Actions UI

**To trigger a build:**

```bash
# Push to main for latest tag
git push origin main

# Or create a version tag
git tag v1.0.0
git push origin v1.0.0
```

The image will be published to: `ghcr.io/YOUR_USERNAME/taleweaver:latest`

**View your published images:** https://github.com/YOUR_USERNAME/taleweaver/pkgs/container/taleweaver

### Option 2: Manual Build and Push

If you prefer to build manually:

```bash
# 1. Log in to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# 2. Build the image (this takes 5-10 minutes)
docker build -t ghcr.io/YOUR_USERNAME/taleweaver:latest .

# 3. Push to registry
docker push ghcr.io/YOUR_USERNAME/taleweaver:latest
```

**Generate a GitHub token:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scope: `write:packages`
4. Copy the token and use it as `GITHUB_TOKEN`

### Option 3: Local Build Only (for testing)

To test the build locally without publishing:

```bash
# Build for your platform only (faster)
docker build -t taleweaver:test .

# Run locally to test
docker run -d -p 80:80 \
  -e LLM_PROVIDER=groq \
  -e GROQ_API_KEY=your-key \
  -e ELEVENLABS_API_KEY=your-key \
  taleweaver:test

# Test health check
curl http://localhost/up
```

## Quick Start

### 1. Install Once

On your server, run:

```bash
curl https://get.once.com | sh
```

This will install Once and its background service.

### 2. Deploy Taleweaver

When Once prompts you to choose an application, select "Enter custom Docker image" and provide:

```
ghcr.io/YOUR_USERNAME/taleweaver:latest
```

Replace `YOUR_USERNAME` with your actual GitHub username.

**Important:** If your repository is private, you'll need to authenticate Once with GitHub:
- The image must be public, OR
- Use `docker login ghcr.io` on your server before running Once

### 3. Configure Hostname

Enter your domain name when prompted (e.g., `stories.yourdomain.com`).

Make sure you have a DNS A record pointing this domain to your server's IP address.

### 4. Set Environment Variables

Once will automatically provide some variables. You need to set:

**Required:**
- `LLM_PROVIDER` - Choose: `groq` (recommended), `anthropic`, or `openai`
- `GROQ_API_KEY` - Your Groq API key (if using Groq)
- `ANTHROPIC_API_KEY` - Your Anthropic API key (if using Claude)
- `OPENAI_API_KEY` - Your OpenAI API key (if using GPT)
- `ELEVENLABS_API_KEY` - Your ElevenLabs API key for voice synthesis

**Optional:**
- `NARRATOR_VOICE_ID` - Custom narrator voice (default: Rachel)
- `CHARACTER_MALE_VOICE_ID` - Custom male character voice
- `CHARACTER_FEMALE_VOICE_ID` - Custom female character voice
- `CHARACTER_CHILD_VOICE_ID` - Custom child character voice

### 5. Access Your App

Once deployment is complete, visit your domain (e.g., `https://stories.yourdomain.com`).

Once automatically provisions SSL certificates via Let's Encrypt.

## Manual Docker Deployment (without Once)

If you prefer to deploy without Once:

### 1. Build the Image

```bash
docker build -t taleweaver .
```

### 2. Run the Container

```bash
docker run -d \
  --name taleweaver \
  -p 80:80 \
  -v taleweaver-storage:/storage \
  -e LLM_PROVIDER=groq \
  -e GROQ_API_KEY=your-key-here \
  -e ELEVENLABS_API_KEY=your-key-here \
  --restart unless-stopped \
  taleweaver
```

### 3. Set Up SSL (Optional but Recommended)

Use a reverse proxy like Caddy or Nginx with Let's Encrypt for SSL.

Example Caddyfile:

```
stories.yourdomain.com {
    reverse_proxy localhost:80
}
```

## PR Preview Deployments (LAN)

Pull requests are automatically built and published to ghcr.io with `pr-N` tags. On a LAN server running Once, you can deploy any PR as a preview instance with its own subdomain and database.

**Prerequisites:** Wildcard DNS (`*.taleweaver.lan`) and mkcert TLS configured on the server. See the [taleweaver-deploy](../taleweaver-deploy/) repo for setup instructions.

**Deploy a PR:**

```bash
once deploy ghcr.io/tnightingale/taleweaver:pr-21 --host pr-21.localhost
# The TLS watcher automatically swaps to https://pr-21.taleweaver.lan
```

Set environment variables for the app via the Once TUI (`once` command) after deploying.

**Remove when done:**

```bash
once remove <app-name>   # e.g., once remove taleweaver.8068f8
```

Each preview instance gets its own storage volume (separate database and files).

## Architecture

Taleweaver runs as a single container with:

- **Port 80**: Caddy web server (reverse proxy)
  - Serves frontend static files
  - Proxies `/api/*` requests to backend
- **Port 8000** (internal): FastAPI backend
- **Volume `/storage`**: Persistent data
  - `/storage/jobs/` - Generated audio files (temporary)
  - `/storage/music/` - Background music library

## Backup & Restore

Once automatically handles backups using the provided hooks:

- **Pre-backup** (`/hooks/pre-backup`): Creates consistent snapshot of job data
- **Post-restore** (`/hooks/post-restore`): Restores job data after backup restoration

To manually backup:

```bash
docker exec taleweaver /hooks/pre-backup
docker cp taleweaver:/storage ./taleweaver-backup
```

To manually restore:

```bash
docker cp ./taleweaver-backup/. taleweaver:/storage
docker exec taleweaver /hooks/post-restore
docker restart taleweaver
```

## Health Checks

Taleweaver exposes a health check endpoint at `/up` (required by Once).

Test it:

```bash
curl http://localhost/up
# Expected: {"status":"ok"}
```

## Updating

### With Once

Once provides automatic updates. Use the dashboard to:
1. Check for updates
2. Install new versions with zero downtime

### Manual Docker Update

```bash
docker pull ghcr.io/yourusername/taleweaver:latest
docker stop taleweaver
docker rm taleweaver
# Run the docker run command from step 2 above
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker logs taleweaver
```

Common issues:
- Missing API keys
- Port 80 already in use
- Storage volume permission issues

### Audio generation fails

Check:
1. ElevenLabs API key is valid
2. ElevenLabs quota hasn't been exceeded
3. LLM provider API key is valid

View backend logs:
```bash
docker exec taleweaver tail -f /var/log/taleweaver.log
```

### Background music not playing

Ensure `/storage/music/` contains:
- `exciting.mp3`
- `heartwarming.mp3`
- `funny.mp3`
- `mysterious.mp3`
- `default.mp3`

These are automatically copied on first run.

## Resource Requirements

**Minimum:**
- 1 CPU core
- 1GB RAM
- 2GB disk space

**Recommended:**
- 2 CPU cores
- 2GB RAM
- 5GB disk space (for audio caching)

## Security Notes

1. **API Keys**: Store securely, never commit to version control
2. **SSL**: Always use HTTPS in production (Once handles this automatically)
3. **Firewall**: Only expose port 80 (HTTP) and 443 (HTTPS)
4. **Updates**: Keep the container updated for security patches

## Support

- GitHub Issues: https://github.com/yourusername/taleweaver/issues
- Documentation: See README.md
- Once Documentation: https://github.com/basecamp/once
