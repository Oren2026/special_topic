# WPF POS 系統 - Visual Studio 開啟指南

## 前置需求
- Visual Studio 2022 (含 .NET 桌面開發工作負載)
- .NET 10 SDK (預覽版)

## 開啟專案

### 方式一：透過 dotnet CLI
```bash
cd ~/Desktop/special_topic/wpf_pos
dotnet new wpf --framework net10.0 --force
dotnet build
dotnet run
```

### 方式二：手動建立 Visual Studio 專案

1. Visual Studio → 建立新專案
2. 選擇 **WPF 應用程式 (.NET Framework)** 或 **WPF 應用程式 (.NET)**
3. 專案名稱：`WPF_POS`
4. 位置：`~/Desktop/special_topic/wpf_pos/`
5. 勾選「不要使用頂層陳述式」

### 所需 NuGet 套件（可選）
- `CommunityToolkit.Mvvm` - 若要用更簡化的 MVVM（目前使用手動實作，可不安裝）

### 替換預設檔案
建立專案後，用本資料夾中的檔案覆蓋：
- `App.xaml` / `App.xaml.cs`
- `MainWindow.xaml` / `MainWindow.xaml.cs`
- 參考 `Models/`、`ViewModels/`、`Views/`、`Services/` 資料夾

---

## 專案結構（完成後）

```
wpf_pos/
├── App.xaml                      ← 樣式 + 資源定義
├── App.xaml.cs                   ← 應用程式起點（初始化 DataService）
├── MainWindow.xaml               ← 主視窗（POS + 後台）
├── MainWindow.xaml.cs           ← 主視窗邏輯
├── Models/
│   ├── Kind.cs
│   ├── Tag.cs
│   ├── Product.cs
│   ├── OrderItem.cs
│   └── Order.cs
├── ViewModels/
│   ├── MainViewModel.cs         ← 前台邏輯
│   └── AdminViewModel.cs        ← 後台邏輯
├── Views/
│   ├── ProductManagementControl.xaml(.cs)
│   ├── KindManagementControl.xaml(.cs)
│   ├── TagManagementControl.xaml(.cs)
│   ├── ProductEditDialog.xaml(.cs)
│   ├── NameEditDialog.xaml(.cs)
│   ├── TagEditDialog.xaml(.cs)
│   └── PaymentDialog.xaml(.cs)
├── Services/
│   └── DataService.cs          ← JSON 讀寫
└── Data/                        ← 執行時自動建立
    └── store.json               ← 商品/種類/標籤資料
```

---

## 操作說明

| 操作 | 說明 |
|------|------|
| 點擊商品 | 加入購物車 |
| 種類篩選 | 左側按鈕，選「全部」或特定種類 |
| 標籤篩選 | 右側按鈕，可多選（AND 邏輯） |
| 結帳 | 選擇現金（找零）或信用卡 |
| 進入後台 | 標題「快餐POS系統」**連續點擊 5 下** |
| 後台操作 | 商品 CRUD / 種類 CRUD / 標籤 CRUD |

---

## 注意事項

- 第一次執行會自動建立 `Data/store.json` 並寫入預設商品
- 商品 ID 自動遞增
- 種類刪除不會連動刪除商品（商品會變成無種類）
- 標籤刪除不會連動刪除商品