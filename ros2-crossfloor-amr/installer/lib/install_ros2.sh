#!/bin/bash
# install_ros2.sh — ROS2 Humble 安裝模組
# 支援檢測、補安裝、完整移除

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=utils.sh
source "${SCRIPT_DIR}/utils.sh"
# shellcheck source=detect.sh
source "${SCRIPT_DIR}/detect.sh"

# ─── 主要函式 ───

# 檢查是否已安裝
check() {
    log_step "檢查 ROS2 Humble 安裝狀態..."
    if has_ros2; then
        log_ok "ROS2 Humble 已安裝"
        # 顯示已安裝的 packages 數量
        if [[ -d /opt/ros/humble/share ]]; then
            local count
            count=$(find /opt/ros/humble/share -maxdepth 1 -type d | wc -l)
            log_info "已安裝 packages: $((count - 1)) 個"
        fi
        return 0
    else
        log_warn "ROS2 Humble 未安裝"
        return 1
    fi
}

# 安裝
install() {
    log_step "安裝 ROS2 Humble..."

    # 1. 安裝前置依賴
    log_info "[1/4] 安裝系統依賴..."
    require_root
    apt_install \
        curl \
        gnupg2 \
        lsb-release \
        software-properties-common \
        build-essential \
        cmake \
        pkg-config \
        libssl-dev \
        libgl1-mxl-glx \
        libglib2.0-dev \
        libeigen3-dev \
        python3-colcon-common-extensions \
        python3-pip \
        python3-venv \
        python3-dev

    # 2. 加入 ROS2 apt 源
    log_info "[2/4] 加入 ROS2 軟體源..."
    local ros_sources_list="/etc/apt/sources.list.d/ros2.list"
    if [[ ! -f "$ros_sources_list" ]]; then
        require_root
        curl -ssL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
            | apt-key add -
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) main" \
            | tee "$ros_sources_list" > /dev/null
        apt update -qq
        log_ok "ROS2 apt 源已加入"
    else
        log_ok "ROS2 apt 源已存在"
    fi

    # 3. 安裝 ROS2 Humble本體
    log_info "[3/4] 安裝 ROS2 Humble（本體約 2GB，可能需要 10-20 分鐘）..."
    require_root
    DEBIAN_FRONTEND=noninteractive apt install -y \
        ros-humble-ros-base \
        ros-humble-angles \
        ros-humble-tf2-ros \
        ros-humble-tf-transformations \
        ros-humble-rclpy \
        ros-humble-geometry2 \
        ros-humble-rviz2

    # 4. 安裝額外依賴
    log_info "[4/4] 安裝 pip 工具..."
    pip_install colcon-ros-bundle

    log_ok "ROS2 Humble 安裝完成"
}

# 驗證
verify() {
    log_step "驗證 ROS2 Humble..."
    if ! has_ros2; then
        log_error "驗證失敗：ROS2 Humble 未正確安裝"
        return 1
    fi

    # 嘗試 source 並取得版本
    # shellcheck source=/opt/ros/humble/setup.bash
    if source /opt/ros/humble/setup.bash 2>/dev/null; then
        if command -v ros2 &>/dev/null; then
            local version
            version=$(ros2 --version 2>/dev/null | head -1 || echo "unknown")
            log_ok "驗證成功: $version"
            return 0
        fi
    fi

    log_error "驗證失敗：無法執行 ros2 指令"
    return 1
}

# 移除
remove() {
    log_step "移除 ROS2 Humble..."
    require_root

    if confirm "確定要移除 ROS2 Humble？此操作無法復原。"; then
        DEBIAN_FRONTEND=noninteractive apt purge -y 'ros-humble-*'
        rm -rf /opt/ros/humble
        rm -f /etc/apt/sources.list.d/ros2.list
        apt autoremove -y
        log_ok "ROS2 Humble 已移除"
    else
        log_info "取消移除"
    fi
}

# ─── 入口 ───
# 用法：./install_ros2.sh [check|install|verify|remove]
main() {
    local action="${1:-check}"

    case "$action" in
        check)   check ;;
        install) install ;;
        verify)  verify ;;
        remove)  remove ;;
        *)
            echo "用法：$0 [check|install|verify|remove]"
            exit 1
            ;;
    esac
}

main "$@"