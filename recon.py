#!/usr/bin/env python3
"""
RECON AUTOMATION v3 — by rajib_mahmud
New: gospider + arjun + paramspider + jsluice/LinkFinder + reconftw support
Mode 1: শুধু domain
Mode 2: domain + all subdomains
"""

import subprocess, sys, os, json, re, argparse, time, random
import urllib.request, urllib.parse, urllib.error
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── Load .env if exists ──────────────────────────────────────────────────────
_env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_file):
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ─── Colors ───────────────────────────────────────────────────────────────────
R="\033[91m"; G="\033[92m"; Y="\033[93m"
B="\033[94m"; C="\033[96m"; W="\033[0m"; BOLD="\033[1m"

# ─── Telegram Config ──────────────────────────────────────────────────────────
# .env file বা environment variable থেকে নেবে
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

def tg_send_message(text):
    """Telegram-এ text message পাঠাও"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        # Telegram 4096 char limit
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            payload = json.dumps({
                "chat_id": TELEGRAM_CHAT_ID,
                "text":    chunk,
            }).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=15)
            time.sleep(0.5)
        return True
    except Exception as e:
        warn(f"Telegram message error: {e}")
        return False

def tg_send_file(filepath, caption=""):
    """Telegram-এ file পাঠাও"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        # File size check — Telegram limit 50MB
        size = os.path.getsize(filepath)
        if size > 50 * 1024 * 1024:
            warn(f"File too large for Telegram: {filepath}")
            return False

        filename = os.path.basename(filepath)

        # multipart/form-data manually build করি
        boundary = "----ReconAutoBoundary"
        with open(filepath, "rb") as f:
            file_data = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
            f"{TELEGRAM_CHAT_ID}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="caption"\r\n\r\n'
            f"{caption}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        urllib.request.urlopen(req, timeout=30)
        return True
    except Exception as e:
        warn(f"Telegram file error: {e}")
        return False

def tg_notify_recon_done(domain, output_dir, stats):
    """Recon শেষে Telegram-এ summary + files পাঠাও"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    head("TELEGRAM NOTIFICATION")

    secrets_count  = stats.get("secrets", 0)
    takeover_count = stats.get("takeover", 0)
    critical_icon  = "🔴" if secrets_count or takeover_count else "🟢"

    # Plain text — no Markdown to avoid parse errors
    check_now = " ← CHECK NOW" if secrets_count else ""
    tak_check = " ← CHECK NOW" if takeover_count else ""

    msg = (
        f"{critical_icon} ReconAuto — Scan Complete\n\n"
        f"Target: {domain}\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Output: {output_dir}/\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Results Summary\n\n"
        f"Total URLs:    {stats.get('urls', 0)}\n"
        f"Subdomains:    {stats.get('subdomains', 0)}\n"
        f"Live Hosts:    {stats.get('live', 0)}\n"
        f"API Endpoints: {stats.get('api', 0)}\n"
        f"JS Files:      {stats.get('js', 0)}\n"
        f"Parameters:    {stats.get('params', 0)}\n"
        f"API Schemas:   {stats.get('schemas', 0)}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Priority Findings\n\n"
        f"🔴 JS Secrets:          {secrets_count}{check_now}\n"
        f"🔴 Takeover Candidates: {takeover_count}{tak_check}\n"
        f"🟡 Hidden Params:       {stats.get('hidden_params', 0)}\n"
        f"🟡 SSRF Candidates:     {stats.get('ssrf', 0)}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"by rajib_mahmud | SurfMap"
    )

    info("Telegram-এ summary পাঠাচ্ছি...")
    if tg_send_message(msg):
        info(f"{G}Summary sent{W}")
    else:
        warn("Summary send failed")

    # Key files পাঠাও
    files_to_send = [
        ("REPORT.md",                "📋 Full Report — AI-তে দাও"),
        ("all_urls.txt",             "🔗 All URLs"),
        ("endpoints_api.txt",        "📡 API Endpoints"),
        ("js_files.txt",             "📄 JS Files"),
        ("parameters.json",          "🔑 Parameters (high-value flagged)"),
        ("params_by_vulntype.json",  "⚠️ Params by Vuln Type"),
        ("api_schema_endpoints.txt", "🗂️ API Schema Endpoints"),
        ("jsluice_secrets.json",     "🔴 JS Secrets"),
        ("takeover_candidates.txt",  "🔴 Takeover Candidates"),
        ("arjun_hidden_params.json", "🟡 Hidden Parameters"),
    ]

    info("Files পাঠাচ্ছি...")
    sent = 0
    for filename, caption in files_to_send:
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 10:
            if tg_send_file(filepath, caption):
                info(f"  {G}✓{W} {filename}")
                sent += 1
                time.sleep(1)  # rate limit
            else:
                warn(f"  ✗ {filename}")

    info(f"Telegram: {sent} files sent")

def banner():
    print(f"""{C}{BOLD}
