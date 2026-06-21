<div align="center">

```
███████╗██╗   ██╗██████╗ ███████╗███╗   ███╗ █████╗ ██████╗
██╔════╝██║   ██║██╔══██╗██╔════╝████╗ ████║██╔══██╗██╔══██╗
███████╗██║   ██║██████╔╝█████╗  ██╔████╔██║███████║██████╔╝
╚════██║██║   ██║██╔══██╗██╔══╝  ██║╚██╔╝██║██╔══██║██╔═══╝
███████║╚██████╔╝██║  ██║██║     ██║ ╚═╝ ██║██║  ██║██║
╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝
```

**Attack Surface Intelligence — Not Just Recon**

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20|%20WSL-f97316?style=for-the-badge&logo=linux&logoColor=white)](https://ubuntu.com)
[![BugBounty](https://img.shields.io/badge/Bug%20Bounty-Ready-ef4444?style=for-the-badge)](https://hackerone.com)
[![Telegram](https://img.shields.io/badge/Telegram-Notify-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org)

> **Most recon tools dump 10,000 URLs and leave you alone.**
> **SurfMap tells you exactly where to attack first.**

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

**SurfMap does.**

---

## What Makes It Different

| Feature | Other Tools | SurfMap |
|---------|-------------|---------|
| URL Collection | 2-3 sources | 10 sources |
| Subdomain Enum | 2-3 sources | 9 sources |
| False Positive Detection | Status code only | Baseline + Next.js + 30 patterns |
| API Schema Detection | ✗ | Swagger + GraphQL + WSDL + WADL |
| API Version Probe | ✗ | 50+ paths including mobile API |
| HTTP Method Fuzzing | ✗ | GET/POST/PUT/DELETE/PATCH/OPTIONS/TRACE |
| Parameter Classification | Just collects | Categorized by vuln type |
| Hidden Parameters | ✗ | arjun integration |
| Subdomain Takeover | ✗ | dnsx + 15 signature checks |
| Smart Deduplication | ✗ | Path-based dedup |
| Telegram Notify | ✗ | Summary + ZIP of all results |
| AI Ready Output | ✗ | REPORT.md → paste to Claude/GPT |

---

## Installation

```bash
# 1. Clone
git clone https://github.com/Rajib-Mahmud/surfmap
cd surfmap

# 2. Install Go tools (recommended for full power)
bash install.sh

# 3. Install Python tools
pip install -r requirements.txt

# 4. Setup Telegram (optional)
cp env.example .env
nano .env  # Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

---

## Usage

```bash
# Mode 1 — Single domain deep extraction (fast)
python3 recon.py target.com --mode 1

# Mode 2 — Full recon with all subdomains (complete)
python3 recon.py target.com --mode 2

# Custom output folder
python3 recon.py target.com --mode 2 -o my_output

# Skip specific modules
python3 recon.py target.com --mode 1 --no-probe --no-tech

# Tool installation guide
python3 recon.py --install
```

---

## Modes

### Mode 1 — Single Domain
```
target.com → URL/JS/API/Parameter deep extraction
Fast: 15-30 minutes
Use when: scope is main domain only
```

### Mode 2 — Full Recon
```
target.com → subdomain enum → DNS verify → all subdomains → full extraction
Complete: 30-90 minutes
Use when: subdomains are in scope
```

---

## What It Collects

### URL Sources — 10
| Source | Type |
|--------|------|
| Wayback Machine CDX | Historical (wildcard support) |
| CommonCrawl (3 indexes) | Historical |
| URLScan.io | Active |
| OTX AlienVault | Threat Intel |
| gau (all providers) | Aggregator |
| katana (depth 5, XHR) | Live Crawler |
| gospider | Live Crawler + Forms |
| hakrawler | Fast Crawler |
| paramspider | Parameter-focused |
| robots.txt + sitemap.xml | Parsed paths |

### Subdomain Sources — 9
`subfinder` · `amass` · `assetfinder` · `crt.sh` · `hackertarget` · `RapidDNS` · `BufferOver` · `CertSpotter` · `ThreatCrowd`

### False Positive Detection
```
Smart baseline — random fake path দিয়ে site-এর 404 fingerprint নেয়
Hash comparison — same hash = false positive
Size comparison — ±50 bytes match = false positive
30+ keyword patterns — Next.js, React, Laravel, Django, WordPress
8000 bytes read — hidden error messages detect করে
```

### API Schema Detection
```
Swagger / OpenAPI  →  Full endpoint list automatically extracted
GraphQL            →  Introspection query — all types/queries/mutations
WADL               →  Java REST API resources
WSDL               →  SOAP service operations
```

### API Version Probe — 50+ paths
```
/api/v1, /api/v2, /api/v3, /api/v4
/mobile/api, /android/api, /ios/api
/internal/api, /debug/api
/rest, /rest/v1, /rest/v2
/graphql, /gql, /ws
```

### HTTP Method Fuzzing
```
GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD, TRACE
XST vulnerability detection (TRACE method)
OPTIONS — allowed methods disclosure
Interesting status code differences flagged
```

### Parameter Intelligence
```
paramspider  →  Historical parameterized URLs
arjun        →  Hidden parameters (not visible in URLs)

Categorized by vulnerability type:
  SSRF/RFI      → ?url=, ?src=, ?path=, ?redirect=
  XSS           → ?q=, ?search=, ?input=, ?name=
  SQLi          → ?id=, ?category=, ?page=, ?search=
  LFI/Path      → ?file=, ?doc=, ?template=, ?view=
  Open Redirect → ?next=, ?return=, ?goto=, ?dest=
```

---

## Priority Output

```
🔴 CRITICAL — Check immediately
   ├── JS secrets (AWS key, API key, JWT, private key)
   ├── GraphQL introspection enabled
   ├── Subdomain takeover candidates
   ├── Sensitive config files (.env, .git, swagger)
   └── HTTP method vulnerabilities (XST)

🟡 MEDIUM — Check next
   ├── Hidden parameters (arjun)
   ├── SSRF/LFI parameter candidates
   ├── Missing security headers
   └── API version endpoints found

🟢 INFO — Full surface map
   ├── All URLs (deduplicated)
   ├── API endpoints
   ├── JS files + extracted endpoints
   └── Full parameter list by vuln type
```

---

## Output Files

```
recon_target_date/
├── REPORT.md                   ← AI-ready report
├── all_urls.txt                ← All URLs (smart deduped)
├── live_hosts.txt              ← Confirmed live hosts
├── endpoints_api.txt           ← API endpoints
├── js_files.txt                ← JavaScript files
├── parameters.txt              ← Parameterized URLs
├── sensitive_paths.txt         ← Admin/config/backup
├── subdomains.txt              ← All subdomains (Mode 2)
├── subdomains_resolved.txt     ← DNS verified (Mode 2)
├── parameters.json             ← Params + high-value flags
├── params_by_vulntype.json     ← SSRF/XSS/SQLi/LFI/Redirect
├── jsluice_endpoints.txt       ← JS-extracted endpoints (AST)
├── jsluice_secrets.json        ← Secrets found in JS
├── api_schema.json             ← Full API schema
├── api_schema_endpoints.txt    ← Schema-extracted endpoints
├── api_version_probe.txt       ← API version endpoints found
├── http_method_findings.json   ← Method fuzzing results
├── arjun_hidden_params.json    ← Hidden parameters
├── takeover_candidates.txt     ← Subdomain takeover (Mode 2)
├── active_probe.json           ← Sensitive path results
├── gospider_forms.txt          ← Form endpoints found
└── tech.json                   ← Technology detection
```

---

## Telegram Integration

```bash
cp env.example .env
nano .env
```

```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id
```

**What gets sent when recon completes:**
- Summary message with all stats and priority findings
- ZIP file containing all output files

Run recon on VPS at night, wake up to results on your phone.

---

## AI Workflow

```
Step 1: python3 recon.py target.com --mode 2
Step 2: Open REPORT.md
Step 3: Paste into Claude/ChatGPT
Step 4: AI analyzes the full attack surface
Step 5: You verify and hunt
```

---

## Tools Reference

```bash
bash install.sh  # installs everything
```

| Tool | Purpose | Install |
|------|---------|---------|
| subfinder | Subdomain enum | go install |
| httpx | Live host check | go install |
| katana | Web crawler | go install |
| gau | URL collection | go install |
| dnsx | DNS resolution | go install |
| gospider | Fast crawler | go install |
| hakrawler | Deep crawler | go install |
| jsluice | AST JS analysis | go install |
| waybackurls | Wayback URLs | go install |
| arjun | Hidden params | pip install |
| paramspider | Param crawler | pip install |

**Without tools:** Python fallback active (60% coverage)
**With all tools:** Full power (90%+ coverage)

---

## Options

```
--mode 1        Single domain extraction
--mode 2        Full recon with all subdomains
--no-js         Skip JS analysis
--no-probe      Skip active path probing
--no-tech       Skip tech detection
--no-gospider   Skip gospider crawler
--no-arjun      Skip hidden parameter finder
--no-params     Skip paramspider
--no-dnsx       Skip DNS resolution (Mode 2)
--no-schema     Skip API schema detection
--install       Show installation guide
-o OUTPUT       Custom output folder
```

---

## Legal

> This tool is for **authorized security testing only.**
> Only use on targets you have **explicit written permission** to test.
> Applicable to: Bug bounty programs, CTFs, your own infrastructure.
> The author is **not responsible** for any unauthorized use.

---

## Author

**rajib_mahmud**
Bug Bounty Hunter & Security Researcher
HackerOne · Intigriti · HackenProof · CVE Research

---

<div align="center">

*Recon ends. Hunting begins.*

**If this helped your hunting, give it a ⭐**

</div>
