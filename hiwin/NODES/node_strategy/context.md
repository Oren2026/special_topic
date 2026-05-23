# Node: node_strategy

**父節點**: node_vision（提供 balls + obstacles）  
**子節點**: node_hardware（輸出 robot_tcp + stroke_dist）  
**創建日期**: 2026-05-23

---

## 職責

擊球策略計算，負責：
- Ghost Ball 瞄點計算
- Bank Shot 庫邊反彈路徑規劃
- 手臂可達性判斷
- 擊球參數輸出（angle, stroke_dist, robot_tcp）

---

## 邊界

**負責**:
- Ghost Ball 幾何計算（G = T + normalize(P-T) × D）
- 障礙物路徑阻斷判斷
- Bank Shot 鏡像法計算
- 瞄準方向與擊球力道

**不負責**:
- 視覺辨識（依賴 node_vision）
- 硬體控制（輸出給 node_hardware）
- 物理模擬驗證（呼叫 node_physics）

---

## 輸入格式

```python
# 來自 node_vision/output.md
{
    "balls": [
        {"type": "CUE_BALL", "x": 300, "y": 315},
        {"type": "TARGET_BALL", "x": 600, "y": 315},
        {"type": "OBSTACLE", "x": 450, "y": 300}
    ],
    "obstacles": [{"x": 450, "y": 300}, ...],
    "cue_ball": {"x": 300, "y": 315},
    "next_target": {"type": "TARGET_BALL", "x": 600, "y": 315}
}

# 來自 node_physics/OUTPUT.md（驗證）
TrajectoryResult { cue_path, collision_events, pocket_sunk }
```

---

## 輸出格式

```python
{
    "type": "direct" | "bank",
    "ghost": (gx, gy),          # Ghost Ball 位置（mm）
    "robot_tcp": (rx, ry),      # 手臂目標座標（mm）
    "angle": float,             # 擊球角度（度）
    "stroke_dist": float,       # 擊球行程（mm）
    "is_reachable": bool,        # 手臂可達性
    "reflection_point": (rx, ry) # Bank Shot 反彈點（bank 時）
}
```

---

## 觸發條件

- node_vision 完成辨識後自動呼叫
- 使用者點擊球檯（TARGET → CUE → POCKET）時
- COMPETE 模式自動執行

---

## 錯誤處理

- **失敗時找誰**: 回歸主 agent
- **重試次數**: 3 次
- **備用方案**: 若 bank shot 計算失敗，回退 direct shot

---

## 已知缺口（委派依據）

### Bank Shot 整合未完成
- `compute_shot(obstacles)` 已實作但 `robot_brain._handle_manual` 未串接
- `ref→G` strict mode 未啟動
- 檔案：`windows/brain/bank_shot_planner.py`

### 障礙物Filter
- `_filtered_obstacles()` 邏輯已實作，需確認與 `vision_pipeline.get_obstacles()` 格式一致

---

## 驗證方法

```bash
cd ~/Desktop/special_topic/hiwin
python -m pytest tests/test_bank_shot_planner.py -v
# 目標：32/32 PASS
```