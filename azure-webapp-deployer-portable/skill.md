---
name: azure-webapp-deployer-portable
description: Deploy a static HTML site or simple Node.js app to Azure App Service with Microsoft Entra ID (Easy Auth) authentication. Works on any Microsoft employee's personal Azure subscription. Asks for Service Tree ID and auto-detects everything else. Use when someone wants to publish an internal web app to Azure.
---

# Azure Web App Deployer (Portable)

Deploys static HTML sites and simple Node.js apps to Azure App Service with Microsoft Entra ID authentication, restricted to the Microsoft tenant. Designed to work on **any Microsoft employee's machine** with their own Azure subscription.

## Trigger

Use this skill when the user:
- Wants to deploy an HTML file, visualization, or web app to Azure
- Asks to "make this a website" or "publish this to Azure"
- Needs a Microsoft-authenticated web app for internal sharing
- Wants to update/redeploy an existing Azure web app

## Before You Start — Gather Information

Before running any commands, you MUST ask the user for these things (use the `ask_user` tool):

### 1. Service Tree ID (REQUIRED)
Ask: "What is your team's Service Tree ID? This is required by Microsoft policy for Azure app registrations. You can find yours at https://servicetree.msftcloudes.com"

Store the value they provide as `$serviceTreeId` for use in Step 4.

### 2. What to deploy
Ask: "What file(s) do you want to deploy?" — identify the HTML file, folder, or app they want published.

### 3. App name
Ask: "What should the app be called? This becomes the URL: `<name>.azurewebsites.net`"

## Step 0: Find Azure CLI

The Azure CLI may or may not be on PATH. Try to locate it:

```powershell
# Try PATH first
$azCmd = (Get-Command az -ErrorAction SilentlyContinue)?.Source
# Common Windows install locations
if (-not $azCmd) {
    $candidates = @(
        "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
        "C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
        "$env:LOCALAPPDATA\Programs\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $azCmd = $c; break }
    }
}
# macOS / Linux
if (-not $azCmd) {
    $candidates = @("/usr/local/bin/az", "/opt/homebrew/bin/az", "/usr/bin/az")
    foreach ($c in $candidates) {
        if (Test-Path $c) { $azCmd = $c; break }
    }
}
if (-not $azCmd) {
    Write-Error "Azure CLI not found. Install it: https://aka.ms/installazurecli"
}
```

If Azure CLI is not installed, tell the user to install it:
- **Windows**: `winget install Microsoft.AzureCLI`
- **macOS**: `brew install azure-cli`
- **Linux**: `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`

Then have them log in: `& $azCmd login`

## Step 1: Detect Subscription and Tenant

```powershell
$account = & $azCmd account show -o json 2>&1 | ConvertFrom-Json
$subId = $account.id
$tenantId = $account.tenantId
$userName = $account.user.name
Write-Host "Logged in as: $userName"
Write-Host "Subscription: $($account.name) ($subId)"
Write-Host "Tenant: $tenantId"
```

If this fails, the user needs to log in first: `& $azCmd login`

If they have multiple subscriptions, list them and ask which to use:
```powershell
& $azCmd account list -o table --query "[].{Name:name, Id:id, State:state}"
```
Then set it: `& $azCmd account set --subscription "<chosen-id>"`

## Step 2: Create or Reuse Resource Group and App Service Plan

### Pick a region
Try regions in this order (US regions often have zero App Service quota for personal subscriptions):
1. Canada Central
2. East US 2
3. West US 2
4. North Europe

### Create resource group
```powershell
$rgName = "rg-webapps"
$location = "canadacentral"
& $azCmd group create --name $rgName --location $location -o none
```

### Create App Service Plan (or reuse existing)
```powershell
$planName = "plan-webapps"
# Check if plan already exists
$existingPlan = & $azCmd appservice plan show --name $planName --resource-group $rgName -o json 2>$null | ConvertFrom-Json
if (-not $existingPlan) {
    & $azCmd appservice plan create `
        --name $planName `
        --resource-group $rgName `
        --sku B1 `
        --is-linux `
        --location $location `
        -o none
    Write-Host "Created App Service Plan: $planName (B1 Linux, $location)"
} else {
    Write-Host "Reusing existing plan: $planName"
}
```

**If plan creation fails due to quota**, try the next region in the list. This is the most common failure point.

## Step 3: Prepare the Deploy Folder

Create a temporary deploy folder with the user's content:

### For a single HTML file:
```powershell
$deployDir = Join-Path $env:TEMP "azure-deploy-$appName"
New-Item -ItemType Directory -Path $deployDir -Force | Out-Null
```

