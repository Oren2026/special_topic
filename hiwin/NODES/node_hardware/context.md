# node_hardware — 手臂 + 擊球機構整合節點

## 職責
確認 `hiwin_arm.py` 和 `striker_bridge.py` 的 stub 實作完整，確保在沒有真實硬體時可以 MOCK 模式運行。

## 現況檢查清單

### `hiwin_arm.py` 必要 API
- [ ] `__init__(mock=True)` — 支援 mock 模式
- [ ] `connect()` — 連線（mock 直接成功）
- [ ] `disconnect()` — 斷線
- [ ] `home(wait=True)` — 歸零
- [ ] `move_to(x, y, z, c, wait=True)` — 直線移動
- [ ] `move_z_for_cue_alignment(x, y, z_target, c)` — Z軸對準
- [ ] `lift_after_shot(x, y, z_safe, c)` — 擊球後抬起

### `striker_bridge.py` 必要 API
- [ ] `__init__(port, baud, timeout, mock=True)` — 支援 mock 模式
- [ ] `connect()` — 連線（mock 直接成功）
- [ ] `disconnect()` — 斷線
- [ ] `execute(robot_tcp, stroke_dist, angle) -> bool` — 執行擊球

## 檢查結果
（由 subagent 填寫）