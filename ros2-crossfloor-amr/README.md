# ROS2 跨樓層 AMR 自主導航系統

> 基於 ROS 2 Humble 的非基礎設施依賴型跨樓層 AMR 自主導航系統

## 📋 專題資訊

- **年度**：115 學年度
- **題目**：基於 ROS 2 的非基礎設施依賴型跨樓層 AMR 自主導航系統開發
- **成員**：黃信惟（組長）、馮至豪、張庭亞
- **指導老師**：待填寫

## 🏗️ 系統架構

```
src/
├── crossfloor_nav/       # 主導航 package（Navid2 + SLAM）
├── imu_filter/          # IMU 垂直狀態估測器
├── elevator_sm/         # 電梯狀態機（Lifecycle Node）
├── multi_map_manager/   # 多地圖動態熱切換
└── behavior_tree/       # 行為樹決策層
```

## 🔧 環境需求

- **OS**：Ubuntu 22.04（WSL2 / VM）
- **ROS2**：Humble Hawksbill
- **Gazebo**：Harmonic（模擬）
- **RAM**：8GB+（VM）

## 🚀 快速開始

```bash
# 進入 workspace
cd ros2-crossfloor-amr

# 安裝依賴（Ubuntu 22.04）
./scripts/setup_dev.sh

# 編譯
./scripts/build_all.sh

# 測試模擬環境
ros2 launch crossfloor_nav simulation.launch.py
```

## 📁 目錄結構

```
ros2-crossfloor-amr/
├── docs/               # 文件、會議紀錄
├── src/               # ROS2 packages
├── sim/               # Gazebo 模擬環境
├── scripts/           # 工具腳本
└── .devcontainer/     # VS Code Remote Container
```

## 📅 進度規劃

### 第一學期（期中 KPI）
- [ ] 多樓層資料結構設計
- [ ] 演算法開發
- [ ] 多地圖管理節點核心框架
- [ ] 進出電梯基礎控制邏輯
- [ ] 節點編譯與測試

### 第一學期（期末 KPI）
- [ ] 建構 Gazebo 模擬環境
- [ ] 模擬環境中單層樓 SLAM 建圖
- [ ] 軟體系統整合
- [ ] 模擬環境跨樓層導航測試
- [ ] 地圖切換延遲與定位成功率評估

### 第二學期（期中 KPI）
- [ ] 實體車硬體平台架設
- [ ] 參數調校與數據採集
- [ ] 地圖掃描與量測記錄
- [ ] 移植至實體車控制器
- [ ] 軟硬體測試

### 第二學期（期末 KPI）
- [ ] 實體車系統整合與優化
- [ ] 動態異常調校
- [ ] 實地連續跨樓層導航測試
- [ ] 效能評估與數據分析

## 🔗 相關資源

- [ROS2 Humble 文件](https://docs.ros.org/en/humble/)
- [Nav2 官方文檔](https://navigation.ros.org/)
- [Gazebo Simulator](https://gazebosim.org/)
- [Behavior Tree Coroutines](https://www.behaviortree.dev/)

## 📄 授權

MIT License