# Node: node_physics — output

**更新**: 2026-05-23
**狀態**: ✅ 已修復（advance_count bug）

---

## 產出摘要

物理模擬引擎修復了 `chain_simulate` 的 advance_count bug（while 迴圈先檢查 spd<0.5 再 skip advance，導致最後一輪未被執行）。修復後 chain_simulate 與 predict_single advance_count 一致（皆為 2000 步）。

---

## 現有功能

### predict_single
- ✅ 單球軌跡預測（摩擦 + 庫邊 + 靜態障礙球碰撞查詢）
- ✅ 停止位置、累計距離、牆壁反彈次數
- ✅ 碰撞事件查詢（collision_before_stop）
- ✅ advance_count = 2000

### chain_simulate
- ✅ 多球碰撞鏈式模擬
- ✅ 球-球彈性碰撞（RESTITUTION）
- ✅ 庫邊反射 + WallHit 記錄
- ✅ 進袋偵測（pocket_sunk, pocket_sunk_ball）
- ✅ advance_count = 2000（修復後，與 predict_single 一致）
- ✅ stop position = (819.8, 315)（與 predict_single 一致，差距 < 5mm）

---

## 驗證資料（2026-05-23）

### 直線右實驗
```
輸入：
  cue_pos = (200, 315)
  cue_dir = (1, 0)
  speed = 3000 mm/s
  target_pos = (600, 315)
  pocket_pos = (1150, 315)

predict_single 輸出：
  stop = (819.8, 315)
  dist = 18980mm
  bounces = 17
  advance_count = 2000

chain_simulate 輸出（修復後）：
  stop = (819.8, 315)
  dist = 18980mm
  bounces = 17
  advance_count = 2000

差距：< 5mm / 0 步 ✅
```

### Bug 根因
`trajectory.py:619-643` while 迴圈中：
- 錯誤：`spd < 0.5` → skip advance → `any_moving=False`（損失最後一輪）
- 正確：advance → 檢查 `spd < 0.5` → break（advance 後才檢查，輸出 advanced 後位置）

---

## 測試覆蓋

| 測試檔案 | 狀態 | 說明 |
|----------|------|------|
| `tests/test_physics_validation.py` | ✅ 10/10 PASS | 物理參數驗證 |
| `tests/test_physics.py` | ✅ 25/25 PASS | 碰撞偵測、反射、進袋 |

---

## 備註

- RESTITUTION = 0.95（來自撞球檯文獻）
- ROLLING_FRICTION = 150 mm/s²（文獻值，待空杆實驗驗證）
- DT_MS = 10（每步 10ms）
- 物理模組位於 `physics/`（與 hiwin 專案平行，獨立維護）