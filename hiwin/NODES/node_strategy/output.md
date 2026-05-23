# Node: node_strategy — output

**更新**: 2026-05-23  
**狀態**: ✅ 已整合（Bank Shot + obstacles 已串接）

---

## 產出摘要

Ghost Ball + Bank Shot 策略計算已完成，94 tests PASS。  
`_handle_manual` 已整合 `compute_shot(obstacles)`，障礙物格式確認與 `vision_pipeline.get_obstacles()` 一致。

---

## 已實作功能

### Ghost Ball 計算
- ✅ `strategy_module._ghost_pos()`：G = T + normalize(P-T) × D（38mm）
- ✅ 與口袋同側驗證（dot > 0 = direct, dot < 0 = bank）

### Bank Shot Planner
- ✅ 鏡像法計算 4 條庫邊反彈候選
- ✅ 雙條件觸發：C→G 被阻 **OR** T→P 被阻
- ✅ Strict Mode：C→ref **且** ref→G 皆無障礙
- ✅ 障礙物 threshold = ball_d × 1.5 = 57mm（ray-circle + perpendicular fallback）

### 障礙物整合
- ✅ `compute_shot(cue, target, pocket, obstacles)` 接口
- ✅ `wsl/robot_brain._handle_manual()` 已呼叫 obstacles 參數
- ✅ `wsl/protocol.py` 新增 `TYPE_OTHER_BALL` 定義

---

## 整合確認

### 障礙物格式對接
```
vision_pipeline.get_obstacles() → [{"x": x_mm, "y": y_mm}, ...]
                                        ↓
                              BankShotPlanner.compute_shot(obstacles)
                                        ↓
                              _handle_manual 解析 TYPE_OTHER_BALL
```

### _handle_manual 變更（wsl/robot_brain.py）
- 新增障礙球解析：`for p in vision_data if p[P.FIELD_TYPE] == P.TYPE_OTHER_BALL`
- `compute_shot(obstacles=obstacles)` 已取代原本的 `obstacles=[]`
- `_validate_cue_hits_target(obstacles=obstacles)` 已更新

### protocol.py 新增
- `TYPE_OTHER_BALL = "OTHER_BALL"` — 標記障礙球

---

## 測試覆蓋

| 測試檔案 | 狀態 | 說明 |
|----------|------|------|
| `tests/test_bank_shot_planner.py` | ✅ 32/32 PASS | Bank Shot 單元測試 |
| `tests/test_physics_validation.py` | ✅ 10/10 PASS | 物理驗證 |
| `tests/test_vision.py` | ✅ 14/14 PASS | 視覺系統 |

**總測試數**: 94/94 PASS（2026-05-09）

---

## 口袋座標（POCKETS）

```python
{
    "top_left":   (-578.5,  53.5),
    "top_right":  ( 578.5,  53.5),
    "bot_left":   (-578.5, 576.5),
    "bot_right":  ( 578.5, 576.5),
    "side_left":  (-575.0, 315.0),
    "side_right": ( 575.0, 315.0),
}
```

---

## 備註

- 原點 (0,0) = 球檯幾何左下角（不是手臂原點）
- 長邊（1200mm）在上下側，短邊（630mm）在左右側
- 策略模組位於 `windows/brain/strategy_module.py` + `bank_shot_planner.py`