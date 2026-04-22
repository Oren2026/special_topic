# 作業說明書
# 【骰子遊戲 / 猜拳遊戲】Windows Forms 雙人對戰

---

## 一、開發環境
- **語言**：C# (.NET Framework / .NET 6+)
- **框架**：Windows Forms（System.Windows.Forms）
- **IDE**：Visual Studio 2022 或 VS Code（搭配 C# Extensions）

---

## 二、如何建立專案（VS 2022）

1. 開啟 Visual Studio 2022 → 新增專案
2. 選擇「Windows Forms App (.NET Framework)」或「Windows Forms App」
3. 命名為 `DiceRPSGame`
4. 點擊「建立」

---

## 三、檔案配置

```
DiceRPSGame/
├── Program.cs              # 程式進入點（自動產生，也可使用本專案提供的版本）
├── Form1.cs                # 完整程式本體（所有邏輯與 Designer 程式碼）
└── images/                  # 【自行建立】放置骰子/猜拳圖片
    ├── 1.png                # 骰子1 或 剪刀
    ├── 2.png                # 骰子2 或 石頭
    ├── 3.png                # 骰子3 或 布
    ├── 4.png                # 骰子4
    ├── 5.png                # 骰子5
    └── 6.png                # 骰子6
```

> **images/ 資料夾需自行建立在專案根目錄**，並放入對應的 PNG 圖片。
> 圖片命名規則：`數字.png`（1~6 for 骰子，1~3 for 猜拳）

---

## 四、程式架構

### 4.1 三大核心功能對應

| 評分項目 | 對應章節 | 說明 |
|---------|---------|------|
| **A. 初始化** | `Form1_Load()` + `LoadDefaultImages()` | 啟動時自動載入 1.png 為預設圖片 |
| **B. 隨機動態圖片** | `btnRoll_Click()` + `PlayRound()` | 隨機產生點數後動態切換為對應 PNG |
| **C. 勝負判定** | `DetermineWinner()` | 比較雙方點數，顯示 win / lose / tie |

### 4.2 額外加分功能
- **模式切換**：ComboBox 可即時切換「骰子」或「猜拳」兩種模式
- **歷史紀錄**：ListBox 顯示最近 20 筆遊戲結果（時間戳 + 雙方出招 + 勝負）
- **Fallback 機制**：當圖片檔案不存在時，在 PictureBox 上繪製數字而非當機
- **記憶體管理**：`Form1_FormClosing()` 釋放 Image 資源

---

## 五、使用方式

1. **執行遊戲**：點選上方「🎲 Dice」或「✂️ RPS」切換模式
2. **骰子模式**：
   - 點「🎲 Roll Dice」按鈕
   - 雙方同時隨機擲出 1~6
   - 點數大者獲勝，平手顯示 Tie
3. **猜拳模式**：
   - 點「✂️ Play」按鈕
   - 雙方隨機出招（1=剪刀、2=石頭、3=布）
   - 結果顯示雙方招式與勝負

---

## 六、程式原創說明

| 項目 | 說明 |
|------|------|
| **整體架構** | 原創，從頭設計 Windows Forms 配置 |
| **Random 亂數** | 使用 `System.Random`，每回合重新實例化避免爭用 |
| **防例外機制** | try-catch 包住圖片載入、模式切換、結果判定三個區塊 |
| **圖片 Fallback** | 原創設計：當圖片缺失時以 GDI+ 繪製數字代替 |
| **猜拳邏輯** | 原創：`diff == 1 \|\| diff == -2` 判斷 P1 獲勝 |
| **AI 輔助** | 有使用 GitHub Copilot 輔助快速生成程式碼骨架 |
| **參考** | 微軟官方 Windows Forms 文件、.NET API Reference |
| **複製貼上** | Designer 程式碼區塊（`InitializeComponent`）為標準 Windows Forms 程式碼，可視為範本 |

---

## 七、編譯與執行

```bash
# 命令列編譯（.NET SDK）
cd DiceRPSGame
dotnet build
dotnet run
```

或在 Visual Studio 中：
1. 將 `Form1.cs` 和 `Program.cs` 內容替換進去
2. 建立 `images/` 資料夾並放入圖片
3. 按 `F5` 執行

---

## 八、截圖預覽（執行結果）

```
┌─────────────────────────────────────┐
│  [🎲 Dice 骰子比大小 ▼]              │
│                                     │
│        🎲 Dice Game                  │
│                                     │
│  Player 1          Player 2         │
│  ┌────────┐        ┌────────┐       │
│  │  1.png │        │  1.png │       │
│  └────────┘        └────────┘       │
│                                     │
│       [ 🎲 Roll Dice 擲骰子 ]       │
│                                     │
│  ★★★ Player 1 Wins! ★★★            │
│  Rule: Higher number wins            │
└─────────────────────────────────────┘
```
