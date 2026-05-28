#!/bin/bash
# install.sh — ROS2 Crossfloor AMR 一鍵安裝腳本
# 用法：
#   curl 安裝：bash -c "$(curl -sL https://.../install.sh)"
#   本地下載：chmod +x install.sh && ./install.sh
#
# 支援參數：
#   install.sh          互動式完整安裝
#   install.sh check   僅檢測環境
#   install.sh dry-run  測試模式（不下載不安裝）
#   install.sh update   更新並重建

set -euo pipefail

# ─── 全域設定 ───
export INSTALLER_VERSION="0.1.0"
export INSTALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LOGFILE="/tmp/ros2_install_$(date +%Y%m%d_%H%M%S).log"

# ─── 載入工具 ───
# shellcheck source=lib/utils.sh
source "${INSTALLER_DIR}/lib/utils.sh"
# shellcheck source=lib/detect.sh
source "${INSTALLER_DIR}/lib/detect.sh"

# ─── Banner ───
show_banner() {
    echo -e "${COLOR_BOLD}${COLOR_CYAN}"
    cat << 'EOF'
    ╔═══════════════════════════════════════════╗
    ║   ROS2 Crossfloor AMR 安裝程式            ║
    ║   跨樓層自主移動機器人導航系統             ║
    ║   Version: 0.1.0                          ║
    ╚═══════════════════════════════════════════╝
EOF
    echo -e "${COLOR_RESET}"
    echo ""
}

# ─── 顯示用法 ───
show_usage() {
    cat << EOF
用法：$0 [模式]

模式：
  （無參數）    互動式完整安裝嚮導
  check         僅檢測環境，不進行任何安裝
  dry-run       測試模式，顯示會做什麼但不下載不安裝
  update        從 GitHub 拉取更新並重建
  verify        驗證已安裝的環境是否正常
  uninstall     移除所有已安裝的元件

範例：
  # 互動式安裝
  ./install.sh

  # 檢測環境
  ./install.sh check

  # 測試模式
  ./install.sh dry-run

  # 遠端安裝（curl）
  bash -c "\$(curl -sL https://raw.githubusercontent.com/Oren2026/special_topic/ros2-crossfloor-amr/installer/install.sh)"
EOF
}

# ─── 互動式安裝嚮導 ───
interactive_install() {
    show_banner

    echo -e "${COLOR_BOLD}開始環境檢測...${COLOR_RESET}"
    echo ""

    # 前置檢查
    check_environment

    echo ""
    if ! confirm "是否開始安裝？"; then
        log_info "取消安裝"
        exit 0
    fi

    # 1. ROS2
    echo ""
    if confirm "是否安裝 ROS2 Humble？（已存在會跳過）"; then
        "${INSTALLER_DIR}/lib/install_ros2.sh" install
    fi

    # 2. Gazebo
    echo ""
    if confirm "是否安裝 Gazebo Harmonic？（已存在會跳過）"; then
        "${INSTALLER_DIR}/lib/install_gazebo.sh" install
    fi

    # 3. 導航套件
    echo ""
    if confirm "是否安裝導航相關套件（Nav2、Slam-toolbox 等）？（已存在會跳過）"; then
        "${INSTALLER_DIR}/lib/install_packages.sh" install
    fi

    # 4. Workspace
    echo ""
    if confirm "是否設定 Workspace 並 Clone 程式碼？"; then
        "${INSTALLER_DIR}/lib/setup_workspace.sh" install
        "${INSTALLER_DIR}/lib/setup_workspace.sh" bashrc
    fi

    echo ""
    report "success" "
✅ 安裝完成！

請執行以下指令啟用環境：
    source ~/.bashrc
    cdr

啟動模擬環境：
    ros2 launch crossfloor_nav simulation.launch.py

詳細 log：$LOGFILE
"
}

# ─── 檢測模式 ───
mode_check() {
    show_banner
    check_environment
}

# ─── 測試模式 ───
mode_dry_run() {
    show_banner
    log_info "測試模式：顯示將要執行的操作"
    echo ""

    local checks=(
        "檢查 OS 版本（需 Ubuntu 22.04）"
        "檢查網路連線（需連線至 GitHub、ROS2 套件庫）"
        "檢查磁碟空間（建議 30GB+）"
        "檢查系統記憶體（建議 8GB+）"
        "若缺少相依，顯示將安裝的套件清單"
    )

    echo -e "${COLOR_BOLD}此模式將執行以下檢查：${COLOR_RESET}"
    for i in "${!checks[@]}"; do
        echo "  $((i+1)). ${checks[$i]}"
    done

    echo ""
    if ! has_ros2; then
        echo -e "  → 將安裝：ROS2 Humble（約 2GB）"
    fi
    if ! has_gazebo; then
        echo -e "  → 將安裝：Gazebo Harmonic（約 500MB）"
    fi

    echo ""
    log_ok "測試模式完成，實際未執行任何安裝"
}

# ─── 更新模式 ───
mode_update() {
    show_banner
    log_step "更新程式碼並重建..."
    "${INSTALLER_DIR}/lib/setup_workspace.sh" update
    echo ""
    report "success" "✅ 更新完成！"
}

# ─── 驗證模式 ───
mode_verify() {
    show_banner
    log_step "驗證環境..."

    local all_ok=true

    "${INSTALLER_DIR}/lib/install_ros2.sh" verify || all_ok=false
    "${INSTALLER_DIR}/lib/install_gazebo.sh" verify || all_ok=false
    "${INSTALLER_DIR}/lib/install_packages.sh" verify || all_ok=false

    if "$all_ok"; then
        report "success"
    else
        report "failed" "部分驗證未通過，請執行完整安裝"
        exit 1
    fi
}

# ─── 解除安裝模式 ───
mode_uninstall() {
    show_banner
    log_step "解除安裝..."

    if ! confirm "確定要移除所有已安裝的元件？"; then
        log_info "取消解除安裝"
        exit 0
    fi

    log_warn "移除 Workspace..."
    "${INSTALLER_DIR}/lib/setup_workspace.sh" remove

    if confirm "是否同時移除 ROS2 Humble？"; then
        "${INSTALLER_DIR}/lib/install_ros2.sh" remove
    fi

    if confirm "是否同時移除 Gazebo Harmonic？"; then
        require_root
        apt purge -y gz-harmonic gz-sim7 gz-tools
        log_ok "Gazebo 已移除"
    fi

    echo ""
    report "success" "解除安裝完成"
}

# ─── 主程式 ───
main() {
    local mode="${1:-install}"

    echo "Log 檔案：$LOGFILE"
    echo ""

    case "$mode" in
        check)     mode_check ;;
        dry-run)   mode_dry_run ;;
        update)    mode_update ;;
        verify)    mode_verify ;;
        uninstall) mode_uninstall ;;
        install)   interactive_install ;;
        -h|--help|help) show_usage ;;
        *)
            log_error "未知模式：$mode"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"