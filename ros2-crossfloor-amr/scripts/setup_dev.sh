#!/bin/bash
# setup_dev.sh — ROS2 Crossfloor AMR 開發環境一次性安裝腳本
# 適用：Ubuntu 22.04（原生或 WSL2）
# 使用方式：bash scripts/setup_dev.sh

set -e

echo "=========================================="
echo "ROS2 Humble 開發環境安裝"
echo "=========================================="

# 1. 更新系統
echo "[1/7] 更新系統套件..."
sudo apt update && sudo apt upgrade -y

# 2. 安裝基本依賴
echo "[2/7] 安裝基本依賴..."
sudo apt install -y \
    curl \
    git \
    gnupg2 \
    lsb-release \
    software-properties-common \
    build-essential \
    cmake \
    pkg-config \
    libssl-dev \
    libgl1-mesa-glx \
    libglib2.0-dev \
    libavcodec-dev \
    libavformat-dev \
    libeigen3-dev \
    python3-colcon-common-extensions \
    python3-pip \
    python3-venv \
    python3-dev \
    libyaml-cpp-dev

# 3. 加入 ROS2 Humble 源
echo "[3/7] 加入 ROS2 Humble 軟體源..."
if [ ! -f /etc/apt/sources.list.d/ros2.list ]; then
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key | sudo apt-key add -
    sudo sh -c 'echo "deb [arch=$(dpkg --print-architecture)] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" > /etc/apt/sources.list.d/ros2.list'
    sudo apt update
fi

# 4. 安裝 ROS2 Humble
echo "[4/7] 安裝 ROS2 Humble..."
sudo apt install -y \
    ros-humble-ros-base \
    ros-humble-angles \
    ros-humble-nav2-* \
    ros-humble-slam-toolbox \
    ros-humble-robot-localization \
    ros-humble-behaviortree-* \
    ros-humble-ros2-control \
    ros-humble-ros2-action \
    ros-humble-launch-xml \
    ros-humble-xacro

# 5. 安裝 Gazebo（Harmonic）
echo "[5/7] 安裝 Gazebo Harmonic..."
if ! command -v gz &> /dev/null; then
    sudo wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo.list > /dev/null
    sudo apt update
    sudo apt install -y gz-harmonic
fi

# 6. 環境變數寫入 bashrc
echo "[6/7] 設定環境變數..."
ROS2_SETUP='
# ROS2 Humble
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=42
'
if ! grep -q "ROS2 Humble" ~/.bashrc; then
    echo "$ROS2_SETUP" >> ~/.bashrc
fi

# 7. 建立 colcon workspace
echo "[7/7] 建立 colcon workspace..."
cd "$(dirname "$0")/.."
mkdir -p src
if ! command -v colcon &> /dev/null; then
    pip3 install colcon-common-extensions
fi

echo ""
echo "=========================================="
echo "安裝完成！請執行以下指令："
echo ""
echo "  source ~/.bashrc"
echo "  colcon build"
echo "=========================================="