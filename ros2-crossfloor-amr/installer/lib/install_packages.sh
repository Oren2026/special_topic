#!/bin/bash
# install_packages.sh — ROS2 導航相關套件安裝
# 包括 Nav2、Slam-toolbox、robot_localization、BehaviorTree 等

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils.sh"
source "${SCRIPT_DIR}/detect.sh"

# ─── 核心套件清單 ───
CORE_PACKAGES=(
    # Nav2 導航框架
    ros-humble-nav2-msgs
    ros-humble-nav2-controller
    ros-humble-nav2-planner
    ros-humble-nav2-bluetooth-navigator
    ros-humble-nav2-behaviors
    ros-humble-nav2-bringup
    ros-humble-nav2-lifecycle-manager
    ros-humble-nav2-map-server
    ros-humble-nav2-costmap-2d
    ros-humble-nav2-velocity-smoother
    ros-humble-nav2-collision-monitor
    ros-humble-nav2-smoother

    # SLAM 建圖
    ros-humble-slam-toolbox

    # 感測器融合（IMU + 里程計）
    ros-humble-robot-localization

    # 座標轉換
    ros-humble-tf2-ros
    ros-humble-tf-transformations

    # 行為樹
    ros-humble-behaviortree-py
    ros-humble-behaviour-tree

    # 控制
    ros-humble-ros2-control
    ros-humble-ros2-action
    ros-humble-ros2-component-container

    # Launch & Utilities
    ros-humble-launch-xml
    ros-humble-launch-yaml
    ros-humble-xacro

    # 雷射雷達驅動（常見硬體）
    ros-humble-urgli
    ros-humble-rplidar-ros

    # IMU 驅動
    ros-humble-imu-tools
    ros-humble-imu-filter-madgwick

    # 訊息類型
    ros-humble-sensor-msgs
    ros-humble-geometry-msgs
    ros-humble-nav-msgs
    ros-humble-std-msgs
    ros-humble-std-srvs
    ros-humble-diagnostic-msgs
)

# ─── 安裝 ───
install() {
    log_step "安裝 ROS2 導航相關套件..."

    if ! has_ros2; then
        log_error "ROS2 未安裝，請先執行 install_ros2.sh"
        return 1
    fi

    # 1. 先 source ROS2 環境
    # shellcheck source=/opt/ros/humble/setup.bash
    source /opt/ros/humble/setup.bash

    # 2. 安裝所有套件
    log_info "[1/2] 安裝 ${#CORE_PACKAGES[@]} 個 ROS2 packages..."
    require_root
    DEBIAN_FRONTEND=noninteractive apt install -y "${CORE_PACKAGES[@]}"

    # 3. 安裝 Python 工具
    log_info "[2/2] 安裝 Python 工具..."
    pip_install \
        transforms3d \
        pyyaml \
        numpy

    log_ok "所有套件安裝完成"
    log_info "已安裝導航相關 packages: ${#CORE_PACKAGES[@]} 個"
}

# ─── 檢查 ───
check() {
    log_step "檢查導航套件安裝狀態..."

    if ! has_ros2; then
        log_warn "ROS2 未安裝"
        return 1
    fi

    # shellcheck source=/opt/ros/humble/setup.bash
    source /opt/ros/humble/setup.bash

    local missing=()
    local total=0
    local current=0

    for pkg in "${CORE_PACKAGES[@]}"; do
        ((total++))
        progress "$current" "$total" "檢查: $pkg"
        if ! has_ros_pkg "${pkg#ros-humble-}"; then
            missing+=("$pkg")
        fi
        ((current++))
    done

    echo ""
    if ((${#missing[@]} > 0)); then
        log_warn "缺少 ${#missing[@]} 個套件：${missing[*]}"
        return 1
    else
        log_ok "所有 ${#CORE_PACKAGES[@]} 個套件皆已安裝"
        return 0
    fi
}

# ─── 驗證 ───
verify() {
    log_step "驗證導航套件..."
    # shellcheck source=/opt/ros/humble/setup.bash
    if ! source /opt/ros/humble/setup.bash 2>/dev/null; then
        log_error "無法 source ROS2 環境"
        return 1
    fi

    local test_cmds=(
        "nav2_bringup"
        "slam_toolbox"
        "robot_localization"
        "bt_navigator"
    )

    for cmd in "${test_cmds[@]}"; do
        if command -v "$cmd" &>/dev/null; then
            log_ok "可用: $cmd"
        else
            log_warn "無法執行: $cmd"
        fi
    done

    log_ok "驗證完成"
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