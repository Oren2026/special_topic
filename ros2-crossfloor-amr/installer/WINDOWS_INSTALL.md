# Windows 一鍵安裝說明

## 方式一：直接雙擊（最簡單）

1. **安裝 Python（如果還沒有）**
   - 下載：https://www.python.org/downloads/
   - 安裝時務必勾選 ✅ **Add Python to PATH**

2. **雙擊執行**
   ```
   雙擊 crossfloor_setup.bat
   ```
   或
   ```
   雙擊 crossfloor_setup.py
   ```

3. **等待完成**
   - 第一次執行會需要系統管理員權限（跳出提示，選「是」）
   - WSL2 + Ubuntu 22.04 安裝約 5-10 分鐘
   - ROS2 + Gazebo + 套件安裝約 30-60 分鐘
   - 請保持網路連線

---

## 方式二：封裝成 .exe（方便散發給隊友）

```bash
# 安裝 pyinstaller
pip install pyinstaller

# 封裝成單一 exe（約 10-20MB）
pyinstaller --onefile --windowed crossfloor_setup.py
```

封裝完成後的 `crossfloor_setup.exe` 可以直接分發給隊友，無需安裝 Python。

---

## 安裝流程

```
雙擊 crossfloor_setup.bat
        ↓
   檢查管理員權限
        ↓
   檢查 WSL2 是否啟用
        ↓（未啟用）
   自動啟用 WSL2 功能 → 需要重開機
        ↓
   檢查 Ubuntu 22.04 是否安裝
        ↓（未安裝）
   自動安裝 Ubuntu 22.04
        ↓
   Clone GitHub Repo
        ↓
   執行 ROS2 + Gazebo 安裝腳本
        ↓
   ✅ 完成
```

---

## 預期輸出

- WSL2 + Ubuntu 22.04 LTS
- ROS2 Humble Hawksbill
- Gazebo Harmonic
- Nav2、Slam-toolbox、robot_localization、BehaviorTree
- 本專案 workspace (`~/ros2_ws/ros2-crossfloor-amr/`)

---

## 常見問題

**Q：跳出「需要系統管理員權限」？**
→ 選「是」，這是正常的，因為要啟用 WSL2 功能。

**Q：出現 `python: command not found`？**
→ 確認 Python 已安裝且有勾選「Add Python to PATH」，然後重新開一個 CMD 視窗再試。

**Q：最後出現錯誤？**
→ 把螢幕截圖傳給組長，可能是網路問題或 Antivirus 阻擋。

**Q：可以中斷嗎？**
→ 可以。程式支援中斷後重新執行，已安裝的部分會自動跳過。