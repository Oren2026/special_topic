#!/bin/bash
# detect.sh — 環境偵測函式庫
# 提供 is_installed, has_ros2, has_ros_pkg, check_environment 等函式

set -euo pipefail

# ─── 來源 utils.sh ───
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=utils.sh
source "${SCRIPT_DIR}/utils.sh"

# ─── 基本指令是否存在 ───
is_installed() {
    command -v "$1" &>/dev/null
}

# ─── apt 套件是否已安裝 ───
is_apt_installed() {
    dpkg -l "$1" &>/dev/null
}

# ─── pip 套件是否已安裝 ───
is_pip_installed() {
    pip3 show "${1%%[<>=]*}" &>/dev/null
}

# ─── 是否已有 ROS2 Humble ───
has_ros2() {
    is_installed ros2 && \
    [[ -f /opt/ros/humble/setup.bash ]]
}

# ─── ROS2 套件是否已安裝 ───
# 用法：has_ros_pkg nav2_bringup
has_ros_pkg() {
    local pkg="$1"
    [[ -d "/opt/ros/humble/share/$pkg" ]]
}

# ─── Gazebo 是否已安裝 ───
has_gazebo() {
    is_installed gz || is_installed gazebo
}

# ─── Gazebo 版本檢查 ───
gazebo_version() {
    if is_installed gz; then
        gz sim --version 2>/dev/null | head -1 || echo "unknown"
    elif is_installed gazebo; then
        gazebo --version 2>/dev/null | head -1 || echo "unknown"
    else
        echo "not installed"
    fi
}

# ─── colcon 是否存在 ───
has_colcon() {
    is_installed colcon
}

# ─── git 是否存在 ───
has_git() {
    is_installed git
}

# ─── Docker 是否存在 ───
has_docker() {
    is_installed docker
}

# ─── CUDA/GPU 是否可用 ───
has_cuda() {
    is_installed nvidia-smi && nvidia-smi &>/dev/null
}

# ─── 檢查系統資源是否足夠 ───
check_system_resources() {
    log_step "檢查系統資源..."

    local mem_gb
    mem_gb=$(get_mem_gb)

    local cpu_cores
    cpu_cores=$(get_cpu_cores)

    local os_name
    os_name=$(detect_os)

    log_info "系統: $os_name"
    log_info "CPU cores: $cpu_cores"
    log_info "RAM: ${mem_gb} GB"

    local warnings=()

    if (( mem_gb < 8 )); then
        warnings+=("記憶體低於 8GB，ROS2 編譯可能會記憶體不足")
    fi

    if (( cpu_cores < 4 )); then
        warnings+=("CPU 核心數少於 4，編譯速度會較慢")
    fi

    if [[ ! "$os_name" =~ ^ubuntu-22 ]]; then
        warnings+=("建議使用 Ubuntu 22.04，其他版本可能相容性問題")
    fi

    if ((${#warnings[@]} > 0)); then
        echo ""
        for w in "${warnings[@]}"; do
            log_warn "$w"
        done
    fi

    log_ok "系統資源檢查完成"
    return 0
}

# ─── 完整環境檢測報告 ───
check_environment() {
    echo ""
    echo -e "${COLOR_BOLD}═══════════════════════════════════════════${COLOR_RESET}"
    echo -e "${COLOR_BOLD}       ROS2 Crossfloor AMR 環境檢測報告${COLOR_RESET}"
    echo -e "${COLOR_BOLD}═══════════════════════════════════════════${COLOR_RESET}"
    echo ""

    check_system_resources
    echo ""

    local items=(
        "Ubuntu 22.04:is_ubuntu2204"
        "git:has_git"
        "curl:is_installed curl"
        "build-essential:is_installed make"
        "Python3:is_installed python3"
        "pip3:is_installed pip3"
        "colcon:has_colcon"
        "ROS2 Humble:has_ros2"
        "Gazebo:has_gazebo"
    )

    local total=${#items[@]}
    local current=0
    local missing=()

    for item in "${items[@]}"; do
        ((current++))
        local name="${item%%:*}"
        local check="${item#*:}"
        progress "$current" "$total" "檢查: $name"

        # eval 動態執行檢測函式
        # shellcheck disable=SC2246
        if ! eval "$check" 2>/dev/null; then
            missing+=("$name")
        fi
    done

    echo ""
    echo -e "${COLOR_BOLD}═══════════════════════════════════════════${COLOR_RESET}"

    if ((${#missing[@]} > 0)); then
        echo -e "${COLOR_YELLOW}缺少元件：${missing[*]}${COLOR_RESET}"
        echo ""
        echo "執行 ./installer/install.sh 進行安裝"
    else
        log_ok "所有依賴皆已滿足"
    fi

    echo ""
    return 0
}

# ─── 匯出函式供外部使用 ───
export -f is_installed
export -f is_apt_installed
export -f is_pip_installed
export -f has_ros2
export -f has_ros_pkg
export -f has_gazebo
export -f has_colcon
export -f has_git
export -f has_docker
export -f has_cuda
export -f check_environment