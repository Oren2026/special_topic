#!/usr/bin/env python3
"""
verify_coord_consistency.py
===========================
跨系統（Windows / WSL）座標一致性驗證腳本。

執行方式：
    cd ~/Desktop/special_topic/hiwin
    python3 verify_coord_consistency.py

輸出：終端彩色報告 + 同目錄 verify_report.csv
"""

import sys
import os
import json
import math
import csv
import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# ── 、路徑設定 ──────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.abspath(__file__))
WINDOWS_CTRL = os.path.join(ROOT, "windows", "control")
WSL_DIR = os.path.join(ROOT, "wsl")

sys.path.insert(0, WINDOWS_CTRL)
sys.path.insert(0, WSL_DIR)

# ── 測試資料：固定 4 角校正點（pixel, 模擬 1280×720 拍攝視角）───────────────

# 模擬相機視角中的球檯四角落（pixel）
# 順序：左上 → 右上 → 右下 → 左下
CALIB_POINTS_PIXEL = [
    [210, 155],   # 左上
    [1070, 155],  # 右上
    [1070, 565],  # 右下
    [210, 565],   # 左下
]

# ── 模擬相機解析度（用於比例估算）───────────────────────────────────────────

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# ════════════════════════════════════════════════════════════════════════════
# Layer 1: Homography dst 座標系驗證
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class HomographySpec:
    """單一系統的 Homography 規格"""
    name: str           # "Windows calibration.py" / "WSL coord_manager.py"
    dst_points: List[Tuple[float, float]]  # 4 個 dst 點
    has_center_origin: bool  # 是否為長邊中點原點

    def dst_expected(self) -> str:
        if self.has_center_origin:
            return "(-600,0)→(600,0)→(600,630)→(-600,630) [長邊中點原點]"
        else:
            return "(0,0)→(1200,0)→(1200,630)→(0,630) [左上角原點]"


def load_windows_calibration() -> HomographySpec:
    """讀取 Windows calibration.py 的 dst 設定"""
    # 直接從原始碼抽取（避免 import cv2 環境問題，用字串比對）
    cal_path = os.path.join(WINDOWS_CTRL, "calibration.py")
    with open(cal_path, encoding="utf-8") as f:
        content = f.read()

    # 找 dst = np.array([...])
    import re
    m = re.search(
        r'dst\s*=\s*np\.array\(\s*\[(.*?)\]\s*,\s*dtype=np\.float32\)',
        content, re.DOTALL
    )
    if not m:
        return HomographySpec("Windows calibration.py", [], False)

    inner = m.group(1)
    nums = re.findall(r'[-+]?\d+', inner)
    pts = [(float(nums[i]), float(nums[i+1])) for i in range(0, len(nums), 2)]
    has_center = any(abs(x) > 100 for x, _ in pts)  # 有 ±600 就是長邊中點原點
    return HomographySpec("Windows calibration.py", pts, has_center)


def load_wsl_coord_manager() -> HomographySpec:
    """
    讀取 WSL coord_manager.py 的 dst 設定

    WSL coord_manager.py 中 pts_dst 可能使用 config 變數，
    解析表達式有難度，直接用 config.py 的實際值重建。
    然後從原始碼第一個 [數字,數字] 判斷是否已更新。
    """
    cfg_path = os.path.join(WSL_DIR, "config.py")
    cm_path = os.path.join(WSL_DIR, "coord_manager.py")

    # 讀 config.py 的實際數值
    cfg_width = 1200
    cfg_height = 630
    with open(cfg_path, encoding="utf-8") as f:
        for line in f:
            if "TABLE_WIDTH" in line and "=" in line:
                m = re.search(r'TABLE_WIDTH\s*=\s*(\d+)', line)
                if m: cfg_width = int(m.group(1))
            if "TABLE_HEIGHT" in line and "=" in line:
                m = re.search(r'TABLE_HEIGHT\s*=\s*(\d+)', line)
                if m: cfg_height = int(m.group(1))

    # 直接用 config 值建出長邊中點原點的 dst
    dst_pts = [
        (-cfg_width / 2, 0.0),
        ( cfg_width / 2, 0.0),
        ( cfg_width / 2, float(cfg_height)),
        (-cfg_width / 2, float(cfg_height)),
    ]

    # 從原始碼第一個 [數字,數字] 判斷是否已用長邊中點原點
    with open(cm_path, encoding="utf-8") as f:
        cm_content = f.read()
    raw_pts = re.findall(r'\[([-\d]+),\s*([-\d]+)\]', cm_content)
    has_center = bool(raw_pts and float(raw_pts[0][0]) < -50)

    return HomographySpec("WSL coord_manager.py", dst_pts, has_center)


