# WPF POS 系統

快餐基本POS，純練習專案。

---

## 開啟方式

### Visual Studio
1. 安裝 **Visual Studio 2022** + **.NET 桌面開發工作負載**
2. 安裝 **.NET 10 SDK**（[dotnet.microsoft.com](https://dotnet.microsoft.com) 下載）
3. 用 VS 開啟 `WPF_POS.sln`

### 命令列
```bash
cd ~/Desktop/special_topic/wpf_pos
dotnet restore
dotnet build
dotnet run
```

---

## 專案結構

```
wpf_pos/
├── WPF_POS.sln              ← 雙擊用 VS 開啟
├── WPF_POS.csproj          ← 專案檔（SDK-style, net10.0-windows）
├── App.xaml/cs             ← 應用程式起點 + 全域樣式
├── MainWindow.xaml/cs      ← 主視窗（POS 前台 + 後台切換）
├── Models/                 ← Kind, Tag, Product, OrderItem, Order
├── ViewModels/             ← MainViewModel, AdminViewModel
├── Views/                  ← UserControl + Dialog
├── Services/               ← DataService（JSON CRUD）
├── Data/                   ← 執行時自動建立 store.json
├── SPEC.md                 ← 完整規格書
└── README.md
```

---

## 操作說明

| 操作 | 說明 |
|------|------|
| 點擊商品 | 加入購物車 |
| 種類篩選 | 左側按鈕（全部/漢堡/副食/飲料/套餐）|
| 標籤篩選 | 右側按鈕（新品/熱銷/限時），可多選 |
| 結帳 | 現金（找零）或信用卡 |
| 進入後台 | 標題「快餐POS系統」**連續點擊 5 下** |
| 後台 | 商品 CRUD / 種類 CRUD / 標籤 CRUD |

---

## 技術規格

- .NET 10.0 + WPF
- 手動 MVVM（無 CommunityToolkit.Mvvm）
- 資料持久化：JSON（`Data/store.json`）
- 啟動時自動初始化預設商品