╦═╗╔═╗╔═╗╔═╗╔╗╔  ╔═╗╦ ╦╔╦╗╔═╗  ╦  ╦ ╦
╠╦╝║╣ ║  ║ ║║║║  ╠═╣║ ║ ║ ║ ║  ╚╗╔╝ ╚╦╝
╩╚═╚═╝╚═╝╚═╝╝╚╝  ╩ ╩╚═╝ ╩ ╚═╝   ╚╝   ╩
{W}{Y}  by rajib_mahmud | Web DNA Extractor v3{W}
{C}  gospider + arjun + paramspider + jsluice + reconftw{W}
""")

def info(msg):  print(f"{G}[+]{W} {msg}")
def warn(msg):  print(f"{Y}[!]{W} {msg}")
def hit(msg):   print(f"{R}[!!!]{W} {BOLD}{msg}{W}")
def head(msg):  print(f"\n{B}{BOLD}━━━ {msg} ━━━{W}")

def mode_banner(mode, domain):
    label = "SINGLE DOMAIN" if mode==1 else "DOMAIN + ALL SUBDOMAINS"
    print(f"\n{Y}{BOLD}  MODE {mode} — {label}: {domain}{W}\n")

# ─── Helpers ──────────────────────────────────────────────────────────────────
def check_tool(t):
    return subprocess.run(["which",t], capture_output=True).returncode == 0

def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except: return ""

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
]
def rand_ua(): return random.choice(UA_LIST)

def http_get(url, timeout=15, headers=None):
    try:
        h = {"User-Agent": rand_ua()}
        if headers: h.update(headers)
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore"), dict(r.headers), r.status
    except: return "", {}, 0

# ═══════════════════════════════════════════════════════════════════════════════
# UPGRADE 1 — MORE SOURCES
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_wayback(domain, wildcard=False, limit=50000):
    prefix = f"*.{domain}/*" if wildcard else f"{domain}/*"
    url = f"http://web.archive.org/cdx/search/cdx?url={prefix}&output=text&fl=original&collapse=urlkey&limit={limit}"
    content, _, _ = http_get(url, timeout=60)
    return {l.strip() for l in content.splitlines() if l.strip()}

def fetch_commoncrawl(domain, wildcard=False):
    urls = set()
    prefix = f"*.{domain}/*" if wildcard else f"{domain}/*"
    # Try last 3 indexes
    indexes = ["CC-MAIN-2024-18", "CC-MAIN-2024-10", "CC-MAIN-2023-50"]
    for idx in indexes:
        try:
            api = f"http://index.commoncrawl.org/{idx}-index?url={prefix}&output=json&limit=10000"
            content, _, _ = http_get(api, timeout=30)
            for line in content.splitlines():
                try:
                    d = json.loads(line)
                    u = d.get("url","")
                    if domain in u: urls.add(u)
                except: pass
        except: pass
    return urls

def fetch_urlscan(domain):
    urls = set()
    try:
        api = f"https://urlscan.io/api/v1/search/?q=domain:{domain}&size=1000"
        content, _, _ = http_get(api, timeout=20)
        data = json.loads(content)
        for r in data.get("results", []):
            u = r.get("page", {}).get("url","")
            if u: urls.add(u)
    except: pass
    return urls

def fetch_otx(domain):
    urls = set()
    try:
        api = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/url_list?limit=500"
        content, _, _ = http_get(api, timeout=20)
        data = json.loads(content)
        for entry in data.get("url_list", []):
            u = entry.get("url","")
            if u: urls.add(u)
    except: pass
    return urls

def fetch_subdomains_rapiddns(domain):
    subs = set()
    try:
        content, _, _ = http_get(f"https://rapiddns.io/subdomain/{domain}?full=1", timeout=20)
        matches = re.findall(rf'[\w\-]+\.{re.escape(domain)}', content)
        subs.update(matches)
    except: pass
    return subs

def fetch_subdomains_bufferover(domain):
    subs = set()
    try:
        content, _, _ = http_get(f"https://dns.bufferover.run/dns?q=.{domain}", timeout=15)
        data = json.loads(content)
        for entry in data.get("FDNS_A", []) + data.get("RDNS", []):
            parts = entry.split(",")
            for p in parts:
                p = p.strip()
                if domain in p: subs.add(p.lstrip("*."))
    except: pass
    return subs

def fetch_subdomains_threatcrowd(domain):
    subs = set()
    try:
        content, _, _ = http_get(f"https://www.threatcrowd.org/searchApi/v2/domain/report/?domain={domain}", timeout=15)
        data = json.loads(content)
        for s in data.get("subdomains", []):
            if domain in s: subs.add(s)
    except: pass
    return subs

def fetch_subdomains_certspotter(domain):
    subs = set()
    try:
        content, _, _ = http_get(f"https://api.certspotter.com/v1/issuances?domain={domain}&include_subdomains=true&expand=dns_names", timeout=20)
        data = json.loads(content)
        for entry in data:
            for name in entry.get("dns_names", []):
                name = name.lstrip("*.")
                if domain in name: subs.add(name)
    except: pass
    return subs

# ═══════════════════════════════════════════════════════════════════════════════
# UPGRADE 2 — BETTER JS ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

# Comprehensive secret patterns
SECRET_PATTERNS = {
    "AWS Access Key":       r'AKIA[0-9A-Z]{16}',
    "AWS Secret Key":       r'(?i)aws.{0,20}secret.{0,20}[\'"]?([0-9a-zA-Z/+]{40})',
    "Google API Key":       r'AIza[0-9A-Za-z\-_]{35}',
    "Google OAuth":         r'[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com',
    "Firebase":             r'AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}',
    "Stripe Live Key":      r'sk_live_[0-9a-zA-Z]{24}',
    "Stripe Test Key":      r'sk_test_[0-9a-zA-Z]{24}',
    "Stripe Publishable":   r'pk_live_[0-9a-zA-Z]{24}',
    "Twilio SID":           r'AC[a-z0-9]{32}',
    "Twilio Token":         r'SK[a-z0-9]{32}',
    "SendGrid Key":         r'SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}',
    "Mailgun Key":          r'key-[0-9a-zA-Z]{32}',
    "GitHub Token":         r'gh[pousr]_[A-Za-z0-9_]{36}',
    "GitLab Token":         r'glpat-[A-Za-z0-9\-_]{20}',
    "Slack Token":          r'xox[baprs]-[0-9A-Za-z\-]{10,48}',
    "Slack Webhook":        r'https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+',
    "JWT Token":            r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
    "Private Key":          r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY(?:\s|-).*?-----',
    "Basic Auth in URL":    r'https?://[^:]+:[^@]+@[^\s/]+',
    "Bearer Token":         r'[Bb]earer\s+[A-Za-z0-9\-._~+/]{20,}=*',
    "Password in Code":     r'(?i)(?:password|passwd|pwd)\s*[:=]\s*[\'"][^\'"]{6,}[\'"]',
    "Secret in Code":       r'(?i)(?:secret|api_key|apikey|client_secret)\s*[:=]\s*[\'"][^\'"]{8,}[\'"]',
    "Hardcoded Token":      r'(?i)(?:token|access_token|auth_token)\s*[:=]\s*[\'"][^\'"]{16,}[\'"]',
    "MongoDB URI":          r'mongodb(?:\+srv)?://[^\s\'"<>]+',
    "MySQL URI":            r'mysql://[^\s\'"<>]+',
    "PostgreSQL URI":       r'postgres(?:ql)?://[^\s\'"<>]+',
    "Redis URI":            r'redis://[^\s\'"<>]+',
    "FTP Credentials":      r'ftp://[^:]+:[^@]+@[^\s]+',
    "Internal IP":          r'(?:10\.|172\.(?:1[6-9]|2\d|3[01])\.|192\.168\.)\d{1,3}\.\d{1,3}',
    "Debug/Test Flag":      r'(?i)(?:debug|test_mode|dev_mode)\s*[:=]\s*(?:true|1|yes)',
}

# Endpoint patterns — covers minified JS
ENDPOINT_PATTERNS = [
    # fetch/axios/http calls
    r'(?:fetch|axios\.(?:get|post|put|patch|delete)|http\.(?:get|post))\s*\(\s*[\'"`]([/][^\'"` ]{2,})[\'"`]',
    # url: '/path' or url: "/path"
    r'url\s*:\s*[\'"`]([/][^\'"` ]{2,})[\'"`]',
    # endpoint: or path: or route:
    r'(?:endpoint|path|route|api_url|baseURL|base_url)\s*[:=]\s*[\'"`]([/][^\'"` ]{2,})[\'"`]',
    # string concatenation — '/api/' + something
    r'[\'"`]([/](?:api|v\d+|graphql|rest|auth|user|admin)[^\'"` ]{0,80})[\'"`]',
    # href or action
    r'(?:href|action)\s*[:=]\s*[\'"`]([/][^\'"` ]{2,})[\'"`]',
    # template literals — `/api/${...}`
    r'`([/][^`]{2,})`',
    # XMLHttpRequest open
    r'\.open\s*\(\s*[\'"][A-Z]+[\'"]\s*,\s*[\'"`]([/][^\'"` ]{2,})[\'"`]',
    # router paths
    r'(?:path|component)\s*:\s*[\'"`]([/][^\'"` ]{2,})[\'"`]',
]

def deobfuscate_js(content):
    """Simple deobfuscation — decode common patterns"""
    # Decode hex strings \x41\x42 → AB
    content = re.sub(r'\\x([0-9a-fA-F]{2})',
                     lambda m: chr(int(m.group(1), 16)), content)
    # Decode unicode \u0041 → A
    content = re.sub(r'\\u([0-9a-fA-F]{4})',
                     lambda m: chr(int(m.group(1), 16)), content)
    # Decode base64 strings (common in obfuscated JS)
    def try_b64(m):
        try:
            import base64
            decoded = base64.b64decode(m.group(1)).decode("utf-8", errors="ignore")
            if decoded.isprintable(): return decoded
        except: pass
        return m.group(0)
    content = re.sub(r'atob\([\'"]([A-Za-z0-9+/=]{20,})[\'"]\)', try_b64, content)
    return content

def analyze_js_file(js_url):
    result = {"url": js_url, "endpoints": [], "secrets": [], "interesting": []}
    content, headers, status = http_get(js_url, timeout=20)
    if not content: return result

    # Deobfuscate first
    content = deobfuscate_js(content)

    # Extract endpoints — all patterns
    endpoints = set()
    for pattern in ENDPOINT_PATTERNS:
        for m in re.finditer(pattern, content, re.I):
            ep = m.group(1).strip()
            # Filter noise
            if (len(ep) > 2 and
                not ep.endswith((".js",".css",".png",".jpg",".svg",".woff",".ico")) and
                not re.match(r'^/\d+$', ep)):
                endpoints.add(ep)
    result["endpoints"] = sorted(endpoints)

    # Extract secrets
    for name, pattern in SECRET_PATTERNS.items():
        matches = re.findall(pattern, content)
        if matches:
            result["secrets"].append({
                "type": name,
                "matches": [str(m)[:100] for m in matches[:3]]
            })

    # Interesting findings
    # Internal domains/IPs
    internal = re.findall(r'(?:staging|dev|internal|test|admin|localhost|127\.0\.0\.1)[^\s\'"<>]{0,50}', content, re.I)
    if internal: result["interesting"].extend([f"Internal ref: {x[:80]}" for x in internal[:5]])

    # Version numbers
    versions = re.findall(r'(?:version|ver)\s*[:=]\s*[\'"]([0-9.]+)[\'"]', content, re.I)
    if versions: result["interesting"].append(f"Versions: {', '.join(versions[:5])}")

    return result

# ═══════════════════════════════════════════════════════════════════════════════
# UPGRADE 3 — ACTIVE PROBING
# ═══════════════════════════════════════════════════════════════════════════════

# Sensitive paths to actively probe
PROBE_PATHS = [
    # Config/secrets
    "/.env", "/.env.local", "/.env.production", "/.env.backup",
    "/config.json", "/config.yml", "/config.yaml", "/configuration.json",
    "/settings.json", "/secrets.json", "/credentials.json",
    # Backup files
    "/backup.zip", "/backup.tar.gz", "/db.sql", "/database.sql",
    "/dump.sql", "/backup.sql", "/.git/config", "/.git/HEAD",
    "/.svn/entries", "/.DS_Store",
    # Debug/info
    "/debug", "/debug.php", "/phpinfo.php", "/info.php",
    "/test.php", "/server-status", "/server-info",
    "/_profiler", "/__debug__", "/telescope", "/horizon",
    # Admin panels
    "/admin", "/admin/", "/administrator", "/wp-admin",
    "/admin/login", "/panel", "/dashboard", "/manage",
    "/cms", "/backend", "/controlpanel", "/cpanel",
    # API
    "/api", "/api/v1", "/api/v2", "/api/v3", "/graphql",
    "/api/swagger", "/swagger", "/swagger-ui.html",
    "/api-docs", "/openapi.json", "/openapi.yaml",
    "/v1/api-docs", "/api/schema", "/api/spec",
    # Health/monitoring
    "/health", "/healthz", "/health/check", "/status",
    "/metrics", "/actuator", "/actuator/health", "/actuator/env",
    "/actuator/mappings", "/actuator/beans",
    # Auth
    "/login", "/signin", "/signup", "/register",
    "/forgot-password", "/reset-password", "/oauth/token",
    "/auth/login", "/api/auth", "/api/login",
    # Dev leftovers
    "/robots.txt", "/sitemap.xml", "/crossdomain.xml",
    "/security.txt", "/.well-known/security.txt",
    "/CHANGELOG", "/CHANGELOG.md", "/README.md", "/README",
    "/package.json", "/composer.json", "/yarn.lock",
    "/Gemfile", "/requirements.txt", "/web.config",
]

def active_probe(base_url, output_dir, threads=20):
    head("ACTIVE PROBING")
    base_url = base_url.rstrip("/")
    findings = []

    def probe_one(path):
        url = base_url + path
        try:
            req = urllib.request.Request(url, headers={"User-Agent": rand_ua()})
            with urllib.request.urlopen(req, timeout=8) as r:
                status = r.status
                content = r.read(2000).decode("utf-8", errors="ignore")
                headers = dict(r.headers)
                size = int(headers.get("Content-Length", len(content)))

                # Skip common false positives
                if status in [404, 410]: return None
                if status == 200 and size < 10: return None

                # Soft 404 / false positive detection
                FALSE_POSITIVE_SIGNS = [
                    "page not found",
                    "404",
                    "not found",
                    "oops",
                    "doesn't exist",
                    "does not exist",
                    "no longer available",
                    "this page could not be found",
                    "the page you requested",
                    "nothing here",
                    "went wrong",
                    "error 404",
                    "http 404",
                    "page doesn't exist",
                    "resource not found",
                ]
                content_lower = content.lower()
                if status == 200 and any(sign in content_lower for sign in FALSE_POSITIVE_SIGNS):
                    return None

                result = {
                    "url": url, "status": status,
                    "size": size, "content_type": headers.get("Content-Type",""),
                    "snippet": content[:200]
                }

                # Flag interesting content
                flags = []
                if re.search(r'(?i)(password|secret|key|token|api_key)', content): flags.append("SENSITIVE_CONTENT")
                if re.search(r'(?i)(error|exception|stack.?trace|debug)', content): flags.append("ERROR_INFO")
                if re.search(r'(?i)(admin|dashboard|panel)', content) and status==200: flags.append("ADMIN_PANEL")
                if path in ["/.git/config","/.git/HEAD"]: flags.append("GIT_EXPOSED")
                if path in ["/.env","/config.json","/secrets.json"]: flags.append("CONFIG_EXPOSED")
                if "/actuator" in path: flags.append("SPRING_ACTUATOR")
                if path in ["/swagger-ui.html","/api-docs","/openapi.json","/graphql"]: flags.append("API_DOCS")
                result["flags"] = flags
                return result
        except urllib.error.HTTPError as e:
            if e.code not in [404,410,403]:
                return {"url": url, "status": e.code, "size":0, "flags":[], "snippet":"", "content_type":""}
        except: pass
        return None

    info(f"{len(PROBE_PATHS)} paths probe করছি → {base_url}")
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = {ex.submit(probe_one, path): path for path in PROBE_PATHS}
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                findings.append(r)
                flags_str = f" {R}[{', '.join(r['flags'])}]{W}" if r['flags'] else ""
                color = G if r['status']==200 else Y
                info(f"  {color}{r['status']}{W} {r['url']}{flags_str}")

    # Save
    probe_file = os.path.join(output_dir, "active_probe.json")
    with open(probe_file, "w") as f:
        json.dump(findings, f, indent=2)

    critical = [x for x in findings if x['flags']]
    info(f"Probe results: {len(findings)} found | {R}{len(critical)} flagged{W}")
    return findings

def probe_params(parameterized_urls, output_dir, sample=50):
    """Parameter-level active probing — IDOR, open redirect, etc."""
    head("PARAMETER PROBING")

    payloads = {
        "IDOR":          ["0", "1", "2", "99999", "-1", "null", "undefined"],
        "Open Redirect": ["https://evil.com", "//evil.com", "/\\evil.com"],
        "Path Traversal":["../etc/passwd", "..%2Fetc%2Fpasswd", "....//....//etc/passwd"],
        "SSRF":          ["http://169.254.169.254/", "http://localhost/", "http://127.0.0.1/"],
        "SQLi Basic":    ["'", "\"", "1 OR 1=1", "1'--"],
        "XSS Basic":     ["<script>alert(1)</script>", "\"><img src=x onerror=alert(1)>"],
    }

    interesting_params = {
        "id","user_id","uid","account","file","path","url",
        "redirect","return","next","src","dest","target","img",
        "template","page","view","cmd","query","search","host"
    }

    findings = []
    tested = 0

    for url in parameterized_urls[:sample]:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        for param_name in params:
            if param_name.lower() not in interesting_params: continue

            for vuln_type, payloads_list in payloads.items():
                # Only test relevant payload types per param
                if vuln_type in ["IDOR"] and param_name.lower() not in ["id","user_id","uid","account"]: continue
                if vuln_type in ["Open Redirect","SSRF"] and param_name.lower() not in ["url","redirect","return","next","src","dest","target"]: continue
                if vuln_type in ["Path Traversal"] and param_name.lower() not in ["file","path","template","page","view"]: continue

                for payload in payloads_list[:2]:
                    new_params = {p: v[0] for p,v in params.items()}
                    new_params[param_name] = payload
                    test_url = urllib.parse.urlunparse(
                        parsed._replace(query=urllib.parse.urlencode(new_params))
                    )
                    content, headers, status = http_get(test_url, timeout=8)
                    if not content: continue

                    finding = None
                    # SSRF — metadata response
                    if vuln_type=="SSRF" and ("ami-id" in content or "instance-id" in content):
                        finding = {"type":"SSRF","severity":"CRITICAL","url":test_url,"evidence":content[:100]}
                    # Open Redirect
                    if vuln_type=="Open Redirect" and status in [301,302,303,307,308]:
                        loc = headers.get("Location","")
                        if "evil.com" in loc:
                            finding = {"type":"Open Redirect","severity":"MEDIUM","url":test_url,"evidence":f"Location: {loc}"}
                    # Path traversal
                    if vuln_type=="Path Traversal" and "root:" in content:
                        finding = {"type":"Path Traversal","severity":"HIGH","url":test_url,"evidence":content[:100]}
                    # SQLi — error-based
                    if vuln_type=="SQLi Basic" and re.search(r'(?i)(sql|syntax|mysql|postgres|oracle|sqlite)', content):
                        finding = {"type":"SQLi Error","severity":"HIGH","url":test_url,"evidence":content[:100]}

                    if finding:
                        hit(f"{finding['type']} [{finding['severity']}] → {test_url}")
                        findings.append(finding)

                tested += 1
                time.sleep(0.1)  # rate limit

    param_probe_file = os.path.join(output_dir, "param_probe.json")
    with open(param_probe_file, "w") as f:
        json.dump(findings, f, indent=2)

    info(f"Parameter probe: {tested} tests | {R}{len(findings)} potential findings{W}")
    return findings

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED — URL Categorization, Parameter Extraction, Tech, Report
# ═══════════════════════════════════════════════════════════════════════════════

def categorize_urls(all_urls, output_dir):
    head("URL CATEGORIZATION")
    cats = {
        "endpoints_api":   [],
        "js_files":        [],
        "parameters":      [],
        "sensitive_paths": [],
        "interesting":     [],
    }
    api_p  = re.compile(r'/(api|v\d+|graphql|rest|service|rpc|ajax|fetch|gql|endpoint)/', re.I)
    js_p   = re.compile(r'\.js(\?.*)?$', re.I)
    par_p  = re.compile(r'\?.*=')
    sen_p  = re.compile(
        r'/(admin|dashboard|panel|login|logout|signin|signup|register|forgot|reset|'
        r'password|upload|export|download|backup|config|setting|account|profile|user|'
        r'debug|test|dev|staging|internal|private|secret|token|key|auth|oauth|'
        r'webhook|callback|redirect|payment|billing|invoice|order|cart|checkout|'
        r'report|log|audit|monitor|health|status|metrics|graphql|swagger|actuator)(/|$|\?)', re.I)
    int_p  = re.compile(r'\.(php|asp|aspx|jsp|json|xml|yaml|yml|env|bak|old|backup|sql|log|zip|tar|gz)(\?.*)?$', re.I)

    for url in all_urls:
        if js_p.search(url):   cats["js_files"].append(url)
        if par_p.search(url):  cats["parameters"].append(url)
        if api_p.search(url):  cats["endpoints_api"].append(url)
        if sen_p.search(url):  cats["sensitive_paths"].append(url)
        if int_p.search(url):  cats["interesting"].append(url)

    for cat, urls in cats.items():
        with open(os.path.join(output_dir, f"{cat}.txt"), "w") as f:
            f.write("\n".join(sorted(set(urls))))
        info(f"{cat}: {BOLD}{len(set(urls))}{W}")
    return cats

def extract_parameters(all_urls, output_dir):
    head("PARAMETER EXTRACTION")
    param_map = {}
    for url in all_urls:
        parsed = urllib.parse.urlparse(url)
        for p in urllib.parse.parse_qs(parsed.query):
            if p not in param_map: param_map[p] = []
            param_map[p].append(url)

    sorted_params = sorted(param_map.items(), key=lambda x: len(x[1]), reverse=True)
    high_value = [
        "id","user","uid","userid","user_id","account","file","path","url",
        "redirect","return","next","target","dest","src","source","img","image",
        "page","view","template","theme","cmd","exec","command","query","search",
        "q","s","input","token","key","api_key","secret","password","pass",
        "email","username","name","type","action","method","format","callback",
        "jsonp","lang","debug","admin","role","permission","auth","session",
        "order_id","product_id","ref","referrer","host","domain",
    ]
    flagged = [
        {"param": p, "count": len(u), "sample": u[0]}
        for p, u in sorted_params
        if p.lower() in [x.lower() for x in high_value]
    ]
    with open(os.path.join(output_dir, "parameters.json"), "w") as f:
        json.dump({"all": [{"param":p,"count":len(u)} for p,u in sorted_params], "flagged": flagged}, f, indent=2)

    info(f"Unique params: {BOLD}{len(param_map)}{W} | High-value: {BOLD}{len(flagged)}{W}")
    if flagged:
        print(f"\n  {Y}High-value params:{W}")
        for p in flagged[:15]:
            print(f"  {G}?{p['param']}={W} ({p['count']}x) → {p['sample'][:80]}")
    return sorted_params, flagged

def detect_tech(targets, output_dir):
    head("TECHNOLOGY DETECTION")
    results = []
    def check(url):
        r = {"url": url, "tech": [], "missing_headers": [], "interesting_headers": []}
        content, headers, status = http_get(url, timeout=10)
        if not status: return r
        for h in ["Server","X-Powered-By","X-Generator","X-Framework","X-Runtime","X-AspNet-Version"]:
            if h in headers: r["tech"].append(f"{h}: {headers[h]}")
        missing = [h for h in ["Strict-Transport-Security","X-Frame-Options",
                   "X-Content-Type-Options","Content-Security-Policy"] if h not in headers]
        if missing: r["missing_headers"] = missing
        for h in ["X-Debug","X-Environment","X-Version","X-Request-Id"]:
            if h in headers: r["interesting_headers"].append(f"{h}: {headers[h]}")
        # Detect from page content
        if "wp-content" in content: r["tech"].append("CMS: WordPress")
        if "Drupal" in content: r["tech"].append("CMS: Drupal")
        if "Laravel" in content: r["tech"].append("Framework: Laravel")
        if "Django" in content or "csrfmiddlewaretoken" in content: r["tech"].append("Framework: Django")
        if "react" in content.lower(): r["tech"].append("Frontend: React")
        if "vue" in content.lower(): r["tech"].append("Frontend: Vue")
        return r

    with ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(check, targets[:20]):
            if r["tech"] or r["interesting_headers"]:
                results.append(r)
                info(f"  {G}{r['url'][:60]}{W}")
                for t in r["tech"]: print(f"    {C}→ {t}{W}")
                for t in r["interesting_headers"]: print(f"    {Y}⚑ {t}{W}")
                if r["missing_headers"]: print(f"    {R}✗ Missing: {', '.join(r['missing_headers'])}{W}")

    with open(os.path.join(output_dir, "tech.json"), "w") as f:
        json.dump(results, f, indent=2)
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# NEW TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

# ─── dnsx ────────────────────────────────────────────────────────────────────
def run_dnsx(subdomains, output_dir):
    """DNS resolution + validation — false positive বাদ দেয়"""
    head("DNSX — DNS RESOLUTION & VALIDATION")

    sub_file = os.path.join(output_dir, "subdomains.txt")
    resolved_file = os.path.join(output_dir, "subdomains_resolved.txt")
    takeover_file = os.path.join(output_dir, "takeover_candidates.txt")

    resolved  = []
    wildcards = []
    takeover  = []

    # Subdomain takeover signatures
    TAKEOVER_SIGNATURES = {
        "GitHub Pages":      "There isn't a GitHub Pages site here",
        "Heroku":            "No such app",
        "Shopify":           "Sorry, this shop is currently unavailable",
        "Fastly":            "Fastly error: unknown domain",
        "Ghost":             "The thing you were looking for is no longer here",
        "Pantheon":          "The gods are wise, but do not know of the site",
        "Tumblr":            "Whatever you were looking for doesn't live here",
        "WordPress":         "Do you want to register",
        "Azure":             "404 Web Site not found",
        "Bitbucket":         "Repository not found",
        "Unbounce":          "The requested URL was not found on this server",
        "Surge.sh":          "project not found",
        "Readme.io":         "Project doesnt exist",
        "S3 Bucket":         "NoSuchBucket",
        "Zendesk":           "Help Center Closed",
        "Cargo":             "If you're moving your domain away from Cargo",
    }

    if check_tool("dnsx"):
        info("dnsx দিয়ে DNS resolve করছি...")
        # Resolve + get A records
        out = run(
            f"dnsx -l {sub_file} -silent -a -resp -json 2>/dev/null",
            timeout=300
        )
        for line in out.splitlines():
            try:
                d = json.loads(line)
                host = d.get("host","")
                ips  = d.get("a", [])
                if host and ips:
                    resolved.append({"host": host, "ips": ips})

                # Wildcard detection
                if d.get("wildcard"):
                    wildcards.append(host)
            except: pass

        # CNAME-based takeover check
        cname_out = run(
            f"dnsx -l {sub_file} -silent -cname -resp -json 2>/dev/null",
            timeout=300
        )
        suspicious_cnames = [
            "github.io","herokussl.com","herokudns.com","unbouncepages.com",
            "pantheonsite.io","domains.tumblr.com","wpengine.com","myshopify.com",
            "azurewebsites.net","cloudapp.net","trafficmanager.net",
            "s3.amazonaws.com","s3-website","bitbucket.io","surge.sh",
            "readme.io","zendesk.com","cargo.site",
        ]
        for line in cname_out.splitlines():
            try:
                d = json.loads(line)
                cname = " ".join(d.get("cname", []))
                host  = d.get("host","")
                for sus in suspicious_cnames:
                    if sus in cname:
                        takeover.append({"host": host, "cname": cname, "service": sus})
                        hit(f"TAKEOVER CANDIDATE: {host} → {cname}")
            except: pass

    else:
        warn("dnsx নেই — Python fallback দিয়ে resolve করছি...")
        warn("Install: go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest")
        import socket

        def resolve_one(sub):
            try:
                ips = socket.gethostbyname_ex(sub)[2]
                return {"host": sub, "ips": ips}
            except: return None

        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(resolve_one, s): s for s in subdomains}
            for fut in as_completed(futures):
                r = fut.result()
                if r: resolved.append(r)

    # HTTP-based takeover check on resolved hosts
    if resolved:
        info(f"Takeover check করছি ({len(resolved)} resolved hosts)...")
        def check_takeover(entry):
            host = entry["host"]
            for scheme in ["https", "http"]:
                content, _, status = http_get(f"{scheme}://{host}", timeout=8)
                if content:
                    for service, sig in TAKEOVER_SIGNATURES.items():
                        if sig.lower() in content.lower():
                            return {"host": host, "service": service, "status": status}
            return None

        with ThreadPoolExecutor(max_workers=20) as ex:
            for r in ex.map(check_takeover, resolved[:100]):
                if r:
                    takeover.append(r)
                    hit(f"SUBDOMAIN TAKEOVER: {r['host']} [{r['service']}]")

    # Save results
    with open(resolved_file, "w") as f:
        for r in resolved:
            f.write(f"{r['host']} → {', '.join(r['ips'])}\n")

    with open(takeover_file, "w") as f:
        json.dump(takeover, f, indent=2)

    if wildcards:
        with open(os.path.join(output_dir, "wildcards.txt"), "w") as f:
            f.write("\n".join(wildcards))
        warn(f"Wildcard DNS detected: {len(wildcards)} entries — false positives possible")

    info(f"Resolved: {BOLD}{len(resolved)}{W} | Wildcards: {len(wildcards)} | Takeover candidates: {R}{len(takeover)}{W}")

    # Return only verified resolved hosts
    return [r["host"] for r in resolved], takeover

# ─── API Schema Detection ─────────────────────────────────────────────────────
def detect_api_schema(live_hosts, output_dir):
    """Swagger, GraphQL, WADL, WSDL, OpenAPI — পুরো API structure বের করে"""
    head("API SCHEMA DETECTION")

    findings = {"swagger":[], "graphql":[], "openapi":[], "wadl":[], "wsdl":[], "json_api":[]}

    SCHEMA_PATHS = {
        "swagger": [
            "/swagger.json","/swagger.yaml","/swagger.yml",
            "/swagger-ui.html","/swagger-ui/index.html",
            "/api/swagger.json","/api/swagger.yaml",
            "/v1/swagger.json","/v2/swagger.json","/v3/swagger.json",
            "/api-docs","/api-docs.json","/api/api-docs",
            "/api/v1/api-docs","/api/v2/api-docs","/api/v3/api-docs",
            "/docs","/api/docs","/documentation",
        ],
        "openapi": [
            "/openapi.json","/openapi.yaml","/openapi.yml",
            "/api/openapi.json","/api/openapi.yaml",
            "/v1/openapi.json","/v2/openapi.json",
            "/.well-known/openapi",
        ],
        "graphql": [
            "/graphql","/graphiql","/graphql/console",
            "/api/graphql","/v1/graphql","/v2/graphql",
            "/query","/api/query","/gql",
            "/graphql/playground","/playground",
        ],
        "wadl": [
            "/application.wadl","/api/application.wadl","/?wadl","/api/?wadl",
        ],
        "wsdl": [
            "/service.wsdl","/api/service.wsdl","/?wsdl","/api/?wsdl",
            "/ws?wsdl","/services?wsdl","/soap?wsdl",
        ],
        "json_api": [
            "/api","/api/v1","/api/v2","/api/v3",
            "/rest/api","/api/schema","/api/spec","/api/spec.json",
        ],
    }

    all_found_urls = set()
    graphql_introspections = []

    def check_one(base, schema_type, path):
        url = base.rstrip("/") + path
        content, headers, status = http_get(url, timeout=10)
        if not content or status in [404,403,401,410]: return None
        ct = headers.get("Content-Type","").lower()
        result = {"url":url,"status":status,"type":schema_type,"endpoints":[]}

        if schema_type in ["swagger","openapi"]:
            if not any(k in content for k in ["swagger","openapi","paths","info"]): return None
            try:
                if "json" in ct or content.strip().startswith("{"):
                    spec = json.loads(content)
                    result["endpoints"] = list(spec.get("paths",{}).keys())[:100]
                    result["info"]    = spec.get("info",{})
                    result["servers"] = spec.get("servers",[])
            except: pass

        elif schema_type == "graphql":
            if status==200 and ("graphql" in ct or "json" in ct or len(content)>50):
                result["endpoints"] = [path]

        elif schema_type == "wadl":
            if "wadl" not in content.lower() and "resource" not in content.lower(): return None
            result["endpoints"] = re.findall(r'path=[\'"]([^\'"]+)[\'"]', content)[:50]

        elif schema_type == "wsdl":
            if "wsdl" not in content.lower() and "definitions" not in content.lower(): return None
            result["endpoints"] = re.findall(r'<(?:wsdl:)?operation\s+name=[\'"]([^\'"]+)[\'"]', content)[:50]

        elif schema_type == "json_api":
            if status==200 and ("json" in ct or content.strip().startswith("{")):
                try:
                    data = json.loads(content)
                    if isinstance(data,dict) and any(k in data for k in ["data","links","meta","routes","endpoints"]):
                        result["endpoints"] = list(data.keys())[:20]
                    else: return None
                except: return None

        return result

    def graphql_introspect(base):
        results = []
        for path in SCHEMA_PATHS["graphql"]:
            url = base.rstrip("/") + path
            try:
                data = json.dumps({"query":"{ __schema { types { name } } }"}).encode()
                req = urllib.request.Request(
                    url, data=data,
                    headers={"Content-Type":"application/json","User-Agent":rand_ua()},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as r:
                    content = r.read().decode("utf-8",errors="ignore")
                    if "__schema" in content or "types" in content:
                        try:
                            schema_data = json.loads(content)
                            types = schema_data.get("data",{}).get("__schema",{}).get("types",[])
                            type_names = [t["name"] for t in types if not t["name"].startswith("__")]
                            results.append({"url":url,"types":type_names[:50],"status":r.status})
                            hit(f"GraphQL Introspection ENABLED: {url}")
                            hit(f"Types: {', '.join(type_names[:8])}")
                        except: pass
            except: pass
        return results

    info(f"{len(live_hosts[:20])} host-এ API schema check করছি...")

    for host in live_hosts[:20]:
        for schema_type, paths in SCHEMA_PATHS.items():
            with ThreadPoolExecutor(max_workers=10) as ex:
                futures = {ex.submit(check_one, host, schema_type, p): p for p in paths}
                for fut in as_completed(futures):
                    r = fut.result()
                    if r:
                        findings[schema_type].append(r)
                        all_found_urls.add(r["url"])
                        ep_count = len(r.get("endpoints",[]))
                        info(f"  {G}[{schema_type.upper()}]{W} {r['url']} [{r['status']}]"
                             + (f" → {ep_count} endpoints" if ep_count else ""))
                        for ep in r.get("endpoints",[])[:10]:
                            print(f"    {C}→ {ep}{W}")

        gi = graphql_introspect(host)
        graphql_introspections.extend(gi)

    # Save
    with open(os.path.join(output_dir,"api_schema.json"),"w") as f:
        json.dump({"findings":findings,"graphql_introspections":graphql_introspections},f,indent=2)

    # All endpoints as URL list
    all_endpoints = set(all_found_urls)
    for results in findings.values():
        for r in results:
            base = "/".join(r["url"].split("/")[:3])
            for ep in r.get("endpoints",[]):
                if ep.startswith("/"): all_endpoints.add(base+ep)

    with open(os.path.join(output_dir,"api_schema_endpoints.txt"),"w") as f:
        f.write("\n".join(sorted(all_endpoints)))

    total    = sum(len(v) for v in findings.values())
    total_ep = sum(len(r.get("endpoints",[])) for v in findings.values() for r in v)
    info(f"API Schema → {total} schemas | {total_ep} endpoints extracted")
    if graphql_introspections:
        hit(f"GraphQL Introspection OPEN: {len(graphql_introspections)} endpoints!")

    return findings, all_endpoints


def run_gospider(target_url, output_dir, depth=3):
    """Fast web crawler — JS parsing + form extraction সহ"""
    head("GOSPIDER — FAST CRAWLER")
    urls = set()

    if not check_tool("gospider"):
        warn("gospider নেই — install: go install github.com/jaeles-project/gospider@latest")
        return urls

    info(f"gospider চালাচ্ছি → {target_url}")
    out = run(
        f"gospider -s {target_url} -d {depth} -c 10 --js --sitemap --robots "
        f"--blacklist '.(png|jpg|gif|css|woff|ttf|svg)' -q 2>/dev/null",
        timeout=300
    )

    ep = re.compile(r'\[url\]\s*-\s*\[.*?\]\s*-\s*(https?://\S+)')
    js = re.compile(r'\[javascript\]\s*-\s*\[.*?\]\s*-\s*(https?://\S+)')
    form = re.compile(r'\[form\]\s*-\s*\[.*?\]\s*-\s*(https?://\S+)')

    js_found = set()
    forms_found = set()

    for line in out.splitlines():
        for pattern, target_set in [(ep, urls), (js, js_found), (form, forms_found)]:
            m = pattern.search(line)
            if m:
                u = m.group(1).strip()
                target_set.add(u)
                urls.add(u)

    # Save
    with open(os.path.join(output_dir, "gospider_urls.txt"), "w") as f:
        f.write("\n".join(sorted(urls)))
    with open(os.path.join(output_dir, "gospider_forms.txt"), "w") as f:
        f.write("\n".join(sorted(forms_found)))

    info(f"gospider → {len(urls)} URLs | {len(js_found)} JS | {len(forms_found)} forms")

    if forms_found:
        print(f"\n  {Y}Forms found (potential CSRF/injection targets):{W}")
        for f_url in list(forms_found)[:10]:
            print(f"  {G}→{W} {f_url}")

    return urls

# ─── paramspider ─────────────────────────────────────────────────────────────
def run_paramspider(domain, output_dir):
    """Wayback + CommonCrawl থেকে parameterized URL collect করে"""
    head("PARAMSPIDER — PARAMETER CRAWLER")
    urls = set()

    if check_tool("paramspider"):
        info("paramspider চালাচ্ছি...")
        out_file = os.path.join(output_dir, "paramspider_raw.txt")
        run(f"paramspider -d {domain} -o {out_file} 2>/dev/null", timeout=180)
        if os.path.exists(out_file):
            with open(out_file) as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line: urls.add(line)
        info(f"paramspider → {len(urls)} parameterized URLs")
    else:
        warn("paramspider নেই — install: pip install paramspider")
        # Fallback — Wayback থেকে param URL বের করি
        info("Fallback: Wayback থেকে param URLs আনছি...")
        content, _, _ = http_get(
            f"http://web.archive.org/cdx/search/cdx?url={domain}/*&output=text"
            f"&fl=original&collapse=urlkey&filter=original:.*=.*&limit=20000",
            timeout=60
        )
        for line in content.splitlines():
            if line.strip() and "=" in line: urls.add(line.strip())
        info(f"Fallback param URLs → {len(urls)}")

    # Save deduplicated
    param_file = os.path.join(output_dir, "paramspider_urls.txt")
    with open(param_file, "w") as f:
        f.write("\n".join(sorted(urls)))

    # Categorize by param type
    vuln_params = {
        "SSRF/RFI":      ["url","src","source","dest","redirect","uri","path","continue","window","next","data","reference","site","html","val","validate","domain","callback","return","page","feed","host","port","to","out","view","dir"],
        "XSS":           ["q","s","search","id","lang","keyword","query","page","keywords","year","view","email","type","name","p","month","immagine","list_type","url","terms","categoryid","key","l","begindate","enddate"],
        "SQLi":          ["id","page","report","dir","search","category","file","class","url","news","item","menu","lang","name","ref","title","content","where","step","s","act","access","admin","product"],
        "Open Redirect": ["next","url","target","rurl","dest","destination","redir","redirect_uri","redirect_url","redirect","out","view","to","image_url","go","return","returnTo","return_to","checkout_url","continue","return_path"],
        "LFI/Path":      ["file","document","folder","root","path","pg","style","pdf","template","php_path","doc","page","name","cat","dir","action","board","date","detail","download","prefix","include","inc","locate","show","site","type","view"],
    }

    categorized = {k: [] for k in vuln_params}
    for url in urls:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        for param in params:
            for vuln_type, param_list in vuln_params.items():
                if param.lower() in param_list:
                    categorized[vuln_type].append(url)
                    break

    cat_file = os.path.join(output_dir, "params_by_vulntype.json")
    with open(cat_file, "w") as f:
        json.dump({k: list(set(v))[:50] for k,v in categorized.items()}, f, indent=2)

    print(f"\n  {Y}Parameters by vulnerability type:{W}")
    for vtype, vurls in categorized.items():
        if vurls:
            print(f"  {G}{vtype}{W}: {len(set(vurls))} URLs")

    return urls, categorized

# ─── arjun ───────────────────────────────────────────────────────────────────
def run_arjun(live_hosts, output_dir, sample=10):
    """Hidden parameter discovery — arjun দিয়ে"""
    head("ARJUN — HIDDEN PARAMETER FINDER")
    all_params = {}

    if not check_tool("arjun"):
        warn("arjun নেই — install: pip install arjun")
        return all_params

    # arjun top endpoints-এ চালাই
    targets = live_hosts[:sample]
    info(f"arjun চালাচ্ছি → {len(targets)} endpoint")

    for target in targets:
        out_file = os.path.join(output_dir, f"arjun_{target.replace('https://','').replace('http://','').replace('/','_')}.json")
        result = run(
            f"arjun -u {target} --stable -oJ {out_file} -q 2>/dev/null",
            timeout=120
        )
        if os.path.exists(out_file):
            try:
                with open(out_file) as f:
                    data = json.load(f)
                params_found = data.get("params", [])
                if params_found:
                    all_params[target] = params_found
                    hit(f"Hidden params found: {target}")
                    for p in params_found:
                        print(f"  {G}→ ?{p}={W}")
            except: pass

    # Save combined
    combined_file = os.path.join(output_dir, "arjun_hidden_params.json")
    with open(combined_file, "w") as f:
        json.dump(all_params, f, indent=2)

    total = sum(len(v) for v in all_params.values())
    info(f"arjun → {total} hidden parameters found across {len(all_params)} endpoints")
    return all_params

# ─── jsluice / LinkFinder ─────────────────────────────────────────────────────
def run_jsluice_linkfinder(js_files, output_dir):
    """AST-based JS analysis — regex-এর চেয়ে অনেক accurate"""
    head("JS DEEP ANALYSIS — jsluice / LinkFinder")
    all_endpoints = set()
    all_secrets = []

    has_jsluice    = check_tool("jsluice")
    has_linkfinder = check_tool("linkfinder") or os.path.exists("/usr/local/bin/linkfinder.py")

    if not has_jsluice and not has_linkfinder:
        warn("jsluice/linkfinder নেই")
        warn("jsluice install: go install github.com/BishopFox/jsluice/cmd/jsluice@latest")
        warn("linkfinder install: pip install linkfinder")
        return all_endpoints, all_secrets

    info(f"{min(len(js_files),80)} JS files deep analyze করছি...")

    def analyze_one(js_url):
        endpoints = set()
        secrets = []

        # Download JS file
        content, _, _ = http_get(js_url, timeout=20)
        if not content: return endpoints, secrets

        # Save to temp file
        tmp = f"/tmp/jsrecon_{abs(hash(js_url))}.js"
        with open(tmp, "w", errors="ignore") as f:
            f.write(content)

        # jsluice — AST-based, best accuracy
        if has_jsluice:
            # Extract URLs
            out = run(f"jsluice urls {tmp} 2>/dev/null")
            for line in out.splitlines():
                try:
                    d = json.loads(line)
                    u = d.get("url","")
                    if u and (u.startswith("/") or u.startswith("http")):
                        endpoints.add(u)
                except:
                    if line.startswith("/"): endpoints.add(line.strip())

            # Extract secrets
            out = run(f"jsluice secrets {tmp} 2>/dev/null")
            for line in out.splitlines():
                try:
                    d = json.loads(line)
                    if d.get("kind") or d.get("value"):
                        secrets.append({
                            "type": d.get("kind","unknown"),
                            "value": str(d.get("value",""))[:100],
                            "url": js_url
                        })
                except: pass

        # LinkFinder — fallback or complement
        elif has_linkfinder:
            lf_cmd = "linkfinder" if check_tool("linkfinder") else "python3 /usr/local/bin/linkfinder.py"
            out = run(f"{lf_cmd} -i {tmp} -o cli 2>/dev/null")
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("/") and len(line) > 2:
                    endpoints.add(line)

        # Cleanup
        try: os.remove(tmp)
        except: pass

        return endpoints, secrets

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(analyze_one, url): url for url in js_files[:80]}
        for fut in as_completed(futures):
            eps, secs = fut.result()
            js_url = futures[fut]
            all_endpoints.update(eps)
            all_secrets.extend(secs)
            if eps:   info(f"  {G}{js_url[:65]}{W} → {len(eps)} endpoints")
            if secs:  hit(f"  SECRETS: {js_url[:60]} → {len(secs)} found")

    # Save
    with open(os.path.join(output_dir, "jsluice_endpoints.txt"), "w") as f:
        f.write("\n".join(sorted(all_endpoints)))
    with open(os.path.join(output_dir, "jsluice_secrets.json"), "w") as f:
        json.dump(all_secrets, f, indent=2)

    info(f"Deep JS analysis → {len(all_endpoints)} endpoints | {len(all_secrets)} secrets")
    if all_secrets:
        print(f"\n  {R}{BOLD}⚠ SECRETS:{W}")
        for s in all_secrets[:10]:
            print(f"  {R}[{s['type']}]{W} {s['value'][:80]}")

    return all_endpoints, all_secrets

# ─── reconftw integration ─────────────────────────────────────────────────────
def check_reconftw(domain, output_dir):
    """reconftw আছে কিনা দেখো এবং থাকলে চালাও"""
    head("RECONFTW CHECK")

    reconftw_paths = [
        "/opt/reconftw/reconftw.sh",
        os.path.expanduser("~/reconftw/reconftw.sh"),
        "/tools/reconftw/reconftw.sh",
    ]

    reconftw_path = None
    for path in reconftw_paths:
        if os.path.exists(path):
            reconftw_path = path
            break

    if not reconftw_path and not check_tool("reconftw"):
        warn("reconftw নেই")
        warn("Install: git clone https://github.com/six2dez/reconftw && cd reconftw && ./install.sh")
        print(f"""
  {Y}reconftw manually চালাতে হলে:{W}
  {C}reconftw -d {domain} -r -o {output_dir}/reconftw/{W}
  {C}reconftw -d {domain} -a -o {output_dir}/reconftw/{W}  # full
        """)
        return False

    info(f"reconftw পাওয়া গেছে → {reconftw_path or 'reconftw'}")
    print(f"""
  {Y}reconftw চালাতে চাইলে আলাদাভাবে চালাও:{W}
  {C}reconftw -d {domain} -r -o {output_dir}/reconftw/{W}   # recon only
  {C}reconftw -d {domain} -s -o {output_dir}/reconftw/{W}   # subdomains only
  {C}reconftw -d {domain} -a -o {output_dir}/reconftw/{W}   # all (slow)
    """)
    return True

# ─── Tool Installation Guide ──────────────────────────────────────────────────
def show_install_guide():
    print(f"""
{B}{BOLD}━━━ TOOL INSTALLATION GUIDE ━━━{W}

