# HIWIN 撞球機器人 — 待辦追蹤

> 更新日期：2026-05-05
> 現況：Bank Shot Planner 已實作 + Unit Tests ✅
> 複審截止：2026-05-22

---

## 📅 複審前作戰時程

```
Phase 1 (現在)   Phase 2 (中期)   Phase 3 (後期)
  │                 │               │
  ├─ 圓形偵測        ├─ 單一擊打      ├─ 物理參數
  ├─ 顏色分類        └─ 障礙判斷     ├─ 側邊相機
  ├─ 9號球順序       └─ 力度估算     └─ 係數微調
  │
  └──────────────────────────► 5/22 複審
```

---

## ✅ 已完成

| 日期 | 項目 | 備註 |
|------|------|------|
| 2026-05-05 | Ghost ball 口袋動態查詢 | `_find_nearest_pocket_name()` pixel→mm→比對6口袋 |
| 2026-05-05 | 擊球後多餘點擊修復 | commit cf66885，_shot_sent flag + 球桌外重置 |
| 2026-05-05 | Bank Shot Planner | 鏡像法計算4條庫邊反彈點，commit 2d97853 |
| 2026-05-05 | Bank Shot Unit Tests ✅ | 32/32 通過，commit d67c729 |

---

## 🔴 高優先級

### 1. 擊球後多餘點擊 ✅ 已修復（cf66885）
**症狀**：TEST 模式三球完成後，每次點擊都重複送同一個 task_id=1001
**修法**：
- `_shot_sent` flag 區分「剛完成（第一次）」vs「已經完成（重複點擊）」
- 訊息區分：第一次顯示「擊球任務已發送！」，重複顯示「已完成，可拖曳調整，或點空白處重新布置」
- BREAK 模式同樣保護

### 2. 口袋直徑 & 開口夾角確認 + SimTable 模型
**現況**：`strategy_module.POCKETS` 使用假設座標，校正後口袋計算可能與實際不符
**問題**：
- `TABLE_WIDTH/TABLE_HEIGHT` 是**外框尺寸（含庫邊）**，口袋位於庫邊內側
- 角落口袋的兩庫邊夾角通常 **≠ 90°**（視檯面而定）
- 側邊口袋位置並非精確認證
**已建立**：
- `sim_table.py`：模擬球檯幾何模型（預設參數：洞口50mm、倒角105°、rail寬50mm）
- `calibration_plus.py`：校正增強（可呼叫 `compute_expected_pockets()` 視覺化口袋位置）
**需要確認**：
- 洞口直徑（洞口實際大小）
- 角落口袋：兩庫邊的**實際夾角**
- 側邊口袋：在長邊的**實際位置**（Y 座標）
**Ghost Ball 偏移量** = `球半徑 + 口袋半徑`，夾角影響鬼球計算方向

### 3. WSL IP 更新到 windows/config.py
**症狀**：`windows/config.py` 的 `SOCKET_HOST` 尚未更新為 WSL IP
**詳見**：`windows/config.py` 內註解待確認

---

## 🟡 中優先級

### 4. COMPETE 模式（自動視覺辨識）

**🔴 Phase 1：影像辨識介面（現在開始）**

目標：建立 `windows/control/vision_pipeline.py` + `ball_identifier.py` + `calibration_control.py`

流程：
```
攝影機畫面
    │
    ▼
HoughCircles 偵測圓形（形狀優先）
    │
    ▼
顏色分割（HSV Hue 範圍）
    │
    ▼
Ball 物件 {position, color, number, is_stripe}
    │
    ▼
sort_by_number() → 過濾出最小號碼
    │
    ▼
Strategy Module 接收 {target_ball, cue_ball, pocket}
```

9號球顏色對照（Hue 範圍，HSV）：
| 球號 | 顏色 | Hue 範圍 |
|------|------|----------|
| 1 | 黃色 | ~25-35 |
| 2 | 藍色 | ~100-130 |
| 3 | 紅色 | ~0-15 或 170-180 |
| 4 | 紫色 | ~130-160 |
| 5 | 橙色 | ~10-25 |
| 6 | 綠色 | ~45-75 |
| 7 | 栗色/褐紅 | ~0-10 (暗紅) |
| 8 | 黑色 | ~0-180 (亮度判斷) |
| 9 | 條紋黃 | 同1但條紋圖案 |

條紋判斷：邊緣 vs 中心亮度差 > 30

**🟡 Phase 2：簡單策略（單一擊打）**

目標：單一擊打版本（像校正測試那樣）
- 輸入：目標球、白球、6個口袋
- 邏輯：白球→目標球→口袋 夾角最小者
- 考慮障礙球遮蔽（直線障礙）

**🟢 Phase 3：參數預留空間**

目標：架構開好，後期擴充不影響現有功能

```python
class StrategyConfig:
    # 擊球選擇權重
    WEIGHT_DISTANCE = 0.3        # 口袋距離
    WEIGHT_ANGLE = 0.4           # 擊球角度難易度
    WEIGHT_OBSTRUCTION = 0.3    # 障礙球阻擋程度

    # 物理參數（後期微調用）
    FRICTION_COEFFICIENT = 0.2   # 桌面摩擦
    CUSHION_REBOUND = 0.75       # 庫邊反彈係數
    SIDE_CAMERA_OFFSET = 0      # 側邊相機擊球點 offset
```

### 5. 擊球後場景重置
**需求**：點擊球桌外空白區域 → 清除 scene，重置為可重新布置

### 6. 校正資料持久化
**需求**：校正矩陣寫入 JSON，斷電重啟後無需重新校正

### 7. 校正完成後畫面
**需求**：校正完成時，6 口袋顯示在正確位置，TEST 模式提示使用者布置球

---

## 🟢 低優先級（未來擴展）

| 項目 | 說明 |
|------|------|
| 多口袋候選線 | Phase 2，一次顯示 6 條可行路徑，顏色分組 |
| 開球多方向 | BREAK angle 目前固定 90°，支援多方向 |
| 側邊相機擊球點確認 | 第二顆鏡頭側邊確認白球擊球位置 |
| 策略學習層 | 貝氏估計 / 強化學習權重 |
| striker_bridge Arduino 通訊 | 實機擊球控制（`STRIKER_MOCK_MODE = False`）|

---

## 🐛 已知問題

| ID | 問題 | 預計修法 |
|----|------|----------|
| #001 | 藍色圈圈「???」出現在某些點擊後 | 小問題，待重現確認 |

---

## 📋 模式責任定義

| 模式 | 責任 |
|------|------|
| **INSTALL（校正）** | 收集 4 點 → 計算透視矩陣 → 建立 pixel↔mm 映射 |
| **TEST（模擬擊球）** | 校正完成後 → 點擊 2 球（目標球+白球）→ Ghost Ball 路線試算；點擊口袋 → 重新試算；點擊球桌外 → 重置布置 |
| **BREAK（開球）** | 只點白球 → angle=90°, stroke=MAX → 開球堆 |
| **COMPETE（自動）** | 視覺形狀先於顏色 → 自動分球 → 策略排序 → 依序執行 |

---

## 技術債

- `strategy_module._calc_stroke()`：變量衝程公式待驗證（`accel_dist_limit` 未使用）
- `windows/vision/objects.py`：口袋徑從 45→50mm 已修正，確認比例尺計算正確
- 口袋 pixel 匹配閾值：100mm 是合理值，但待實際校正後驗證
