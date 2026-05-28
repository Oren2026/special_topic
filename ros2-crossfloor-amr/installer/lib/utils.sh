#!/bin/bash
# utils.sh — 共用工具函式庫
# 包含顏色輸出、日誌、進度條、系統偵測等工具函式

set -euo pipefail

# ─── 顏色定義 ───
export COLOR_RESET='\033[0m'
export COLOR_RED='\033[0;31m'
export COLOR_GREEN='\033[0;32m'
export COLOR_YELLOW='\033[0;33m'
export COLOR_BLUE='\033[0;34m'
export COLOR_CYAN='\033[0;36m'
export COLOR_BOLD='\033[1m'

# ─── 日誌函式 ───
log_info()  { echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET}  $*"; }
log_ok()    { echo -e "${COLOR_GREEN}[OK]${COLOR_RESET}   $*"; }
log_warn()  { echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET}  $*"; }
log_error() { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $*"; }
log_step()  { echo -e "${COLOR_CYAN}[STEP]${COLOR_RESET}  $*"; }

# ─── 進度條 ───
# 用法：progress 3 "描述文字"
progress() {
    local current=$1
    local total=$2
    local msg="${3:-}"
    local pct=$((current * 100 / total))
    local done=$((pct / 2))
    local remain=$((50 - done))
    printf "\r${COLOR_CYAN}[%-50s] %3d%%${COLOR_RESET} %s" \
        "$(printf '#%.0s' $(seq 1 $done) 2>/dev/null || echo '')" \
        "$pct" "$msg"
    if (( current == total )); then
        echo ""
    fi
}

# ─── 確認提示 ───
# 用法：confirm "要繼續嗎？" || exit 0
confirm() {
    local prompt="${1:-繼續？}"
    local default="${2:-N}"
    local yn
    if [[ "$default" == "Y" ]]; then
        prompt="$prompt [Y/n]"
    else
        prompt="$prompt [y/N]"
    fi
    read -p "$prompt " yn
    case "$yn" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

# ─── 是否為 root ───
is_root() {
    [[ "$EUID" -eq 0 ]]
}

# ─── 需求 root ───
require_root() {
    if ! is_root; then
        log_error "此操作需要 root 權限。請使用 sudo 執行。"
        exit 1
    fi
}

# ─── 作業系統偵測 ───
detect_os() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        echo "$ID-$VERSION_ID"
    else
        echo "unknown"
    fi
}

# ─── 是否為 Ubuntu 22.04 ───
is_ubuntu2204() {
    [[ "$(detect_os)" == "ubuntu-22.04" ]]
}

# ─── 取得 CPU 核心數 ───
get_cpu_cores() {
    nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 4
}

# ─── 取得可用記憶體（GB） ───
get_mem_gb() {
    awk '/MemTotal/ {printf "%.0f", $2/1024/1024}' /proc/meminfo 2>/dev/null || echo 8
}

# ─── 安裝套件（apt） ───
# 用法：apt_install <package1> <package2> ...
apt_install() {
    require_root
    local packages=("$@")
    local missing=()
    for pkg in "${packages[@]}"; do
        if ! dpkg -l "$pkg" &>/dev/null; then
            missing+=("$pkg")
        fi
    done
    if ((${#missing[@]} > 0)); then
        log_info "安裝缺少的套件: ${missing[*]}"
        apt update -qq
        DEBIAN_FRONTEND=noninteractive apt install -y "${missing[@]}"
    else
        log_ok "所有套件皆已安裝: ${packages[*]}"
    fi
}

# ─── pip 安裝 ───
pip_install() {
    local packages=("$@")
    for pkg in "${packages[@]}"; do
        if pip show "${pkg%%[<>=]*}" &>/dev/null; then
            log_ok "已安裝: $pkg"
        else
            log_info "安裝 Python 套件: $pkg"
            pip3 install "$pkg" -q
        fi
    done
}

# ─── 等待使用者按 Enter ───
pause() {
    echo ""
    read -p "按 Enter 繼續..." </dev/tty
}

# ─── 執行指令並記錄 log ───
run_cmd() {
    local cmd="$*"
    local logfile="${LOGFILE:-/tmp/ros2_install.log}"
    log_info "執行: $cmd"
    if $cmd >> "$logfile" 2>&1; then
        log_ok "完成"
        return 0
    else
        log_error "失敗，詳細 log: $logfile"
        return 1
    fi
}

# ─── 建立目錄（如不存在） ───
ensure_dir() {
    if [[ ! -d "$1" ]]; then
        mkdir -p "$1"
        log_info "建立目錄: $1"
    fi
}

# ─── 備份檔案 ───
backup_file() {
    if [[ -f "$1" ]] && [[ ! -f "${1}.bak" ]]; then
        cp "$1" "${1}.bak"
        log_info "備份: $1 → ${1}.bak"
    fi
}

# ─── 結尾報告 ───
report() {
    local status="$1"
    local msg="${2:-}"
    echo ""
    if [[ "$status" == "success" ]]; then
        echo -e "${COLOR_BOLD}${COLOR_GREEN}"
        echo "╔══════════════════════════════════════════╗"
        echo "║         ✅ 安裝完成！                     ║"
        echo "╚══════════════════════════════════════════╝"
        echo -e "${COLOR_RESET}"
    else
        echo -e "${COLOR_BOLD}${COLOR_RED}"
        echo "╔══════════════════════════════════════════╗"
        echo "║         ❌ 安裝失敗                      ║"
        echo "╚══════════════════════════════════════════╝"
        echo -e "${COLOR_RESET}"
    fi
    [[ -n "$msg" ]] && echo -e "${COLOR_YELLOW}$msg${COLOR_RESET}"
}