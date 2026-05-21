# WPF POS 系統規格書
> 快餐基本POS，純練習專案

---

## 1. 技術架構

```
WPF_POS/
├── App.xaml                    # 應用程式起點
├── MainWindow.xaml              # 主視窗（點餐+結帳）
├── Models/
│   ├── Product.cs              # 商品模型
│   ├── Category.cs             # 分類模型
│   ├── OrderItem.cs            # 訂單項目
│   └── Order.cs                # 訂單
├── ViewModels/
│   ├── MainViewModel.cs        # 主視圖模型
│   └── PaymentViewModel.cs     # 結帳視圖模型
├── Views/
│   ├── ProductPanel.xaml       # 商品面板（類別+商品）
│   ├── CartPanel.xaml          # 購物車面板
│   └── PaymentDialog.xaml      # 結帳對話框
├── Services/
│   ├── ProductService.cs       # 商品資料服務
│   └── OrderService.cs         # 訂單服務
├── Data/
│   └── sample_data.json       # 範例商品資料
└── Resources/
    └── Styles.xaml             # 共用樣式
```

---

## 2. MVVM 架構

```
┌─────────────────────────────────────────────┐
│                    View                      │
│  MainWindow / ProductPanel / CartPanel      │
└──────────────────┬──────────────────────────┘
                   │ DataBinding
┌──────────────────▼──────────────────────────┐
│                ViewModel                     │
│  MainViewModel / PaymentViewModel            │
│  (INotifyPropertyChanged + ICommand)         │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│                 Model                         │
│  Product / Category / Order / OrderItem      │
└─────────────────────────────────────────────┘
```

**工具支援：**
- CommunityToolkit.Mvvm（輕量MVVM框架）
- 或手動實作 INotifyPropertyChanged

---

## 3. 功能模組

### 3.1 商品展示
- 類別側邊欄：漢堡、副餐、飲料、套餐
- 商品網格：按鈕式展示（方便觸控）
- 顯示：名稱 + 價格 + 圖示

### 3.2 購物車
- 右側面板：目前訂單項目
- 數量 +/- 按鈕
- 刪除單項 / 清空購物車
- 小計計算

### 3.3 結帳
- 總金額顯示
- 付款方式：現金 / 信用卡（模擬）
- 找零計算（現金模式）
- 完成後清空訂單

### 3.4 取消交易
- 一鍵取消當前訂單
- 確認提示

---

## 4. 資料模型

### Product
```csharp
- Id: int
- Name: string
- Price: decimal
- CategoryId: int
- ImagePath: string (可選)
```

### Category
```csharp
- Id: int
- Name: string
- DisplayOrder: int
```

### OrderItem
```csharp
- Product: Product
- Quantity: int
- Subtotal: decimal (Price * Quantity)
```

### Order
```csharp
- Items: List<OrderItem>
- Subtotal: decimal
- Tax: decimal (10%)
- Total: decimal
- PaymentMethod: string
- PaidAmount: decimal
- Change: decimal
```

---

## 5. 後台系統（商品管理）

### 5.1 進入方式
- 在主視窗的 POS 系統名稱上**連續點擊 5 下** → 進入後台
- 防止一般使用者誤觸

### 5.2 功能

#### 5.2.1 種類管理（主要分類）
- 動態新增/編輯/刪除種類（如：漢堡、副食、飲料、套餐）
- 種類用於前台商品展示的分類依據
- 可設定排列順序

#### 5.2.2 標籤管理（篩選用）
- 動態新增/編輯/刪除標籤（如：新品、熱銷、限时）
- 標籤用於篩選顯示，不影響分類
- 前台可依標籤篩選（如：只顯示「新品」商品）

#### 5.2.3 商品管理
- 新增商品：名稱、價格、種類、標籤（可複選）、圖示
- 編輯商品：修改所有欄位
- 刪除商品：確認後刪除
- 搜尋：依名稱關鍵字搜尋

### 5.3 前台標籤篩選
```
┌──────────────────────────────────────────────────────────────┐
│  [全部] [漢堡] [副食] [飲料] [套餐]        [新品] [熱銷] [限時] │
└──────────────────────────────────────────────────────────────┘
```
- 左側：種類篩選（顯示所有種類按鈕 + 全部）
- 右側：標籤篩選（顯示所有標籤按鈕）
- 同時作用：種類篩選 + 標籤篩選

### 5.4 後台 UI 佈局

```
┌──────────────────────────────────────────────────────────┐
│  ⚙️ 後台管理系統              [返回POS]                   │
├──────────────┬───────────────────────────────────────────┤
│              │                                           │
│  [商品管理]  │  商品列表                                  │
│              │  ┌──────────────────────────────────────┐ │
│  [種類管理]  │  │ 牛肉堡    $70    漢堡    [編輯][刪除] │ │
│              │  │ 雞腿堡    $65    漢堡    [編輯][刪除] │ │
│  [標籤管理]  │  │ 薯條(大)  $50    副食    [編輯][刪除] │ │
│              │  │ ...                                   │ │
│              │  └──────────────────────────────────────┘ │
│              │                                           │
│              │  [+ 新增商品]                             │
└──────────────┴───────────────────────────────────────────┘
```

