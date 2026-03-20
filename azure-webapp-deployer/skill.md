---
name: azure-webapp-deployer
description: Deploy a static HTML site (or simple Node.js app) to Azure App Service with Microsoft Entra ID authentication. Creates the App Service, app registration, and Easy Auth — all via Azure CLI. Use when the user wants to publish an HTML file, visualization, or single-page app to Azure so Microsoft employees can access it with login.
---

# Azure Web App Deployer

Deploys static HTML sites and simple Node.js apps to Azure App Service with Microsoft Entra ID (Azure AD) authentication, restricted to a single tenant. Handles everything: App Service creation, app registration, Easy Auth configuration, and zip deployment.

## Trigger

Use this skill when the user:
- Wants to deploy an HTML file or visualization to Azure
- Asks to "make this a website" or "publish this to Azure"
- Needs a Microsoft-authenticated web app for internal sharing
- Wants to update/redeploy an existing Azure web app

## Prerequisites

- **Azure CLI** installed at: `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`
- User logged in (`az account show` succeeds)
- The Azure CLI path must be stored in a variable since it's not on PATH:
  ```powershell
  $azCmd = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
  ```

## Key Configuration

- **Service Tree ID** (required for all app registrations): `ab0c20d0-d5a1-4ab9-bb66-286c6c84d930`
- **Microsoft Tenant ID**: `72f988bf-86f1-41af-91ab-2d7cd011db47`
- **Preferred region**: Canada Central (US regions may have zero App Service quota)
- **Preferred SKU**: B1 (Linux)
- **Existing resource group**: `rg-game-imagegen`
- **Existing App Service plan**: `plan-caidr-top10` (B1 Linux, Canada Central)

## Step 1: Prepare the Deploy Folder

Create a flat deploy folder with:

### server.js (minimal Node.js static server)
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

### package.json
```json
{"name":"app-name","version":"1.0.0","scripts":{"start":"node server.js"}}
```

### index.html
Copy the target HTML file as `index.html` in the deploy folder.

**For multi-file apps**, expand server.js to serve multiple files with MIME type detection. But for single-page visualizations, the simple version above works perfectly.

## Step 2: Create and Deploy the App Service

Use `az webapp up` — it handles app creation, Oryx build, and deployment in one command:

```powershell
$azCmd = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
cd <deploy-folder>
& $azCmd webapp up `
  --name <app-name> `
  --resource-group rg-game-imagegen `
  --plan plan-caidr-top10 `
  --runtime "NODE:20-lts"
```

**IMPORTANT:** Run this from inside the deploy folder (`cd deploy` first).

The first deployment takes ~2 minutes (cold start on B1 plan). Wait for "Site started successfully" before proceeding.

### Verify the site is live before adding auth:
```powershell
$r = Invoke-WebRequest -Uri "https://<app-name>.azurewebsites.net" -UseBasicParsing -TimeoutSec 30
"Status: $($r.StatusCode), Length: $($r.Content.Length)"
```
You MUST confirm the site returns your HTML content (200 with correct content length) before proceeding to auth setup.

## Step 3: Create App Registration

```powershell
$azCmd = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
$app = & $azCmd ad app create `
  --display-name "<app-name>" `
  --web-redirect-uris "https://<app-name>.azurewebsites.net/.auth/login/aad/callback" `
  --sign-in-audience "AzureADMyOrg" `
  --service-management-reference "ab0c20d0-d5a1-4ab9-bb66-286c6c84d930" `
  -o json 2>&1 | ConvertFrom-Json
$clientId = $app.appId
```

### CRITICAL: Enable ID Token Issuance

**This step is required for Easy Auth to work. Without it, users get HTTP 401.**

```powershell
& $azCmd ad app update `
  --id $clientId `
  --web-redirect-uris "https://<app-name>.azurewebsites.net/.auth/login/aad/callback" `
  --enable-id-token-issuance true
```

## Step 4: Configure Easy Auth (via REST API)

The `az webapp auth` CLI commands have v1/v2 conflicts. Use the REST API directly for reliable auth configuration:

```powershell
$tenantId = "72f988bf-86f1-41af-91ab-2d7cd011db47"
$subId = & $azCmd account show --query id -o tsv
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
            "https://<app-name>.azurewebsites.net"
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
$uri = "https://management.azure.com/subscriptions/$subId/resourceGroups/rg-game-imagegen/providers/Microsoft.Web/sites/<app-name>/config/authsettingsV2?api-version=2022-03-01"
Invoke-RestMethod -Uri $uri -Method PUT -Headers $headers -Body $body -ContentType "application/json"
```

## Step 5: Verify

Open `https://<app-name>.azurewebsites.net` in the browser. It should:
1. Redirect to Microsoft login
2. After signing in, show your HTML content
3. Only Microsoft tenant users can access it

## Redeployment (Future Updates)

```powershell
$azCmd = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
# 1. Copy updated HTML to deploy folder
Copy-Item <source-html> deploy\index.html -Force
# 2. Deploy from deploy folder
cd deploy
& $azCmd webapp up --name <app-name> --resource-group rg-game-imagegen --plan plan-caidr-top10 --runtime "NODE:20-lts"
cd ..
# 3. Commit to git
git add -A && git commit -m "update" && git push origin master
```

No need to reconfigure auth — it persists across deployments.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| HTTP 401 after adding auth | ID token issuance not enabled | `az ad app update --id $clientId --enable-id-token-issuance true` |
| Site times out / doesn't load | Cold start on B1 plan (~2 min) | Wait 2 minutes after deploy, then retry |
| "Sign in to your account" page (44KB) | Node.js server didn't start; Azure shows default page | Check `server.js` exists in wwwroot, startup command is `node server.js` |
| `az webapp auth` errors about v1/v2 | CLI auth extension conflicts | Use the REST API method in Step 4 instead |
| `ServiceManagementReference` error on app create | Missing Service Tree ID | Add `--service-management-reference "ab0c20d0-d5a1-4ab9-bb66-286c6c84d930"` |
| SCM/Kudu 401 Unauthorized | Basic auth disabled on SCM site | Enable: `az resource update --resource-group <rg> --name scm --namespace Microsoft.Web --resource-type basicPublishingCredentialsPolicies --parent sites/<app-name> --set properties.allow=true` |

## Existing Deployments

| App Name | URL | Resource Group | Plan |
|----------|-----|----------------|------|
| caidr-top10-problems | https://caidr-top10-problems.azurewebsites.net | rg-game-imagegen | plan-caidr-top10 |
| resops-impact-deck | https://resops-impact-deck.azurewebsites.net | rg-game-imagegen | plan-caidr-top10 |
| caidr-room-booking | https://caidr-room-booking.azurewebsites.net | rg-caidr-room-booking | caidr-room-plan |

## Key Lessons Learned

1. **Always use `az webapp up`** from inside the deploy folder — it handles Oryx build and startup automatically.
2. **Always enable ID token issuance** (`--enable-id-token-issuance true`) — Easy Auth requires it but `az ad app create` doesn't enable it by default.
3. **Always verify the site serves content BEFORE adding auth** — if Node.js fails to start, auth will mask the real error.
4. **Use REST API for auth config** — the `az webapp auth` CLI has v1/v2 version conflicts that cause confusing errors.
5. **B1 cold starts take ~2 minutes** — don't panic if the site doesn't respond immediately after deploy.
6. **Canada Central** is the preferred region — US regions may have zero App Service quota.
7. **No client secret needed** for Easy Auth — unlike Static Web Apps custom auth, App Service Easy Auth only needs the client ID and issuer URL.
