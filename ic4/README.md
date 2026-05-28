# IC4 - IC Design Visualization Tool

![IC4 Demo](docs/demo.gif)

**IC4** 是一個 Rust 實現的積體電路設計視覺化工具，涵蓋從邏輯合成到實體佈局的主流數位設計流程。

---

## 功能架構

### 1. 邏輯合成 (Logic Synthesis)

| 模組 | 功能 |
|------|------|
| `Signal` | 布林代數表達式樹 (And/Or/Not/Var/Const) |
| `Kmap` | Karnaugh Map 卡諾圖化簡 |
| `QuineMcCluskey` | Quine-McCluskey 質蘊含項求解 |
| `TechMapper` | 技術映射至標準單元庫 |

```rust
use ic4::prelude::*;

let a = Signal::var("a");
let b = Signal::var("b");
let c = Signal::var("c");

// 布林表達式: (a & b) | c
let expr = a.and(b).or(c);
```

### 2. 實體設計 (Physical Design)

| 模組 | 功能 |
|------|------|
| `Floorplan` | 晶片版面規劃、切片式包裝、模擬退火 |
| `Placer` | 區塊配置 (Grid / Force-Directed) |
| `Router` | 布線演算法 (Lee / Maze / Channel) |

### 3. 視覺化 (Visualization)

- **文字模式**: `cargo run --example demo` — 終端機 ASCII 輸出
- **GUI 模式**: `cargo run --example gui_demo` — 互動式 4 面板 GUI

---

## 快速開始

```bash
# 終端機演示（無需 GUI）
cargo run --example demo

# GUI 演示（需要圖形介面）
cargo run --example gui_demo

# 測試
cargo test
```

---

## 專案結構

```
ic4/
├── src/
│   ├── synthesis/       # 邏輯合成
│   │   ├── kmap.rs     # K-map 卡諾圖
│   │   ├── quine.rs    # Quine-McCluskey
│   │   ├── techmap.rs  # 技術映射
│   │   └── mod.rs      # Signal 布林表達式
│   ├── physical/       # 實體設計
│   │   ├── floorplan.rs # 版面規劃
│   │   ├── place.rs    # 配置器
│   │   └── route.rs    # 路由器
│   └── viz/            # 視覺化
│       ├── kmap.rs     # K-map 繪製
│       ├── floorplan.rs
│       ├── placement.rs
│       └── routing.rs
└── examples/
    ├── demo.rs         # 文字終端演示
    └── gui_demo.rs     # GUI 演示
```

---

## IC 設計流程說明

現代數位 IC 設計通常包含以下階段，IC4 對應支援：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  RTL 設計   │────▶│ 邏輯合成    │────▶│ 技術映射    │
│ (Verilog)   │     │ (K-map/Q-M) │     │ (標準單元庫) │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   布線     │◀────│   配置     │◀────│  版面規劃   │
│  (Router)   │     │ (Placer)   │     │(Floorplan)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## CPU 演示架構

`cpu_demo.rs` 展示一個簡化的 CPU 資料路徑：

```
┌──────────────────────────────────────────────────┐
│                  CPU Datapath                     │
│                                                   │
│   ┌────────┐     ┌────────┐     ┌────────┐       │
│   │  REG   │────▶│  ALU   │────▶│  REG   │       │
│   │ (A, B) │     │        │     │  (Y)   │       │
│   └────────┘     └────────┘     └────────┘       │
│        │                ▲                          │
│        │                │                          │
│   ┌────────┐     ┌────────┐                       │
│   │ Decoder │────▶│  PC    │                       │
│   │ (IR)    │     │        │                       │
│   └────────┘     └────────┘                       │
│                                                   │
│   K-map: 指令解碼邏輯 → 電路化簡                   │
│   Floorplan: CPU 區塊佈局                          │
│   Placement: 模組配置位置                          │
│   Routing: 訊號連線                                │
└──────────────────────────────────────────────────┘
```

---

## 技術規格

- **語言**: Rust 2021
- **圖形**: `egui` (可選，default feature)
- **依賴**: `rand` (物理設計演算法)
- **測試覆蓋**: 70+ 單元測試

---

## 版本歷程

- `0.1.0`: 初始版本
  - ✅ K-map 卡諾圖化簡
  - ✅ Quine-McCluskey 質蘊含項
  - ✅ 版面規劃（切片式包裝）
  - ✅ 配置（Grid / Force-Directed）
  - ✅ 佈線（Lee / Maze / Channel）
  - ✅ GUI 四面板視覺化
  - ✅ 文字終端演示

---

## Roadmap

- [ ] 清除編譯 warning（12 個）
- [ ] K-map don't-care 顯示（黃色）
- [ ] 四面板 Regenerate 按鈕
- [ ] 布林表達式即時編輯
- [ ] 輸出 Verilog/netlist