#### server.js (minimal Node.js static server)
```javascript
const http = require("http");
const fs = require("fs");
const path = require("path");
const PORT = process.env.PORT || 8080;
http.createServer((req, res) => {
  const file = path.join(__dirname, "index.html");
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(500); res.end("Error"); return; }
    res.writeHead(200, {"Content-Type":"text/html"});
    res.end(data);
  });
}).listen(PORT, () => console.log("Listening on " + PORT));
```

#### package.json
```json
{"name":"<app-name>","version":"1.0.0","scripts":{"start":"node server.js"}}
```

Copy the target HTML file as `index.html` into the deploy folder.

### For multi-file apps:
Expand server.js to serve multiple files with proper MIME types:
```javascript
const http = require("http");
const fs = require("fs");
const path = require("path");
const PORT = process.env.PORT || 8080;
const MIME = {
  ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
  ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg",
  ".svg": "image/svg+xml", ".ico": "image/x-icon", ".woff2": "font/woff2"
};
http.createServer((req, res) => {
  let filePath = path.join(__dirname, req.url === "/" ? "index.html" : req.url);
  fs.readFile(filePath, (err, data) => {
    if (err) { res.writeHead(404); res.end("Not found"); return; }
    const ext = path.extname(filePath);
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    res.end(data);
  });
}).listen(PORT, () => console.log("Listening on " + PORT));
```

## Step 4: Deploy the App

```powershell
cd $deployDir
& $azCmd webapp up `
    --name $appName `
    --resource-group $rgName `
    --plan $planName `
    --runtime "NODE:20-lts"
```

**IMPORTANT:** Run from inside the deploy folder.

First deployment takes ~2 minutes (B1 cold start). Wait for completion.

### Verify the site is live BEFORE adding auth:
```powershell
Start-Sleep -Seconds 10
$r = Invoke-WebRequest -Uri "https://$appName.azurewebsites.net" -UseBasicParsing -TimeoutSec 60
"Status: $($r.StatusCode), Length: $($r.Content.Length)"
```

If the site returns a small page (~44KB) that says "Sign in to your account" or "Hey, Node developers!", the Node server hasn't started yet. Wait 2 minutes and retry. If it persists, check that `server.js` and `package.json` are in the deployed content.

You MUST confirm the site returns the user's HTML content (200 OK with correct content) before proceeding to auth.

## Step 5: Create App Registration

Use the Service Tree ID the user provided earlier:

```powershell
$app = & $azCmd ad app create `
    --display-name "$appName" `
    --web-redirect-uris "https://$appName.azurewebsites.net/.auth/login/aad/callback" `
    --sign-in-audience "AzureADMyOrg" `
    --service-management-reference "$serviceTreeId" `
    -o json 2>&1 | ConvertFrom-Json
$clientId = $app.appId
Write-Host "App Registration created. Client ID: $clientId"
```

### CRITICAL: Enable ID Token Issuance

**This step is REQUIRED. Without it, users get HTTP 401 after login.**

```powershell
& $azCmd ad app update `
    --id $clientId `
    --web-redirect-uris "https://$appName.azurewebsites.net/.auth/login/aad/callback" `
    --enable-id-token-issuance true
```

## Step 6: Configure Easy Auth (via REST API)

The `az webapp auth` CLI has v1/v2 version conflicts. Always use the REST API directly:

```powershell
$token = & $azCmd account get-access-token --resource "https://management.azure.com" --query accessToken -o tsv

$body = @{
  properties = @{
    platform = @{
      enabled = $true
      runtimeVersion = "~1"
    }
    globalValidation = @{
      requireAuthentication = $true
      unauthenticatedClientAction = "RedirectToLoginPage"
      redirectToProvider = "aad"
    }
    identityProviders = @{
      azureActiveDirectory = @{
        enabled = $true
        login = @{ disableWWWAuthenticate = $false }
        registration = @{
          clientId = $clientId
          openIdIssuer = "https://login.microsoftonline.com/$tenantId/v2.0"
        }
        validation = @{
          allowedAudiences = @(
            $clientId,
            "api://$clientId",
            "https://$appName.azurewebsites.net"
          )
          defaultAuthorizationPolicy = @{ allowedPrincipals = @{} }
          jwtClaimChecks = @{}
        }
      }
    }
    login = @{
      tokenStore = @{ enabled = $false }
      cookieExpiration = @{
        convention = "FixedTime"
        timeToExpiration = "08:00:00"
      }
      nonce = @{
        validateNonce = $true
        nonceExpirationInterval = "00:05:00"
      }
      preserveUrlFragmentsForLogins = $false
    }
    httpSettings = @{
      requireHttps = $true
      forwardProxy = @{ convention = "NoProxy" }
      routes = @{ apiPrefix = "/.auth" }
    }
  }
} | ConvertTo-Json -Depth 10

$headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }
$uri = "https://management.azure.com/subscriptions/$subId/resourceGroups/$rgName/providers/Microsoft.Web/sites/$appName/config/authsettingsV2?api-version=2022-03-01"
Invoke-RestMethod -Uri $uri -Method PUT -Headers $headers -Body $body -ContentType "application/json"
```