def verify_layer1() -> Tuple[bool, str]:
    """
    Layer 1: Homography dst 座標系一致性
    規則：兩邊都必須使用「長邊中點原點」
    """
    win_spec = load_windows_calibration()
    wsl_spec = load_wsl_coord_manager()

    lines = []
    ok = True

    for spec in [win_spec, wsl_spec]:
        if spec.has_center_origin:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            ok = False
        lines.append(f"  {spec.name}: {status}")
        lines.append(f"    dst = {spec.dst_points}")
        lines.append(f"    {spec.dst_expected()}")

    verdict = "✅ PASS" if ok else "❌ FAIL"
    detail = (
        f"{verdict} — Homography dst 座標系\n" +
        "\n".join(lines) +
        "\n\n【修復指引】" +
        "\n  WSL coord_manager.py: pts_dst 改為" +
        "\n    [[-600, 0], [600, 0], [600, 630], [-600, 630]]"
    )
    return ok, detail


# ════════════════════════════════════════════════════════════════════════════
# Layer 2: 口袋 mm 座標一致性
# ════════════════════════════════════════════════════════════════════════════

# Windows SimTable 的口袋定義（從 sim_table.py 抽出）
# 原點在長邊中點：X ∈ [-600, +600], Y ∈ [0, 630]
WINDOWS_POCKETS = {
    "top_left":   {"x": -578.5, "y": 53.5,  "kind": "corner"},
    "top_right":  {"x":  578.5, "y": 53.5,  "kind": "corner"},
    "bot_left":   {"x": -578.5, "y": 576.5, "kind": "corner"},
    "bot_right":  {"x":  578.5, "y": 576.5, "kind": "corner"},
    "side_left":  {"x": -575.0, "y": 315.0, "kind": "side"},
    "side_right": {"x":  575.0, "y": 315.0, "kind": "side"},
}


def load_wsl_pockets() -> Dict[str, Tuple[float, float]]:
    """從 WSL strategy_module.py 抽出 POCKETS 定義"""
    sm_path = os.path.join(WSL_DIR, "strategy_module.py")
    with open(sm_path, encoding="utf-8") as f:
        content = f.read()

    import re
    # 抓 POCKETS = { ... } 區塊
    m = re.search(r'POCKETS\s*=\s*\{(.+?)\n\s*\}', content, re.DOTALL)
    if not m:
        return {}

    block = m.group(1)
    pockets = {}
    for line in block.split('\n'):
        # "name": (x, y), — 支援整數和浮點數
        pm = re.search(r'"(\w+)":\s*\(\s*([-\d.]+),\s*([-\d.]+)\s*\)', line)
        if pm:
            pockets[pm.group(1)] = (float(pm.group(2)), float(pm.group(3)))

    return pockets


def mm_coords_consistent(win_pockets: Dict, wsl_pockets: Dict) -> Tuple[bool, List[str]]:
    """
    檢查兩邊口袋 mm 座標是否一致
    兩邊現在都使用 SimTable 長邊中點原點，座標應直接可比較
    """
    lines = []
    ok = True

    # Pocket 名稱對照表（WSL 舊名 → WSL 新名 / SimTable 名）
    # top_mid/bot_mid（WSL舊）→ side_left/side_right（SimTable）
    name_aliases = {
        "top_mid": "side_left",
        "bot_mid": "side_right",
    }

    all_names = set(win_pockets.keys())
    wsl_remapped = {name_aliases.get(n, n): v for n, v in wsl_pockets.items()}
    all_names |= set(wsl_remapped.keys())

    for name in sorted(all_names):
        w = win_pockets.get(name)
        s = wsl_remapped.get(name)

        if w is None:
            lines.append(f"  {name}: ⚠️ 只在 WSL 有定義（Windows 缺）")
            continue
        if s is None:
            lines.append(f"  {name}: ⚠️ 只在 Windows 有定義（WSL 缺）")
            continue

        wx, wy = w["x"], w["y"]
        sx, sy = s

        diff = math.hypot(wx - sx, wy - sy)

        if diff < 5.0:  # < 5mm 誤差
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            ok = False
        lines.append(f"  {name}: {status}")
        lines.append(f"    Windows: ({wx:.1f}, {wy:.1f})")
        lines.append(f"    WSL:     ({sx:.1f}, {sy:.1f})")
        lines.append(f"    差距: {diff:.1f}mm {'✅' if diff < 5 else '❌'}")

    return ok, lines


