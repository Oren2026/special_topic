#!/bin/bash
# install_gazebo.sh — Gazebo Harmonic 安裝模組

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils.sh"
source "${SCRIPT_DIR}/detect.sh"

# ─── 安裝 Gazebo Harmonic ───
install() {
    log_step "安裝 Gazebo Harmonic..."

    # 1. 安裝依賴
    log_info "[1/3] 安裝系統依賴..."
    require_root
    apt_install \
        wget \
        gnupg \
        libbullet-dev \
        libsdformat11 \
        libavcodec-dev \
        libavformat-dev \
        libavutil-dev \
        libfreeimage-dev \
        libgtest-dev \
        libgts-dev \
        libogre-1.9-dev \
        libogre-2.3-dev \
        libprotoc-dev \
        libswscale-dev \
        libtinyxml2-dev \
        libxml2-dev \
        pkg-config

    # 2. 加入 OSRF 源
    log_info "[2/3] 加入 OSRF（Open Source Robotics Foundation）軟體源..."
    local osrf_sources="/etc/apt/sources.list.d/gazebo.list"
    if [[ ! -f "$osrf_sources" ]]; then
        require_root
        wget -q -O /tmp/gazebo-keyring.deb https://packages.osrfoundation.org/gazebo.pub.key
        apt install -y /tmp/gazebo-keyring.deb
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu $(lsb_release -cs) main" \
            | tee "$osrf_sources" > /dev/null
        apt update -qq
        rm -f /tmp/gazebo-keyring.deb
        log_ok "OSRF 軟體源已加入"
    else
        log_ok "OSRF 軟體源已存在"
    fi

    # 3. 安裝 Gazebo Harmonic
    log_info "[3/3] 安裝 Gazebo Harmonic（模擬器本體）..."
    require_root
    DEBIAN_FRONTEND=noninteractive apt install -y \
        gz-harmonic \
        gz-sim7 \
        gz-tools

    log_ok "Gazebo Harmonic 安裝完成"
    log_info "可用指令：gz sim（啟動模擬器）"
}

# ─── 檢查 ───
check() {
    log_step "檢查 Gazebo 安裝狀態..."
    if has_gazebo; then
        local ver
        ver=$(gazebo_version)
        log_ok "Gazebo 已安裝：$ver"
        return 0
    else
        log_warn "Gazebo 未安裝"
        return 1
    fi
}

# ─── 驗證 ───
verify() {
    log_step "驗證 Gazebo Harmonic..."
    if ! has_gazebo; then
        log_error "驗證失敗"
        return 1
    fi

    if command -v gz &>/dev/null; then
        local ver
        ver=$(gz --version 2>/dev/null | head -1 || echo "unknown")
        log_ok "驗證成功：$ver"
        return 0
    fi
    log_error "驗證失敗：gz 指令無法執行"
    return 1
}

# ─── 入口 ───
main() {
    local action="${1:-check}"
    case "$action" in
        check)   check ;;
        install) install ;;
        verify)  verify ;;
        *)
            echo "用法：$0 [check|install|verify]"
            exit 1
            ;;
    esac
}

main "$@"