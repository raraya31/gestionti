# Mobile Webhook Router (n8n)

An automated **voice-to-text command router** for Gestion TI Informatique. Speak (or type)
a command on your phone, an automation POSTs it to an n8n webhook, **Claude 3.5 Sonnet**
classifies the intent, and n8n executes a real operation, then replies with a short summary.

- **Live workflow:** https://n8n.gestionti.info/workflow/xVVBs3c3QljJrIQ1
- **Webhook (production):** `POST https://n8n.gestionti.info/webhook/mobile-router`
- **Webhook (editor test):** `POST https://n8n.gestionti.info/webhook-test/mobile-router`
- **Importable copy:** [`Mobile_Webhook_Router.json`](./Mobile_Webhook_Router.json)
- **Tester:** [`../scripts/Test-MobileWebhookRouter.ps1`](../scripts/Test-MobileWebhookRouter.ps1)

## Request payload

```json
{ "command": "string", "source": "mobile_voice" }
```

## Response payload

```json
{ "status": "ok", "action": "GENERATE_SCRIPT", "summary": "Script saved to ...", "timestamp": "2026-08-12T01:33:43.116Z" }
```

## The three routed actions

| Intent | What it does | Nodes |
|--------|--------------|-------|
| **MODIFY_WORKFLOW** | `GET /api/v1/workflows/{id}` → Claude rewrites the JSON logic → `PUT /api/v1/workflows/{id}` | n8n Get Workflow → Prepare Modify Prompt → Claude Modify Workflow → Extract Updated Workflow → n8n Update Workflow |
| **GENERATE_SCRIPT** | Claude writes a full PowerShell/Python script; n8n saves it to `/claude-workspace/scripts/` | Script to Binary → Save Script to Disk |
| **EXECUTE_API** | Claude formats a payload and n8n calls **HaloPSA** or **Microsoft Graph** | Route Target System → HaloPSA / Microsoft Graph API Call |

## Flow

```
Mobile Voice Webhook (POST)
  └─ Normalize Input            (body.command / body.source, with defaults)
     └─ Build Router Prompt     (builds the Claude request body)
        └─ Claude Router (Parse Intent)   → api.anthropic.com/v1/messages, claude-3-5-sonnet
           └─ Extract Intent    (JSON.parse of Claude's reply)
              └─ Route Action   (Switch on $json.action)
                 ├─ MODIFY_WORKFLOW → … → Respond - Modify
                 ├─ GENERATE_SCRIPT → … → Respond - Script
                 └─ EXECUTE_API   → Route Target System
                                     ├─ halopsa  → … → Respond - HaloPSA
                                     └─ msgraph  → … → Respond - MS Graph
```

Each branch ends in its own **Respond to Webhook** node, so the caller (your phone) receives
the execution summary synchronously. Swap or add a Telegram / Gmail / Twilio node before the
respond node if you also want a push notification.

## Credentials

The importable JSON is pre-wired to the credentials that already exist in this instance:

| Node(s) | Credential type | Credential |
|---------|-----------------|-----------|
| Claude Router (Parse Intent), Claude Modify Workflow | HTTP Header Auth (`x-api-key`) | **Anthropic API (x-api-key)** (`ZlSbBLrOrNxGENjr`) |
| HaloPSA API Call | OAuth2 | **HaloPSA - Generic OAuth2** (`DgMhUz8gJRLimxV4`) |
| Microsoft Graph API Call | OAuth2 | **Graph App-Only - GestionTI Mail** (`4wyhPuBINu2NwRTG`) |
| n8n Get Workflow, n8n Update Workflow | HTTP Header Auth (`X-N8N-API-KEY`) | **create one** — see below |

> The Anthropic credential must supply the header **`x-api-key`** with your Anthropic key.
> The `anthropic-version: 2023-06-01` and `content-type` headers are already set on the node.

### Create the n8n REST API credential (for MODIFY_WORKFLOW)

1. In n8n: **Settings → n8n API → Create an API key**.
2. **Credentials → New → Header Auth**: Name `X-N8N-API-KEY`, Value = the API key.
3. Select that credential on **n8n Get Workflow** and **n8n Update Workflow**.
4. (Optional) Set an env var `N8N_API_BASE_URL` (e.g. `https://n8n.gestionti.info`); the nodes
   fall back to `http://localhost:5678` if it is unset.

## One-time host prerequisite (GENERATE_SCRIPT)

The **Save Script to Disk** node writes to `/claude-workspace/scripts/`. That directory must
exist on the machine running n8n and be writable by the n8n process:

```bash
mkdir -p /claude-workspace/scripts
```

(If n8n runs in Docker, create/mount it inside the container.) Without it the node returns
`ENOENT: no such file or directory`.

## Testing

### Verified — GENERATE_SCRIPT pipeline (execution `8464`)

A pinned-data test run confirmed the routing and logic end to end:

- `Normalize Input` extracted the command from `body`
- `Extract Intent` parsed Claude's JSON → `GENERATE_SCRIPT`
- `Route Action` sent the item to **output #1 only** (correct branch isolation)
- `Script to Binary` produced a 204-byte `Get-DiskSpace.ps1`
- `Save Script to Disk` was the only failure — because `/claude-workspace/scripts/` did not yet
  exist on the host (fixed by the `mkdir` above)

### Live test from PowerShell

```powershell
# Production URL (workflow must be Active, and node credentials selected)
./scripts/Test-MobileWebhookRouter.ps1 -Command "Write a PowerShell script that reports free disk space on all fixed drives"

# Editor test URL (open the workflow, click 'Listen for test event' first)
./scripts/Test-MobileWebhookRouter.ps1 -Command "Create a HaloPSA ticket: printer down in Suite 200" -Test
```

### Import into another n8n instance

**Workflows → Import from File →** `n8n/Mobile_Webhook_Router.json`, then confirm the
credential selections on the six HTTP Request nodes.

## Security notes

- No secrets are stored in this repo — only credential **IDs/names**; the secret values live in
  n8n's encrypted credential store.
- The webhook is unauthenticated by design (public inbound URL). If you expose it beyond your own
  automation, add Header Auth on the **Mobile Voice Webhook** node (e.g. a shared secret your phone
  sends) or put it behind a reverse proxy.
- `MODIFY_WORKFLOW` lets Claude rewrite live workflow JSON. Review changes / keep versioning on.