def verify_layer2() -> Tuple[bool, str]:
    """
    Layer 2: 口袋 mm 座標一致性
    需考慮原點差異：WSL 左上角原點 vs Windows SimTable 長邊中點原點
    """
    wsl_pockets = load_wsl_pockets()
    ok, lines = mm_coords_consistent(WINDOWS_POCKETS, wsl_pockets)

    verdict = "✅ PASS" if ok else "❌ FAIL"
    detail = (
        f"{verdict} — 口袋 mm 座標一致性\n" +
        "\n".join(lines) +
        ("\n\n【修復指引】" if not ok else "") +
        ("\n  WSL strategy_module.py POCKETS 需同步為 SimTable 定義：\n" if not ok else "")
    )
    return ok, detail


# ════════════════════════════════════════════════════════════════════════════
# Layer 3: Round-trip 穩定性測試
# ════════════════════════════════════════════════════════════════════════════

def simulate_homography_roundtrip(
    dst_points: List[Tuple[float, float]],
    calib_pixel: List[List[float]],
    test_mm_points: List[Tuple[float, float]]
) -> Tuple[bool, List[str], float]:
    """
    模擬 Homography round-trip 穩定性
    1. 用 calib_pixel + dst_points 計算 Homography
    2. pixel → mm → pixel（逆變換）
    3. mm → pixel → mm（正變換）

    回傳：(ok, lines, max_error)
    """
    try:
        import numpy as np
        import cv2
    except ImportError:
        return False, ["  ⚠️  numpy/cv2 未安裝，跳過 Layer 3"], 999.0

    src = np.array(calib_pixel, dtype=np.float32)
    dst = np.array(dst_points, dtype=np.float32)

    M = cv2.getPerspectiveTransform(src, dst)
    M_inv = np.linalg.inv(M)

    lines = []
    max_error = 0.0
    ok = True

    # Test 1: pixel → mm → pixel
    for i, (px, py) in enumerate(test_mm_points):
        # 先轉 mm（用正變換，但 swap：pixel 是 src，mm 是 dst）
        pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
        mm_hom = cv2.perspectiveTransform(pt, M)[0][0]
        mx, my = mm_hom[0], mm_hom[1]

        # mm → pixel（逆變換）
        mm_pt = np.array([[[mx, my]]], dtype=np.float32)
        pixel_back = cv2.perspectiveTransform(mm_pt, M_inv)[0][0]
        bx, by = pixel_back[0], pixel_back[1]

        err = math.hypot(bx - px, by - py)
        max_error = max(max_error, err)

        if err > 0.5:
            status = "❌ FAIL"
            ok = False
        else:
            status = "✅ PASS"
        lines.append(f"  pixel→mm→pixel [{i}]: ({px:.0f},{py:.0f}) → ({mx:.1f},{my:.1f}) → ({bx:.1f},{by:.1f}) | 誤差 {err:.3f}px {status}")

    # Test 2: mm → pixel → mm（使用逆變換）
    for i, (mx, my) in enumerate(test_mm_points):
        mm_pt = np.array([[[mx, my]]], dtype=np.float32)
        pixel = cv2.perspectiveTransform(mm_pt, M_inv)[0][0]
        px, py = pixel[0], pixel[1]

        pt = np.array([[[px, py]]], dtype=np.float32)
        mm_back = cv2.perspectiveTransform(pt, M)[0][0]
        bx, by = mm_back[0], mm_back[1]

        err = math.hypot(bx - mx, by - my)
        max_error = max(max_error, err)

        if err > 0.5:
            status = "❌ FAIL"
            ok = False
        else:
            status = "✅ PASS"
        lines.append(f"  mm→pixel→mm [{i}]: ({mx:.0f},{my:.0f}) → ({px:.1f},{py:.1f}) → ({bx:.1f},{by:.1f}) | 誤差 {err:.3f}mm {status}")

    return ok, lines, max_error