### 5.5 資料模型

#### Product
```csharp
- Id: int
- Name: string
- Price: decimal
- KindId: int (所屬種類)
- TagIds: List<int> (所屬標籤，可多選)
- ImagePath: string (可選)
- CreatedAt: DateTime
```

#### Kind（種類）
```csharp
- Id: int
- Name: string
- DisplayOrder: int
```

#### Tag（標籤）
```csharp
- Id: int
- Name: string
- Color: string (UI顯示用)
```

---

## 6. 預設資料（初始樣本）

```json
{
  "kinds": [
    { "id": 1, "name": "漢堡", "displayOrder": 1 },
    { "id": 2, "name": "副食", "displayOrder": 2 },
    { "id": 3, "name": "飲料", "displayOrder": 3 },
    { "id": 4, "name": "套餐", "displayOrder": 4 }
  ],
  "tags": [
    { "id": 1, "name": "新品", "color": "#4CAF50" },
    { "id": 2, "name": "熱銷", "color": "#FF9800" },
    { "id": 3, "name": "限時", "color": "#F44336" }
  ],
  "products": [
    { "id": 1, "name": "牛肉堡", "price": 70, "kindId": 1, "tagIds": [1] },
    { "id": 2, "name": "雞腿堡", "price": 65, "kindId": 1, "tagIds": [2] },
    { "id": 3, "name": "素食堡", "price": 60, "kindId": 1, "tagIds": [] },
    { "id": 4, "name": "薯條(大)", "price": 50, "kindId": 2, "tagIds": [] },
    { "id": 5, "name": "薯條(小)", "price": 35, "kindId": 2, "tagIds": [] },
    { "id": 6, "name": "雞塊", "price": 45, "kindId": 2, "tagIds": [2] },
    { "id": 7, "name": "可樂", "price": 30, "kindId": 3, "tagIds": [] },
    { "id": 8, "name": "雪碧", "price": 30, "kindId": 3, "tagIds": [] },
    { "id": 9, "name": "奶茶", "price": 40, "kindId": 3, "tagIds": [1] },
    { "id": 10, "name": "牛肉套餐", "price": 110, "kindId": 4, "tagIds": [2] },
    { "id": 11, "name": "雞腿套餐", "price": 105, "kindId": 4, "tagIds": [] },
    { "id": 12, "name": "素食套餐", "price": 95, "kindId": 4, "tagIds": [] }
  ]
}
```

---

## 6. UI 佈局

```
┌──────────────────────────────────────────────────────────┐
│  🏪 快餐POS系統                            [取消交易]     │
├─────────────────────────────┬────────────────────────────┤
│                             │  購物車                    │
│  [漢堡] [副餐] [飲料] [套餐]│  ┌──────────────────────┐  │
│                             │  │ 牛肉堡 x2    $140   │  │
│  ┌─────┐ ┌─────┐ ┌─────┐   │  │ 薯條(大) x1  $50    │  │
│  │     │ │     │ │     │   │  │ 可樂 x2      $60    │  │
│  │ 圖  │ │ 圖  │ │ 圖  │   │  └──────────────────────┘  │
│  │     │ │     │ │     │   │                            │
│  ├─────┤ ├─────┤ ├─────┤   │  小計：$250                │
│  │牛肉堡│ │雞腿堡│ │素食堡│   │  稅(10%): $25             │
│  │ $70 │ │ $65 │ │ $60 │   │  ──────────────            │
│  └─────┘ └─────┘ └─────┘   │  總計：$275                │
│                             │                            │
│  ┌─────┐ ┌─────┐ ┌─────┐   │  [        結帳        ]   │
│  │ ... │ │ ... │ │ ... │   │                            │
│  └─────┘ └─────┘ └─────┘   │                            │
├─────────────────────────────┴────────────────────────────┤
│  狀態： ready                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 8. 開發順序

1. **專案建立** - WPF App + MVVM 結構
2. **Model** - Product, Kind, Tag, Order, OrderItem
3. **資料服務** - JSON 讀寫（ProductService, KindService, TagService）
4. **前台 POS** - 種類篩選 + 商品展示 + 購物車
5. **標籤篩選** - 前台標籤按鈕 + 雙重篩選邏輯
6. **結帳流程** - 付款對話框 + 找零
7. **後台系統** - 商品 CRUD + 種類管理 + 標籤管理
8. **樣式優化** - 按鈕/版面調整

---

## 8. 技術細節

### 8.1 後台防護
- 無需登入（純練習專案）
- 依賴「連續點擊 5 下」作為進入條件
- 返回按鈕回到主 POS 視圖

### 8.2 資料持久化
- 商品資料：JSON 檔案（`Data/products.json`）
- 啟動時讀取，變更時寫入
- 無需資料庫（SQLite 可選，未來擴展）

### 8.3 頁面切換
- 使用 `ContentControl` + `DataTemplate` 切換前台/後台視圖
- 或使用 `NavigationWindow`（待確認）

---

> 確認後再開始實作。可以調整商品種類或功能範圍。