{Y}Go tools (VPS-এ একবার চালাও):{W}
  go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
  go install github.com/projectdiscovery/httpx/cmd/httpx@latest
  go install github.com/projectdiscovery/katana/cmd/katana@latest
  go install github.com/lc/gau/v2/cmd/gau@latest
  go install github.com/tomnomnom/waybackurls@latest
  go install github.com/jaeles-project/gospider@latest
  go install github.com/BishopFox/jsluice/cmd/jsluice@latest

{Y}Python tools:{W}
  pip install paramspider arjun linkfinder

{Y}reconftw (full pipeline):{W}
  git clone https://github.com/six2dez/reconftw
  cd reconftw && ./install.sh

{Y}Other:{W}
  go install github.com/tomnomnom/assetfinder@latest
  go install github.com/OWASP/Amass/v3/...@latest
  go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
""")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Web DNA Extractor v3 — rajib_mahmud",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
MODES:
  --mode 1   শুধু domain       → URL/JS/API/Parameter deep extraction
  --mode 2   domain + subs    → Subdomain enum → DNS verify → Full extraction

OPTIONS:
  --no-js        JS analysis skip করো (jsluice + regex)
  --no-probe     Active probing skip করো (sensitive path check)
  --no-tech      Tech detection skip করো (header/framework)
  --no-gospider  gospider crawler skip করো
  --no-arjun     Hidden parameter finder skip করো
  --no-params    paramspider skip করো
  --no-dnsx      DNS resolution + takeover check skip করো (Mode 2)
  --no-schema    API schema detection skip করো (Swagger/GraphQL/WSDL)
  --install      সব tool-এর installation guide দেখাও
  -o OUTPUT      Output folder নাম দাও (default: auto-generated)

WHAT IT COLLECTS:
  URLs          → Wayback + CommonCrawl + URLScan + OTX + gau + katana + gospider
  Subdomains    → subfinder + amass + crt.sh + hackertarget + RapidDNS + CertSpotter
  DNS           → dnsx resolve + wildcard detect + takeover candidate
  JS Files      → jsluice (AST) + LinkFinder + regex
  Parameters    → paramspider + arjun hidden params — vuln type categorized
  API Schema    → Swagger + OpenAPI + GraphQL introspection + WADL + WSDL

OUTPUT FILES:
  all_urls.txt              → সব URL একসাথে
  subdomains.txt            → সব subdomain (Mode 2)
  subdomains_resolved.txt   → DNS verified subdomain (Mode 2)
  live_hosts.txt            → Live host list
  endpoints_api.txt         → API endpoints
  js_files.txt              → সব JS file
  parameters.txt            → Parameterized URL
  sensitive_paths.txt       → Admin/config/backup path
  parameters.json           → Parameter detail + high-value flag
  jsluice_endpoints.txt     → jsluice extracted endpoints
  jsluice_secrets.json      → jsluice extracted secrets
  api_schema.json           → Full API schema detail
  api_schema_endpoints.txt  → Schema extracted endpoints
  params_by_vulntype.json   → SSRF/XSS/SQLi/LFI/Redirect candidate
  arjun_hidden_params.json  → Hidden parameter findings
  takeover_candidates.txt   → Subdomain takeover candidate (Mode 2)
  active_probe.json         → Sensitive path probe result
  REPORT.md                 → Final AI-ready report

TELEGRAM:
  cp .env.example .env
  # Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
  # Recon শেষে auto REPORT.md + files পাঠাবে

EXAMPLES:
  python3 recon.py example.com --mode 1
  python3 recon.py example.com --mode 2
  python3 recon.py example.com --mode 1 --no-probe --no-tech
  python3 recon.py example.com --mode 2 -o my_recon
  python3 recon.py --install
        """
    )
    parser.add_argument("domain", nargs="?")
    parser.add_argument("--mode",        type=int, choices=[1,2])
    parser.add_argument("--no-js",       action="store_true")
    parser.add_argument("--no-probe",    action="store_true")
    parser.add_argument("--no-tech",     action="store_true")
    parser.add_argument("--no-gospider", action="store_true")
    parser.add_argument("--no-arjun",    action="store_true")
    parser.add_argument("--no-params",   action="store_true")
    parser.add_argument("--no-dnsx",     action="store_true")
    parser.add_argument("--no-schema",   action="store_true")
    parser.add_argument("--install",     action="store_true")
    parser.add_argument("-o","--output")
    args = parser.parse_args()

    banner()

    if args.install:
        show_install_guide()
        return

    if not args.domain or not args.mode:
        parser.print_help()
        return

    domain = args.domain.replace("https://","").replace("http://","").rstrip("/")
    mode_banner(args.mode, domain)

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.output or f"recon_v3_mode{args.mode}_{domain}_{ts}"
    os.makedirs(out, exist_ok=True)
    info(f"Output: {out}")

    # reconftw check (non-blocking)
    check_reconftw(domain, out)

    all_urls = set()
    targets  = [domain]
    live     = [f"https://{domain}"]

    # ── MODE 1 ──────────────────────────────────────────────────────────────
    if args.mode == 1:
        head("URL COLLECTION — SINGLE DOMAIN")

        if check_tool("gau"):
            info("gau চালাচ্ছি...")
            for l in run(f"gau {domain} --threads 5 2>/dev/null", 300).splitlines():
                if domain in l: all_urls.add(l.strip())

        if check_tool("waybackurls"):
            info("waybackurls চালাচ্ছি...")
            for l in run(f"echo {domain} | waybackurls 2>/dev/null", 180).splitlines():
                if domain in l: all_urls.add(l.strip())

        if check_tool("katana"):
            info("katana চালাচ্ছি...")
            for l in run(f"katana -u https://{domain} -silent -d 4 -jc 2>/dev/null", 300).splitlines():
                if domain in l: all_urls.add(l.strip())

        # gospider
        if not args.no_gospider:
            gs_urls = run_gospider(f"https://{domain}", out, depth=3)
            all_urls.update(gs_urls)

        # More sources
        info("Wayback CDX আনছি...")
        all_urls.update(fetch_wayback(domain, wildcard=False))
        info("CommonCrawl আনছি...")
        all_urls.update(fetch_commoncrawl(domain, wildcard=False))
        info("URLScan আনছি...")
        r = fetch_urlscan(domain); all_urls.update(r); info(f"URLScan → {len(r)}")
        info("OTX AlienVault আনছি...")
        r = fetch_otx(domain); all_urls.update(r); info(f"OTX → {len(r)}")

    # ── MODE 2 ──────────────────────────────────────────────────────────────
    else:
        head("SUBDOMAIN ENUMERATION")
        subs = {domain}

        for tool, cmd in [
            ("subfinder", f"subfinder -d {domain} -silent 2>/dev/null"),
            ("amass",     f"amass enum -passive -d {domain} 2>/dev/null"),
            ("assetfinder", f"assetfinder --subs-only {domain} 2>/dev/null"),
        ]:
            if check_tool(tool):
                info(f"{tool}...")
                for l in run(cmd, 180).splitlines():
                    if l.strip(): subs.add(l.strip())

        # API sources
        for label, fetcher in [
            ("crt.sh",       lambda: _crtsh(domain)),
            ("hackertarget", lambda: _hackertarget(domain)),
            ("RapidDNS",     lambda: fetch_subdomains_rapiddns(domain)),
            ("BufferOver",   lambda: fetch_subdomains_bufferover(domain)),
            ("CertSpotter",  lambda: fetch_subdomains_certspotter(domain)),
            ("ThreatCrowd",  lambda: fetch_subdomains_threatcrowd(domain)),
        ]:
            info(f"{label}...")
            try: subs.update(fetcher())
            except: pass

        targets = sorted(subs)
        with open(os.path.join(out,"subdomains.txt"),"w") as f:
            f.write("\n".join(targets))
        info(f"মোট subdomains: {BOLD}{len(targets)}{W}")

        # Live check
        head("LIVE HOST CHECK")
        if check_tool("httpx"):
            result = run(f"httpx -l {out}/subdomains.txt -silent -status-code -title -json 2>/dev/null", 300)
            live = []
            for l in result.splitlines():
                try:
                    d=json.loads(l); u=d.get("url","")
                    if u: live.append(u); info(f"  {G}{u}{W} [{d.get('status_code','')}]")
                except: pass
        else:
            def chk(sub):
                for s in ["https","http"]:
                    u=f"{s}://{sub}"
                    r=run(f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout 5 {u}")
                    if r and r not in ["000",""]: return u
            with ThreadPoolExecutor(20) as ex:
                live = [r for r in ex.map(chk, targets) if r]

        with open(os.path.join(out,"live_hosts.txt"),"w") as f:
            f.write("\n".join(live))
        info(f"Live hosts: {BOLD}{len(live)}{W}")

        # dnsx — DNS validation + takeover check
        resolved_hosts = live
        takeover_candidates = []
        if not args.no_dnsx:
            resolved_hosts, takeover_candidates = run_dnsx(targets, out)
            if takeover_candidates:
                hit(f"⚠ {len(takeover_candidates)} SUBDOMAIN TAKEOVER CANDIDATES FOUND!")

        # URL collection
        head("URL COLLECTION — ALL SUBDOMAINS")
        if check_tool("gau"):
            for l in run(f"gau --subs {domain} --threads 10 2>/dev/null", 400).splitlines():
                all_urls.add(l.strip())
        if check_tool("katana") and live:
            for l in run(f"katana -list {out}/live_hosts.txt -silent -d 3 -jc 2>/dev/null", 400).splitlines():
                all_urls.add(l.strip())

        # gospider — all live hosts
        if not args.no_gospider and live:
            for host in live[:10]:
                gs_urls = run_gospider(host, out, depth=2)
                all_urls.update(gs_urls)

        info("Wayback CDX wildcard...")
        all_urls.update(fetch_wayback(domain, wildcard=True))
        info("CommonCrawl wildcard...")
        all_urls.update(fetch_commoncrawl(domain, wildcard=True))
        all_urls.update(fetch_urlscan(domain))
        all_urls.update(fetch_otx(domain))

    all_urls = {u for u in all_urls if u}
    with open(os.path.join(out,"all_urls.txt"),"w") as f:
        f.write("\n".join(sorted(all_urls)))
    info(f"মোট URLs: {BOLD}{len(all_urls)}{W}")

    # ── Shared Phases ────────────────────────────────────────────────────────
    cats   = categorize_urls(all_urls, out)
    params = extract_parameters(all_urls, out)

    # paramspider
    param_urls, param_cats = set(), {}
    if not args.no_params:
        param_urls, param_cats = run_paramspider(domain, out)
        all_urls.update(param_urls)

    # API Schema Detection
    schema_findings = {}
    schema_endpoints = set()
    if not args.no_schema:
        schema_findings, schema_endpoints = detect_api_schema(live, out)
        all_urls.update(schema_endpoints)

    # arjun — hidden params
    hidden_params = {}
    if not args.no_arjun and live:
        hidden_params = run_arjun(live, out, sample=8)

    # JS Analysis — jsluice/LinkFinder first, regex fallback
    js_all = []
    jsluice_endpoints = set()
    jsluice_secrets = []
    if not args.no_js and cats.get("js_files"):
        js_files = list(set(cats["js_files"]))

        # Deep analysis — jsluice / LinkFinder
        jsluice_endpoints, jsluice_secrets = run_jsluice_linkfinder(js_files, out)

        # Regex analysis (always runs — complements jsluice)
        head("JS ANALYSIS — REGEX (complement)")
        info(f"{min(len(js_files),60)} JS files regex analyze করছি...")
        with ThreadPoolExecutor(max_workers=10) as ex:
            for r in ex.map(analyze_js_file, js_files[:60]):
                js_all.append(r)
                if r["endpoints"]: info(f"  {G}{r['url'][:65]}{W} → {len(r['endpoints'])} endpoints")
                if r["secrets"]:
                    for s in r["secrets"]: hit(f"SECRET: {s['type']} → {r['url'][:60]}")

    # Active Probing
    probe = []
    param_probe = []
    if not args.no_probe:
        probe_target = live[0] if live else f"https://{domain}"
        probe = active_probe(probe_target, out)
        combined_params = list(cats.get("parameters",[])) + list(param_urls)
        if combined_params:
            param_probe = probe_params(combined_params, out)

    if not args.no_tech:
        detect_tech(live[:20] if args.mode==2 else [f"https://{domain}"], out)

    # ── Final Report ─────────────────────────────────────────────────────────
    # Combine all JS findings
    js_secrets_combined = jsluice_secrets + [
        s for r in js_all for s in r.get("secrets",[])
    ]
    js_endpoints_combined = sorted(
        jsluice_endpoints | set(ep for r in js_all for ep in r.get("endpoints",[]))
    )

    flagged = params[1] if isinstance(params, tuple) else []
    probe_flagged  = [p for p in probe if p.get("flags")]
    critical_probes = [p for p in probe if any(
        f in p.get("flags",[]) for f in ["GIT_EXPOSED","CONFIG_EXPOSED","SPRING_ACTUATOR","API_DOCS"]
    )]

    head("FINAL REPORT")
    report = f"""# RECON REPORT v3 — {domain}
### Mode: {"SINGLE DOMAIN" if args.mode==1 else "DOMAIN + SUBDOMAINS"}
### {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | by rajib_mahmud

---

## SUMMARY

| | Count |
|--|--|
| {"Subdomains" if args.mode==2 else "Target"} | {len(targets)} |
| Total URLs | {len(all_urls)} |
| API Endpoints | {len(set(cats.get('endpoints_api',[])))} |
| JS Files | {len(set(cats.get('js_files',[])))} |
| JS Endpoints (jsluice) | {len(jsluice_endpoints)} |
| JS Endpoints (regex) | {len(set(ep for r in js_all for ep in r.get('endpoints',[])))} |
| **JS Secrets** | **{len(js_secrets_combined)}** |
| Parameterized URLs | {len(set(cats.get('parameters',[])))} |
| ParamSpider URLs | {len(param_urls)} |
| Hidden Params (arjun) | {sum(len(v) for v in hidden_params.values())} |
| High-value Params | {len(flagged)} |
| Active Probe Hits | {len(probe)} |
| **Critical Probe Hits** | **{len(critical_probes)}** |
| Param Probe Findings | {len(param_probe)} |

---
"""
    if js_secrets_combined:
        report += f"\n## 🔴 SECRETS FOUND ({len(js_secrets_combined)})\n"
        for s in js_secrets_combined[:20]:
            val = s.get('value') or (s.get('matches',[''])[0] if s.get('matches') else '')
            report += f"- **{s['type']}** → `{s.get('url','')}`\n  `{val[:80]}`\n"

    # Takeover candidates
    takeover_candidates = []
    takeover_file = os.path.join(out, "takeover_candidates.txt")
    if os.path.exists(takeover_file):
        try:
            with open(takeover_file) as f:
                takeover_candidates = json.load(f)
        except: pass

    if takeover_candidates:
        report += f"\n## 🔴 SUBDOMAIN TAKEOVER CANDIDATES ({len(takeover_candidates)})\n"
        for t in takeover_candidates:
            report += f"- `{t.get('host','')}` → {t.get('service','unknown')} — `{t.get('cname', t.get('status',''))}`\n"

    if critical_probes:
        report += f"\n## 🔴 CRITICAL PROBE HITS\n"
        for p in critical_probes:
            report += f"- `{p['url']}` [{p['status']}] — {', '.join(p['flags'])}\n"

    if param_probe:
        report += f"\n## 🔴 PARAMETER FINDINGS\n"
        for p in param_probe:
            report += f"- **{p['type']}** [{p['severity']}] `{p['url']}`\n"

    if hidden_params:
        report += f"\n## 🟡 HIDDEN PARAMETERS (arjun)\n"
        for url, plist in hidden_params.items():
            report += f"- `{url}` → `{'`, `'.join(plist)}`\n"

    # API Schema
    if schema_findings:
        report += f"\n## 🟢 API SCHEMA FOUND\n"
        for stype, results in schema_findings.items():
            if results:
                report += f"\n### {stype.upper()} ({len(results)})\n"
                for r in results:
                    ep_count = len(r.get("endpoints",[]))
                    report += f"- `{r['url']}` [{r['status']}]"
                    if ep_count: report += f" → {ep_count} endpoints"
                    report += "\n"
                    for ep in r.get("endpoints",[])[:10]:
                        report += f"  - `{ep}`\n"

    if param_cats:
        report += f"\n## PARAMETERS BY VULN TYPE\n"
        for vtype, vurls in param_cats.items():
            if vurls:
                report += f"\n### {vtype} ({len(set(vurls))})\n"
                for u in list(set(vurls))[:5]:
                    report += f"- `{u}`\n"

    report += f"\n## JS ENDPOINTS\n"
    for ep in js_endpoints_combined[:60]:
        report += f"- `{ep}`\n"

    report += f"\n## HIGH-VALUE PARAMETERS\n"
    for p in flagged[:25]:
        report += f"- `?{p['param']}=` ({p['count']}x) → `{p['sample'][:90]}`\n"

    report += f"\n## SENSITIVE PATHS\n"
    for url in sorted(set(cats.get('sensitive_paths',[])))[:40]:
        report += f"- `{url}`\n"

    report += f"""
---

## AI PROMPT — master.md-এ paste করো

```
Target: {domain}
Mode: {"Single Domain" if args.mode==1 else "Full (Domain + Subdomains)"}
Total URLs: {len(all_urls)}
JS Secrets: {len(js_secrets_combined)} {"⚠ CRITICAL" if js_secrets_combined else ""}
Critical Probes: {len(critical_probes)} {" → " + ", ".join([p["url"] for p in critical_probes[:2]]) if critical_probes else ""}
Hidden Params (arjun): {sum(len(v) for v in hidden_params.values())}
Param Findings: {len(param_probe)}
High-value Params: {", ".join(["?"+p["param"]+"=" for p in flagged[:15]])}
Param by vulntype: {json.dumps({k:len(v) for k,v in param_cats.items() if v})}
JS Endpoints: {", ".join(js_endpoints_combined[:20])}
```
"""
    with open(os.path.join(out,"REPORT.md"),"w") as f:
        f.write(report)

    info(f"Report: {BOLD}{out}/REPORT.md{W}")
    print(f"\n{G}{BOLD}✓ Done! → {out}/{W}\n")

    # ── Telegram Notification ────────────────────────────────────────────────
    # param_cats থেকে SSRF count বের করি
    ssrf_count = len(set(param_cats.get("SSRF/RFI", []))) if param_cats else 0

    tg_notify_recon_done(domain, out, stats={
        "urls":          len(all_urls),
        "subdomains":    len(targets),
        "live":          len(live),
        "api":           len(set(cats.get("endpoints_api",[]))),
        "js":            len(set(cats.get("js_files",[]))),
        "params":        len(set(cats.get("parameters",[]))),
        "schemas":       sum(len(v) for v in schema_findings.values()) if schema_findings else 0,
        "secrets":       len(js_secrets_combined),
        "takeover":      len(takeover_candidates),
        "hidden_params": sum(len(v) for v in hidden_params.values()),
        "ssrf":          ssrf_count,
    })

# ─── Helper functions for subdomain sources ───────────────────────────────────
def _crtsh(domain):
    subs = set()
    c,_,_ = http_get(f"https://crt.sh/?q=%.{domain}&output=json", 30)
    for e in json.loads(c):
        for n in e.get("name_value","").split("\n"):
            n=n.strip().lstrip("*.")
            if domain in n: subs.add(n)
    return subs

def _hackertarget(domain):
    subs = set()
    c,_,_ = http_get(f"https://api.hackertarget.com/hostsearch/?q={domain}", 20)
    for l in c.splitlines():
        if "," in l:
            s=l.split(",")[0].strip()
            if domain in s: subs.add(s)
    return subs

if __name__ == "__main__":
    main()
