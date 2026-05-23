# node_integration — Windows-Only 整合節點

## 職責
將 HIWIN 撞球機器人重構為 **純 Windows-Only 架構**，移除 WSL 依賴。

## 目標架構
```
windows/main.py
├── HMI()              # Tkinter UI
└── RobotBrain()       # 決策核心（同一進程）
    ├── strategy_module
    ├── bank_shot_planner
    ├── coord_manager
    ├── hiwin_arm (stub)
    └── striker_bridge (stub)
```

## 現況（待移除）
- `wsl/` — 整個資料夾即將廢除
- `windows/control/socket_client.py` — 移除
- `windows/main.py` — 目前只啟動 HMI，需要同時啟動 RobotBrain

## 具體工作

### 1. 更新 `windows/main.py`
```python
# 新增：啟動 RobotBrain
from brain.robot_brain import RobotBrain

if __name__ == "__main__":
    brain = RobotBrain()
    brain.start()          # 連線手臂 + 擊球機構
    app = HMI(brain)       # 傳入 brain
    app.run()
```

### 2. 更新 `windows/control/hmi.py`
- `__init__(self, brain: RobotBrain = None)` — 接收 brain injection
- 移除 `self._socket = SocketClient()` + `.connect()` + `._on_wsl_message`
- 移除 `self._socket.on_message(...)` 訂閱
- 點擊事件直接呼叫 `self._brain.compute_and_execute_shot(...)` 而非 `SocketClient.send()`
- 校正事件直接呼叫 `self._brain.calibrate(points)`

### 3. 更新 `windows/control/state_machine.py`
- 移除所有 `SocketClient` import 和實例
- Handler 完成後直接 call brain API，回傳結果
- 不再等待 WSL socket 回應

### 4. 刪除 socket client（備份到 `wsl/` 目錄下）
- `windows/control/socket_client.py` → 搬至 `wsl/backup_socket_client.py`

### 5. 驗證
```bash
cd ~/Desktop/special_topic/hiwin
python windows/main.py
```
→ GUI 視窗出現，點擊「打球測試」能正常運作

## 約束
- 不修改 `windows/brain/robot_brain.py`（已完整）
- 不修改 `physics/`（已完整）
- 破壞性變更前先 `git commit`