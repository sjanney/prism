# Prism Licensing Worker

A Cloudflare Workers-based licensing system for Prism Pro.

## Quick Start

### 1. Prerequisites

- [Node.js](https://nodejs.org/) (v18+)
- [Cloudflare Account](https://dash.cloudflare.com/sign-up) (free)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/)

### 2. Install Dependencies

```bash
cd licensing-worker
npm install
```

### 3. Login to Cloudflare

```bash
wrangler login
```

### 4. Create KV Namespace

```bash
wrangler kv:namespace create LICENSES
```

Copy the `id` from the output and replace `YOUR_KV_NAMESPACE_ID` in `wrangler.toml`.

### 5. Set API Secret

Generate a secure random secret:

```bash
openssl rand -hex 32
```

Set it as a Cloudflare secret:

```bash
wrangler secret put API_SECRET
# Paste your secret when prompted
```

**Save this secret** - you'll need it for the admin tools.

### 6. Deploy

```bash
wrangler deploy
```

You'll get a URL like: `https://prism-licensing.{your-subdomain}.workers.dev`

## API Endpoints

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/validate?key=XXXX` | GET | Validate a license key |
| `/` | GET | Health check |

### Admin Endpoints (Require API_SECRET)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/create` | POST | Create a new license |
| `/admin/revoke` | POST | Revoke a license |
| `/admin/list` | GET | List all licenses |
| `/admin/lookup?email=XXX` | GET | Find licenses by email |

All admin endpoints require the header:
```
Authorization: Bearer YOUR_API_SECRET
```

## Usage Examples

### Create a License

```bash
curl -X POST https://YOUR_WORKER_URL/admin/create \
  -H "Authorization: Bearer YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "tier": "pro",
    "months": 1
  }'
```

Response:
```json
{
  "success": true,
  "key": "PRISM-PRO-ABCD-EFGH-IJKL-MNOP",
  "license": {
    "tier": "pro",
    "email": "customer@example.com",
    "created_at": "2026-01-05T...",
    "expires_at": "2026-02-05T..."
  }
}
```

### Validate a License

```bash
curl "https://YOUR_WORKER_URL/validate?key=PRISM-PRO-ABCD-EFGH-IJKL-MNOP"
```

Response:
```json
{
  "valid": true,
  "tier": "pro",
  "expires_at": "2026-02-05T...",
  "days_remaining": 31
}
```

### Revoke a License

```bash
curl -X POST https://YOUR_WORKER_URL/admin/revoke \
  -H "Authorization: Bearer YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"key": "PRISM-PRO-ABCD-EFGH-IJKL-MNOP"}'
```

## Development

### Local Development

```bash
npm run dev
```

This starts a local server on `localhost:8787`.

### Testing

Create a `.dev.vars` file for local secrets:

```
API_SECRET=test-secret-for-development
```

Then use the dev server with:

```bash
curl -X POST http://localhost:8787/admin/create \
  -H "Authorization: Bearer test-secret-for-development" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@test.com", "tier": "pro", "months": 1}'
```

## Security Notes

- The API_SECRET is stored in Cloudflare's secure secrets storage
- Never commit `.dev.vars` to git (it's in `.gitignore`)
- All admin endpoints require authentication
- License keys are stored in Cloudflare KV (encrypted at rest)
- CORS is enabled for client-side validation

## Costs

Cloudflare Workers free tier includes:
- 100,000 requests/day
- 1,000 KV writes/day
- 100,000 KV reads/day

This is more than enough for most licensing use cases.
