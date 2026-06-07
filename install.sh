#!/bin/bash
# ═══════════════════════════════════════════════════════
# ReconAuto — One-Click Tool Installer
# by rajib_mahmud
# ═══════════════════════════════════════════════════════

set -e

R="\033[91m"; G="\033[92m"; Y="\033[93m"
C="\033[96m"; W="\033[0m"; BOLD="\033[1m"

print_banner() {
echo -e "${C}${BOLD}"
cat << 'BANNER'
██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗ █████╗ ██╗   ██╗████████╗ ██████╗
██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗
██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║███████║██║   ██║   ██║   ██║   ██║
██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║██╔══██║██║   ██║   ██║   ██║   ██║
██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║██║  ██║╚██████╔╝   ██║   ╚██████╔╝
╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝
BANNER
echo -e "${W}${Y}           Tool Installer — by rajib_mahmud${W}"
echo ""
}

ok()   { echo -e "${G}[✓]${W} $1"; }
fail() { echo -e "${R}[✗]${W} $1"; }
info() { echo -e "${Y}[*]${W} $1"; }
head() { echo -e "\n${C}${BOLD}━━━ $1 ━━━${W}"; }

# ── Go tool installer ────────────────────────────────────────────────────────
install_go_tool() {
    local name=$1
    local pkg=$2
    if command -v "$name" &>/dev/null; then
        ok "$name (already installed)"
        return
    fi
    info "Installing $name..."
    if go install "$pkg" 2>/dev/null; then
        if command -v "$name" &>/dev/null; then
            ok "$name installed successfully"
        else
            fail "$name binary not in PATH — add GOPATH/bin to PATH"
        fi
    else
        fail "$name install failed — try: go install $pkg"
    fi
}

# ── Pip tool installer ────────────────────────────────────────────────────────
install_pip_tool() {
    local name=$1
    local pkg=$2
    if command -v "$name" &>/dev/null || pip show "$pkg" &>/dev/null 2>&1; then
        ok "$name (already installed)"
        return
    fi
    info "Installing $name..."
    if pip install "$pkg" -q 2>/dev/null || pip3 install "$pkg" -q 2>/dev/null; then
        ok "$name installed"
    else
        fail "$name install failed — try: pip install $pkg"
    fi
}

print_banner

# ── System check ─────────────────────────────────────────────────────────────
head "SYSTEM CHECK"

# Python
if command -v python3 &>/dev/null; then
    ok "Python3: $(python3 --version)"
else
    fail "Python3 not found — install: sudo apt install python3"
    exit 1
fi

# pip
if command -v pip &>/dev/null || command -v pip3 &>/dev/null; then
    ok "pip found"
else
    info "Installing pip..."
    python3 -m ensurepip --upgrade 2>/dev/null || sudo apt install python3-pip -y 2>/dev/null
fi

# Go
if command -v go &>/dev/null; then
    ok "Go: $(go version | awk '{print $3}')"
    GO_AVAILABLE=true
    # Add GOPATH to PATH
    export PATH="$PATH:$(go env GOPATH)/bin"
    GOPATH_BIN="$(go env GOPATH)/bin"
    if ! grep -q "GOPATH" ~/.bashrc 2>/dev/null; then
        echo "export PATH=\$PATH:\$(go env GOPATH)/bin" >> ~/.bashrc
        info "Added GOPATH/bin to ~/.bashrc"
    fi
else
    fail "Go not found"
    echo -e "  ${Y}Install Go:${W}"
    echo -e "  ${C}wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz${W}"
    echo -e "  ${C}sudo tar -C /usr/local -xzf go1.21.0.linux-amd64.tar.gz${W}"
    echo -e "  ${C}echo 'export PATH=\$PATH:/usr/local/go/bin' >> ~/.bashrc${W}"
    echo -e "  ${C}source ~/.bashrc${W}"
    GO_AVAILABLE=false
fi

# ── Go Tools ──────────────────────────────────────────────────────────────────
if [ "$GO_AVAILABLE" = true ]; then
    head "GO TOOLS"
    install_go_tool "subfinder"   "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    install_go_tool "httpx"       "github.com/projectdiscovery/httpx/cmd/httpx@latest"
    install_go_tool "katana"      "github.com/projectdiscovery/katana/cmd/katana@latest"
    install_go_tool "dnsx"        "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
    install_go_tool "gau"         "github.com/lc/gau/v2/cmd/gau@latest"
    install_go_tool "waybackurls" "github.com/tomnomnom/waybackurls@latest"
    install_go_tool "assetfinder" "github.com/tomnomnom/assetfinder@latest"
    install_go_tool "gospider"    "github.com/jaeles-project/gospider@latest"
    install_go_tool "jsluice"     "github.com/BishopFox/jsluice/cmd/jsluice@latest"
fi

# ── Python Tools ──────────────────────────────────────────────────────────────
head "PYTHON TOOLS"
install_pip_tool "paramspider" "paramspider"
install_pip_tool "arjun"       "arjun"
install_pip_tool "linkfinder"  "linkfinder"

# ── Telegram Setup ────────────────────────────────────────────────────────────
head "TELEGRAM SETUP"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        ok ".env created from .env.example"
        echo -e "  ${Y}Edit .env and add your:${W}"
        echo -e "  ${C}TELEGRAM_BOT_TOKEN${W} — from @BotFather"
        echo -e "  ${C}TELEGRAM_CHAT_ID${W}   — from @userinfobot"
    fi
else
    ok ".env already exists"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
head "SUMMARY"
ALL_TOOLS=(subfinder httpx katana dnsx gau waybackurls assetfinder gospider jsluice arjun paramspider)
FOUND=0
MISSING=()

for tool in "${ALL_TOOLS[@]}"; do
    if command -v "$tool" &>/dev/null; then
        ((FOUND++))
        ok "$tool"
    else
        MISSING+=("$tool")
        fail "$tool — not found"
    fi
done

echo ""
echo -e "${BOLD}Coverage: ${FOUND}/${#ALL_TOOLS[@]} tools installed${W}"

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${Y}Missing: ${MISSING[*]}${W}"
fi

if [ "$FOUND" -ge 8 ]; then
    echo -e "\n${G}${BOLD}✓ Full power mode — 90%+ coverage${W}"
elif [ "$FOUND" -ge 5 ]; then
    echo -e "\n${Y}Good coverage — install remaining tools for best results${W}"
else
    echo -e "\n${Y}Basic mode — Python fallback active (60% coverage)${W}"
fi

echo -e "\n${G}${BOLD}Ready! Run:${W}"
echo -e "  ${C}python3 recon.py target.com --mode 1${W}   # Single domain"
echo -e "  ${C}python3 recon.py target.com --mode 2${W}   # Full recon"
echo -e "  ${C}python3 recon.py --help${W}                # All options"
echo ""