def verify_layer3() -> Tuple[bool, str]:
    """
    Layer 3: Round-trip 穩定性
    使用 Windows 的 dst 點（長邊中點原點）作為基準
    """
    win_spec = load_windows_calibration()
    if not win_spec.has_center_origin:
        return False, (
            "❌ FAIL — Windows dst 非長邊中點原點，跳過 Layer 3\n"
            "【需先修復 Layer 1】"
        )

    # 測試點：取 6 個口袋 mm 座標 + 4 個特殊點
    test_mm = [
        (-600, 0),    # 長邊左端
        (600, 0),     # 長邊右端
        (-600, 630),  # 長邊左下
        (600, 630),   # 長邊右下
        (0, 0),       # 原點
        (-578.5, 53.5),   # top_left 口袋
        (578.5, 53.5),    # top_right 口袋
        (575.0, 315.0),   # side_right 口袋
    ]

    ok, lines, max_err = simulate_homography_roundtrip(
        win_spec.dst_points,
        CALIB_POINTS_PIXEL,
        test_mm
    )

    verdict = "✅ PASS" if ok else "❌ FAIL"
    detail = (
        f"{verdict} — Round-trip 穩定性（閾值 0.5）\n"
        f"  最大誤差: {max_err:.3f}\n" +
        "\n".join(lines)
    )
    return ok, detail


# ════════════════════════════════════════════════════════════════════════════
# 主報告產生器
# ════════════════════════════════════════════════════════════════════════════

def green(t): return f"\033[92m{t}\033[0m"
def red(t):   return f"\033[91m{t}\033[0m"
def yellow(t): return f"\033[93m{t}\033[0m"

LAYER_NAMES = [
    "Layer 1: Homography dst 座標系（長邊中點原點）",
    "Layer 2: 口袋 mm 座標一致性",
    "Layer 3: Round-trip 穩定性",
]

LAYER_FUNCS = [verify_layer1, verify_layer2, verify_layer3]


def run_all() -> Tuple[List[bool], List[str]]:
    results = []
    details = []
    for name, fn in zip(LAYER_NAMES, LAYER_FUNCS):
        print(f"\n{'='*60}")
        print(f"  {name}")
        print('='*60)
        try:
            ok, detail = fn()
        except Exception as e:
            ok = False
            detail = f"❌ FAIL — 執行例外: {e}"
            import traceback
            detail += "\n" + traceback.format_exc()
        results.append(ok)
        details.append(detail)
        print(detail)
    return results, details


def write_csv(results: List[bool], details: List[str]):
    report_path = os.path.join(ROOT, "verify_report.csv")
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Layer", "Status", "Detail"])
        for i, (name, ok, detail) in enumerate(zip(LAYER_NAMES, results, details)):
            status = "PASS" if ok else "FAIL"
            # 去除 ANSI code 簡單處理
            clean = detail.replace("\033[92m", "").replace("\033[0m", "").replace("\033[91m", "").replace("\033[93m", "")
            writer.writerow([name, status, clean])
    return report_path


def main():
    print("\n" + "🏁".center(60, "="))
    print("  HIWIN 撞球機器人 — 跨系統座標一致性驗證")
    print("=".center(60, "="))
    print(f"\n📁 專案目錄: {ROOT}")
    print(f"📷 測試校正點（pixel）: {CALIB_POINTS_PIXEL}")
    print(f"🖥️  相機解析度: {CAMERA_WIDTH}×{CAMERA_HEIGHT}")

    results, details = run_all()

    # 總結
    print(f"\n{'='*60}")
    print("  總結")
    print('='*60)
    all_pass = all(results)
    pass_count = sum(results)
    total = len(results)
    print(f"\n  結果: {pass_count}/{total} layers passed")

    if all_pass:
        print(f"\n  {green('✅ 全部 PASS — 座標系統一致')}")
    else:
        print(f"\n  {red('❌ 有 FAIL — 需修復後重新驗證')}")
        failed = [LAYER_NAMES[i] for i, r in enumerate(results) if not r]
        for fn in failed:
            print(f"     - {fn}")

    report_path = write_csv(results, details)
    print(f"\n📄 報告已寫入: {report_path}")

    # Exit code
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