## Step 7: Verify and Report

```powershell
Write-Host ""
Write-Host "========================================="
Write-Host " Deployment Complete!"
Write-Host "========================================="
Write-Host "URL:            https://$appName.azurewebsites.net"
Write-Host "Resource Group: $rgName"
Write-Host "Plan:           $planName"
Write-Host "Region:         $location"
Write-Host "Auth:           Microsoft Entra ID (Microsoft employees only)"
Write-Host "========================================="
```

Tell the user to open the URL in their browser. It should:
1. Redirect to Microsoft login
2. After signing in, show their content
3. Only Microsoft tenant users can access it

## Redeployment (Future Updates)

To update the app later, just re-run `az webapp up` from the deploy folder:

```powershell
# 1. Copy updated files to deploy folder
# 2. Deploy
cd <deploy-folder>
& $azCmd webapp up --name $appName --resource-group $rgName --plan $planName --runtime "NODE:20-lts"
```

Auth persists across deployments — no need to reconfigure.

## Cleanup

After successful deployment, clean up the temp deploy folder:
```powershell
Remove-Item $deployDir -Recurse -Force
```

## Prerequisites the User Needs

Before this skill can work, the user needs:

| Requirement | How to get it |
|-------------|---------------|
| **Azure subscription** | Most Microsoft FTEs have one via Visual Studio Enterprise. Check https://my.visualstudio.com or the Azure Portal → Subscriptions |
| **Owner or Contributor role** on subscription | Automatic on personal MSDN subscriptions |
| **Azure CLI installed** | `winget install Microsoft.AzureCLI` (Windows) / `brew install azure-cli` (macOS) |
| **Logged in to Azure CLI** | `az login` |
| **Service Tree ID** | From https://servicetree.msftcloudes.com — ask your team lead if unsure |
| **Ability to create App Registrations** | Enabled by default for most Microsoft employees |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `az login` says "no subscriptions found" | No Azure subscription linked | Go to https://my.visualstudio.com → activate Azure benefit |
| App Service plan creation fails (quota) | Region has zero quota for the SKU | Try a different region: Canada Central → East US 2 → West US 2 → North Europe |
| HTTP 401 after adding auth | ID token issuance not enabled | `az ad app update --id $clientId --enable-id-token-issuance true` |
| Site times out / doesn't load | Cold start on B1 plan (~2 min) | Wait 2 minutes after deploy, then retry |
| "Sign in to your account" page (44KB) | Node.js server didn't start | Check `server.js` exists in deployed content, startup is `node server.js` |
| `az webapp auth` errors about v1/v2 | CLI auth extension conflicts | Use the REST API method in Step 6 instead |
| `ServiceManagementReference` error on app create | Missing or invalid Service Tree ID | Ask user to verify their Service Tree ID at https://servicetree.msftcloudes.com |
| SCM/Kudu 401 Unauthorized | Basic auth disabled on SCM site | `az resource update --resource-group $rgName --name scm --namespace Microsoft.Web --resource-type basicPublishingCredentialsPolicies --parent sites/$appName --set properties.allow=true` |
| `az: command not found` | Azure CLI not on PATH | Find it at known install paths or reinstall |

## Key Lessons Learned

1. **Always use `az webapp up`** from inside the deploy folder — it handles Oryx build and startup automatically.
2. **Always enable ID token issuance** — Easy Auth requires it but `az ad app create` doesn't enable it by default.
3. **Always verify the site serves content BEFORE adding auth** — if Node.js fails to start, auth will mask the real error.
4. **Use REST API for auth config** — the `az webapp auth` CLI has v1/v2 version conflicts that cause confusing errors.
5. **B1 cold starts take ~2 minutes** — don't panic if the site doesn't respond immediately after deploy.
6. **Canada Central** is the best starting region — US regions often have zero App Service quota on personal subscriptions.
7. **No client secret needed** for Easy Auth — it only needs the client ID and issuer URL.
8. **Service Tree ID is mandatory** at Microsoft — always ask for it upfront to avoid app registration failures.
