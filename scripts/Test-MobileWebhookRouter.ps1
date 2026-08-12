<#
.SYNOPSIS
    Sends a voice-style command to the n8n "Mobile Webhook Router" workflow and
    prints the execution summary it returns.

.DESCRIPTION
    Simulates the payload your phone (voice-to-text shortcut / automation) would
    POST to the webhook:  { "command": "<text>", "source": "mobile_voice" }

    The workflow classifies the command with Claude 3.5 Sonnet and routes it to
    one of three actions (MODIFY_WORKFLOW / GENERATE_SCRIPT / EXECUTE_API), then
    replies with a concise JSON summary.

.PARAMETER Command
    The natural-language instruction to send. This is the text a voice assistant
    would transcribe.

.PARAMETER BaseUrl
    Base URL of the n8n instance. Defaults to https://n8n.gestionti.info

.PARAMETER Test
    Use the n8n TEST webhook path (/webhook-test/...) instead of the production
    path (/webhook/...). The test path only accepts a request while the workflow
    canvas is open with "Listen for test event" active.

.EXAMPLE
    # Ask it to generate a PowerShell script (production URL, workflow must be Active)
    ./Test-MobileWebhookRouter.ps1 -Command "Write a PowerShell script that reports free disk space on all fixed drives"

.EXAMPLE
    # Drive the EXECUTE_API path against Microsoft Graph
    ./Test-MobileWebhookRouter.ps1 -Command "Using Microsoft Graph, list the first 5 users in the tenant"

.EXAMPLE
    # Use the editor test URL while 'Listen for test event' is armed in n8n
    ./Test-MobileWebhookRouter.ps1 -Command "Create a HaloPSA ticket: printer down in Suite 200" -Test

.NOTES
    Author : Gestion TI Informatique
    Works on Windows PowerShell 5.1 and PowerShell 7+.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Command,

    [string]$BaseUrl = 'https://n8n.gestionti.info',

    [string]$WebhookPath = 'mobile-router',

    [switch]$Test
)

$ErrorActionPreference = 'Stop'

# Production vs. test webhook path
$segment = if ($Test) { 'webhook-test' } else { 'webhook' }
$uri = ('{0}/{1}/{2}' -f $BaseUrl.TrimEnd('/'), $segment, $WebhookPath)

# Payload the mobile voice trigger sends
$payload = [ordered]@{
    command = $Command
    source  = 'mobile_voice'
}
$body = $payload | ConvertTo-Json -Depth 5 -Compress

Write-Host "==> POST $uri" -ForegroundColor Cyan
Write-Host "    body: $body" -ForegroundColor DarkGray

try {
    $response = Invoke-RestMethod -Uri $uri -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 120

    Write-Host "`n<== Router response" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10 | Write-Host

    if ($response.summary) {
        Write-Host "`nSummary: $($response.summary)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "`n[ERROR] Request failed." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red

    # Surface the HTTP body n8n returned, if any (helps diagnose 404 / auth / node errors)
    if ($_.Exception.Response) {
        try {
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $raw = $reader.ReadToEnd()
            if ($raw) { Write-Host "Response body: $raw" -ForegroundColor DarkYellow }
        } catch { }
    }

    Write-Host "`nCommon causes:" -ForegroundColor DarkGray
    Write-Host "  * 404  -> workflow not Active (production URL) or 'Listen for test event' not armed (use -Test)." -ForegroundColor DarkGray
    Write-Host "  * 500  -> a node failed; check the execution in n8n (e.g. Anthropic credential not selected)." -ForegroundColor DarkGray
    exit 1
}
