<div align="center">

```
██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗ █████╗ ██╗   ██╗████████╗ ██████╗ 
██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗
██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║███████║██║   ██║   ██║   ██║   ██║
██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║██╔══██║██║   ██║   ██║   ██║   ██║
██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║██║  ██║╚██████╔╝   ██║   ╚██████╔╝
╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ 
```

**Attack Surface Intelligence — Not Just Recon**

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20|%20WSL-f97316?style=for-the-badge&logo=linux&logoColor=white)](https://ubuntu.com)
[![BugBounty](https://img.shields.io/badge/Bug%20Bounty-Ready-ef4444?style=for-the-badge)](https://hackerone.com)
[![Telegram](https://img.shields.io/badge/Telegram-Notify-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org)

> **Most recon tools dump 10,000 URLs and leave you alone.**  
> **ReconAuto tells you exactly where to attack first.**

</div>

---

## The Problem Every Hunter Faces

```
Run recon  ──→  Get 10,000 URLs  ──→  Where do I even start?
                                              │
                                              ▼
                                    Random testing
                                    Duplicate reports  
                                    Wasted hours
```

Every bug bounty hunter faces this. No existing tool solves it.

**ReconAuto does.**

---

## What Makes It Different

```
Other tools:  subfinder → httpx → gau → ???  (you figure out the rest)

ReconAuto:    domain → full attack surface map → prioritized findings → AI report
```

| Feature | Other Tools | ReconAuto |
|---------|-------------|-----------|
| URL Collection | 2-3 sources | 8 sources |
| Subdomain Enum | 2-3 sources | 9 sources |
| API Schema Detection | ✗ | Swagger + GraphQL + WSDL + WADL |
| Parameter Classification | Just collects | Categorized by vuln type |
| Hidden Parameters | ✗ | arjun integration |
| Subdomain Takeover | ✗ | dnsx + 15 signature checks |
| Telegram Notify | ✗ | Auto report + files |
| AI Ready Output | ✗ | REPORT.md → paste to Claude/GPT |
| Priority Findings | ✗ | 🔴 Critical → 🟡 Medium → 🟢 Info |

---

## Installation

```bash
# 1. Clone
git clone https://github.com/Rajib-Mahmud/surfmap
cd reconauto

# 2. Install Go tools (recommended for full power)
bash install.sh

# 3. Install Python tools
pip install -r requirements.txt

# 4. Setup Telegram (optional)
cp .env.example .env
nano .env  # Add your bot token + chat ID
```

---

## Usage

```bash
# Mode 1 — Single domain deep extraction
python3 recon.py target.com --mode 1

# Mode 2 — Full recon with all subdomains
python3 recon.py target.com --mode 2

# Mode 2 — Custom output folder
python3 recon.py target.com --mode 2 -o my_output

# Skip specific modules
python3 recon.py target.com --mode 1 --no-probe --no-tech

# Tool installation guide
python3 recon.py --install
```

---

## What It Collects

### URLs — 8 Sources
| Source | Type |
|--------|------|
| Wayback Machine CDX | Historical |
| CommonCrawl (3 indexes) | Historical |
| URLScan.io | Active |
| OTX AlienVault | Threat Intel |
| gau | Aggregator |
| katana | Live Crawler |
| gospider | Live Crawler + Forms |
| paramspider | Parameter-focused |

### Subdomains — 9 Sources
`subfinder` · `amass` · `assetfinder` · `crt.sh` · `hackertarget` · `RapidDNS` · `BufferOver` · `CertSpotter` · `ThreatCrowd`

### API Schema Detection
```
Swagger/OpenAPI  →  Full endpoint list extracted automatically
GraphQL          →  Introspection query — all types/queries/mutations
WADL             →  Java REST API resources
WSDL             →  SOAP service operations
JSON API         →  REST schema detection
```

### Parameter Intelligence
```
paramspider  →  Historical parameterized URLs
arjun        →  Hidden parameters (not visible in URLs)

Categorized by vulnerability type:
  SSRF/RFI     → ?url=, ?src=, ?path=, ?redirect=
  XSS          → ?q=, ?search=, ?input=, ?name=
  SQLi         → ?id=, ?category=, ?page=, ?search=
  LFI/Path     → ?file=, ?doc=, ?template=, ?view=
  Open Redirect → ?next=, ?return=, ?goto=, ?dest=
```

---

## Priority Output

```
🔴 CRITICAL — Check immediately
   ├── JS secrets found (AWS key, API key, JWT, private key)
   ├── GraphQL introspection enabled
   ├── Subdomain takeover candidates
   └── Sensitive config files exposed (.env, .git, swagger)

🟡 MEDIUM — Check next
   ├── Hidden parameters discovered (arjun)
   ├── SSRF/LFI parameter candidates
   └── Admin panel indicators

🟢 INFO — Full surface map
   ├── All URLs
   ├── API endpoints
   ├── JS files
   └── Parameterized URLs by vuln type
```

---

## Output Files

```
recon_target_20240101_120000/
├── REPORT.md                  ← AI-ready report (paste to Claude/GPT)
├── all_urls.txt               ← Every URL found
├── live_hosts.txt             ← Confirmed live hosts
├── endpoints_api.txt          ← API endpoints
├── js_files.txt               ← JavaScript files
├── parameters.txt             ← Parameterized URLs
├── sensitive_paths.txt        ← Admin/config/backup paths
├── subdomains.txt             ← All subdomains (Mode 2)
├── subdomains_resolved.txt    ← DNS verified (Mode 2)
├── parameters.json            ← Params + high-value flags
├── params_by_vulntype.json    ← SSRF/XSS/SQLi/LFI/Redirect
├── jsluice_endpoints.txt      ← JS-extracted endpoints (AST)
├── jsluice_secrets.json       ← Secrets found in JS
├── api_schema.json            ← Full API schema detail
├── api_schema_endpoints.txt   ← Schema-extracted endpoints
├── arjun_hidden_params.json   ← Hidden parameter findings
├── takeover_candidates.txt    ← Subdomain takeover (Mode 2)
└── active_probe.json          ← Sensitive path probe results
```

---

## AI Workflow

ReconAuto is built around the `master.md` AI framework:

```
Step 1: python3 recon.py target.com --mode 2
Step 2: Open REPORT.md
Step 3: Paste master.md + REPORT.md into Claude/ChatGPT
Step 4: AI analyzes the attack surface
Step 5: You verify and hunt
```

`master.md` teaches AI to think like a senior security researcher — not just look for common bugs, but understand application DNA and find what others miss.

---

## Telegram Integration

Get notified on your phone when recon completes:

```bash
# Setup
cp .env.example .env
nano .env
```

```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id
```

**What gets sent:**
- 📊 Summary message with all stats
- 🔴 Critical findings highlighted
- 📋 `REPORT.md` — paste directly to AI
- 🔗 `all_urls.txt`, `endpoints_api.txt`
- ⚠️ `jsluice_secrets.json` (if secrets found)
- 🎯 `params_by_vulntype.json`
- 🔴 `takeover_candidates.txt` (if found)

Run recon on VPS, get results on your phone. 

---

## Recommended Tools

```bash
bash install.sh  # installs everything
```

| Tool | Install | Purpose |
|------|---------|---------|
| subfinder | go install | Subdomain enum |
| httpx | go install | Live host check |
| katana | go install | Web crawler |
| gau | go install | URL collection |
| dnsx | go install | DNS resolution |
| gospider | go install | Fast crawler |
| jsluice | go install | AST JS analysis |
| waybackurls | go install | Wayback URLs |
| arjun | pip install | Hidden params |
| paramspider | pip install | Param crawler |

**Without tools:** Python fallback (60% coverage)  
**With all tools:** Full power (90%+ coverage)

---

## Options Reference

```
--mode 1        Single domain extraction
--mode 2        Full recon with all subdomains
--no-js         Skip JS analysis (jsluice + regex)
--no-probe      Skip active path probing
--no-tech       Skip tech detection
--no-gospider   Skip gospider crawler
--no-arjun      Skip hidden parameter finder
--no-params     Skip paramspider
--no-dnsx       Skip DNS resolution (Mode 2)
--no-schema     Skip API schema detection
--install       Show tool installation guide
-o OUTPUT       Custom output folder name
```

---

## Legal Disclaimer

> This tool is for **authorized security testing only.**  
> Only use on targets you have **explicit written permission** to test.  
> Applicable to: Bug bounty programs, CTFs, your own infrastructure.  
> The author is **not responsible** for any unauthorized use or damage.

---

## Author

**rajib_mahmud**  
Bug Bounty Hunter & Security Researcher  
HackerOne · Intigriti · HackenProof · CVE Research

---

<div align="center">

**Found a bug? Open an issue.**  
**Tool helped your hunting? Give it a ⭐**

*Recon ends. Hunting begins.*

</div>
