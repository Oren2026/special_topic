#!/bin/bash
# pull_updates.sh — 異地同步並編譯
# 使用方式：bash scripts/pull_updates.sh

set -e

cd "$(dirname "$0")/.."

echo "=========================================="
echo "同步 ROS2 專案"
echo "=========================================="

# Pull latest from GitHub
git pull origin ros2-crossfloor-amr

# Source ROS2
source /opt/ros/humble/setup.bash

# Build
colcon build --symlink-install

echo ""
echo "同步完成！"