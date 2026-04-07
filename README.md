# Copilot CLI Skills

Reusable skills for [GitHub Copilot CLI](https://docs.github.com/copilot/concepts/agents/about-copilot-cli). Each skill teaches Copilot how to perform a specific task end-to-end.

## Available Skills

| Skill | Description |
|-------|-------------|
| [azure-webapp-deployer-portable](./azure-webapp-deployer-portable/skill.md) | Deploy a static HTML site or Node.js app to Azure App Service with Microsoft Entra ID auth. Works on any Microsoft employee's personal Azure subscription. |

## How to Install a Skill

### Quick Install (one command)

```powershell
# Windows
mkdir "$env:USERPROFILE\.copilot\skills\azure-webapp-deployer-portable" -Force
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/danhgottlieb/copilot-skills/master/azure-webapp-deployer-portable/skill.md" -OutFile "$env:USERPROFILE\.copilot\skills\azure-webapp-deployer-portable\skill.md"
```

```bash
# macOS / Linux
mkdir -p ~/.copilot/skills/azure-webapp-deployer-portable
curl -o ~/.copilot/skills/azure-webapp-deployer-portable/skill.md \
  https://raw.githubusercontent.com/danhgottlieb/copilot-skills/master/azure-webapp-deployer-portable/skill.md
```

Then run `/skills` in Copilot CLI to verify it's loaded.

### Alternative: Install for a specific project

Drop the skill into your project's `.github/skills/` directory. Anyone working in that repo gets the skill automatically:

```
your-repo/
  .github/
    skills/
      azure-webapp-deployer-portable/
        skill.md
```

## Prerequisites

Each skill lists its own prerequisites. For the Azure deployer, you'll need:
- [GitHub Copilot CLI](https://docs.github.com/copilot/concepts/agents/about-copilot-cli) installed
- [Azure CLI](https://aka.ms/installazurecli) installed
- A Microsoft Azure subscription (most FTEs have one via Visual Studio Enterprise)
- Your team's [Service Tree ID](https://servicetree.msftcloudes.com)

## Usage

Once installed, just tell Copilot CLI what you want in natural language:

> "Deploy this HTML file to Azure as an internal website"

Copilot will activate the skill, ask for your Service Tree ID, and handle everything else.
