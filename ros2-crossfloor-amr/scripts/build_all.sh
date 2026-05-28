#!/bin/bash
# build_all.sh — 編譯所有 ROS2 packages

set -e

cd "$(dirname "$0")/.."

echo "=========================================="
echo "編譯 ros2-crossfloor-amr"
echo "=========================================="

# source ROS2 environment
source /opt/ros/humble/setup.bash

# Build all packages
colcon build --symlink-install

echo ""
echo "=========================================="
echo "編譯完成！"
echo ""
echo "測試來源：source install/setup.bash"
echo "=========================================="