# 🎲 骰子比大小遊戲（RandomRace Dice Game）

A two-player dice rolling game built with C# Windows Forms.

---

## 遊戲說明 | Game Overview

**類型**：雙人骰子對戰遊戲
**功能**：兩位玩家同時擲骰，點數大者獲勝

---

## 技術規格 | Technical Specs

| 項目 | 規格 |
|------|------|
| 語言 | C# |
| 框架 | Windows Forms (.NET 10) |
| 開發環境 | Visual Studio 2022+ / VS Code |
| 圖片格式 | PNG（Dice_Images 目錄） |

---

## 遊戲功能 | Features

### 🎯 核心玩法
- 點擊「擲骰子！」按鈕，兩位玩家同時隨機擲出 1~6 點
- 點數大者獲勝，平手則顯示平手

### 🎨 三種骰子風格
| 風格 | 說明 |
|------|------|
| Classic | 經典骰子設計 |
| Neon | 霓虹風格 |
| Gold | 金色奢華風格 |

每次擲骰子時，系統隨機選擇一種風格（兩個骰子為同一風格）

### ✨ 視覺效果
- **擲骰動畫**：0.5 秒內快速閃爍 7 次骰子圖片，增加遊戲緊張感
- **顏色提示**：玩家 1 勝利顯示紅色，玩家 2 勝利顯示藍色，平手為黑色
- **圖片縮放**：使用 Zoom 模式，確保骰子圖片不變形

---

## 專案結構 | Project Structure

```
randomrace/
├── randomrace.slnx              # VS 解決方案檔案
├── randomrace/
│   ├── randomrace.csproj       # 專案檔（.NET 10 Windows Forms）
│   ├── Program.cs               # 應用程式入口點
│   ├── Form1.Designer.cs       # UI 元件定義（由 VS 生成）
│   ├── Form1_New.cs            # 主要遊戲邏輯
│   ├── Form1.resx              # 資源檔案
│   ├── Dice_Images/            # 骰子圖片目錄
│   │   ├── Classic/            # 經典風格（1.png ~ 6.png）
│   │   ├── Neon/               # 霓虹風格（1.png ~ 6.png）
│   │   └── Gold/               # 金色風格（1.png ~ 6.png）
│   └── bin/
│       └── Debug/
│           └── net10.0-windows/
│               └── Dice_Images/  # 執行時圖片路徑
└── README.md
```

---

## 系統需求 | Requirements

- **Windows 10/11** 作業系統
- **.NET 10 Runtime**（Windows Desktop）
- **Visual Studio 2022+**（如需編譯）

---

## 編譯與執行 | Build & Run

### 編譯
```bash
cd randomrace
dotnet build
```

### 執行
```bash
dotnet run
```

或直接執行 `randomrace.exe`（位於 `bin/Debug/net10.0-windows/`）

---

## 遊戲截圖 | Screenshots

啟動時顯示「準備開始」，點擊按鈕後動畫播放，最終顯示勝負結果。

---

## AI 協作說明 | AI Collaboration

本專案開發過程中借助 AI 工具（Gemini / Copilot）協作完成：

| 階段 | AI 角色 |
|------|---------|
| 架構設計 | 提供 C# Windows Forms 架構建議 |
| 程式碼生成 | 生成核心邏輯（擲骰、亂數、動畫）|
| 例外處理 | 補充 try-catch 與錯誤處理 |
| 最終調教 | 由開發者（黑皮）完整測試與優化 |

> ⚠️ **注意**：部分邏輯經過人工調整，例如 `Form1_New.cs` 中的風格隨機選擇與動畫時序參數。

---

## License

本專案僅供學習與個人使用。

---

*Generated with assistance from AI (Hermes Research & Gemini/Copilot)*
