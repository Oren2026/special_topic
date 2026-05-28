#!/bin/bash
# launcher.sh — 一鍵啟動完整模擬環境
# 用法：./launcher.sh [mode]
#
# 模式：
#   （無參數）  完整模擬環境（Nav2 + SLAM + Gazebo + RViz2）
#   nav         只啟動導航（已建圖）
#   slam        只啟動 SLAM 建圖
#   gazebo      只啟動 Gazebo
#   bringup     只啟動底層節點

set -euo pipefail

# ─── 顏色 ───
export COLOR_RESET='\033[0m'
export COLOR_GREEN='\033[0;32m'
export COLOR_CYAN='\033[0;36m'

# ─── 環境 ───
ROBOT_WS_DIR="${ROBOT_WS_DIR:-$HOME/ros2_ws}"
ROS2_SETUP="/opt/ros/humble/setup.bash"
WS_SETUP="$ROBOT_WS_DIR/install/setup.bash"
CROSSFLOOR_DIR="$ROBOT_WS_DIR/ros2-crossfloor-amr"

# ─── 訊息 ───
info() { echo -e "${COLOR_CYAN}[INFO]${COLOR_RESET} $*"; }
ok()   { echo -e "${COLOR_GREEN}[OK]${COLOR_RESET}   $*"; }

# ─── 檢查環境 ───
check_env() {
    local errors=0

    if [[ ! -f "$ROS2_SETUP" ]]; then
        echo -e "\033[0;31m[ERROR]\033[0m ROS2 Humble 未安裝"
        echo "請先執行：./install.sh"
        ((errors++))
    fi

    if [[ ! -f "$WS_SETUP" ]]; then
        echo -e "\033[0;31m[ERROR]\033[0m Workspace 未建立或未編譯"
        echo "請先執行：./install.sh 或 colcon build"
        ((errors++))
    fi

    if (( errors > 0 )); then
        echo ""
        echo "環境檢查失敗，請先完成安裝"
        exit 1
    fi
}

# ─── Source 環境 ───
source_env() {
    # shellcheck source=/opt/ros/humble/setup.bash
    source "$ROS2_SETUP"
    # shellcheck source=$HOME/ros2_ws/install/setup.bash
    if [[ -f "$WS_SETUP" ]]; then
        source "$WS_SETUP"
    fi
}

# ─── 啟動完整模擬 ───
launch_full() {
    info "啟動完整模擬環境..."
    info "包含：Nav2 + SLAM + Gazebo + RViz2"

    source_env

    # 啟動 Gazebo（背景）
    info "啟動 Gazebo..."
    # shellcheck source=gz-harmonic
    gz sim -r "$CROSSFLOOR_DIR/sim/worlds/office_floor1.sdf" &

    sleep 3

    # 啟動 SLAM
    info "啟動 SLAM Toolbox..."
    ros2 launch slam_toolbox online_async_launch.py \
        use_sim_time:=true \
        map_file_name:="$CROSSFLOOR_DIR/src/crossfloor_nav/maps/floor1.yaml" &

    sleep 2

    # 啟動 Nav2
    info "啟動 Nav2 導航框架..."
    ros2 launch nav2_bringup navigation_launch.py \
        use_sim_time:=true &

    sleep 2

    # 啟動 RViz2（可選）
    if command -v rviz2 &>/dev/null; then
        info "啟動 RViz2（視覺化）..."
        rviz2 -d "$CROSSFLOOR_DIR/src/crossfloor_nav/config/nav2_default_view.rviz" &
    fi

    ok "模擬環境已啟動！"
    echo ""
    echo "按 Ctrl+C 結束所有節點"
    wait
}

# ─── 只啟動導航 ───
launch_nav() {
    info "啟動 Nav2 導航（需已有地圖）..."
    source_env
    ros2 launch nav2_bringup navigation_launch.py use_sim_time:=true
}

# ─── 只啟動 SLAM ───
launch_slam() {
    info "啟動 SLAM 建圖..."
    source_env
    ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true
}

# ─── 只啟動 Gazebo ───
launch_gazebo() {
    info "啟動 Gazebo 模擬器..."
    if [[ -f "$CROSSFLOOR_DIR/sim/worlds/office_floor1.sdf" ]]; then
        gz sim -r "$CROSSFLOOR_DIR/sim/worlds/office_floor1.sdf"
    else
        gz sim
    fi
}

# ─── 只啟動 Bringup ───
launch_bringup() {
    info "啟動底層節點（雷達、IMU、馬達驅動）..."
    source_env
    ros2 launch crossfloor_nav bringup.launch.py
}

# ─── 主程式 ───
main() {
    check_env

    local mode="${1:-full}"

    echo ""
    echo -e "${COLOR_GREEN}╔═══════════════════════════════════════╗${COLOR_RESET}"
    echo -e "${COLOR_GREEN}║   Crossfloor AMR 啟動器               ║${COLOR_RESET}"
    echo -e "${COLOR_GREEN}╚═══════════════════════════════════════╝${COLOR_RESET}"
    echo ""

    case "$mode" in
        full)    launch_full ;;
        nav)     launch_nav ;;
        slam)    launch_slam ;;
        gazebo)  launch_gazebo ;;
        bringup) launch_bringup ;;
        *)
            echo "用法：$0 [full|nav|slam|gazebo|bringup]"
            echo ""
            echo "模式："
            echo "  full    完整模擬環境（預設）"
            echo "  nav     只啟動 Nav2 導航"
            echo "  slam    只啟動 SLAM 建圖"
            echo "  gazebo  只啟動 Gazebo"
            echo "  bringup 只啟動底層節點"
            exit 1
            ;;
    esac
}

main "$@"