"""
Physics — 純規劃導向模組
只提供兩個核心 function，够 robot_brain 直接使用

公式：
  速度衰減：v(t) = v0 - friction × t
  滑行距離：s = v0² / (2 × friction)
  反向計算：v_needed = sqrt(2 × friction × dist)
"""

# ── 常數 ──────────────────────────────────────
FRICTION      = 60.0   # cm/s²，撞球檯典型摩擦力
BALL_RADIUS   = 5.73   # cm
MAX_VELOCITY  = 200.0  # cm/s，正常桿力上限（約 2 m/s，够打過半場）


# ── 核心 function ─────────────────────────────

def required_velocity_for_distance(dist: float) -> float:
    """
    給定目標距離（cm），需要多少初速才能滑到？
    
    推導：s = v0² / (2f)  →  v0 = sqrt(2 × f × s)
    
    Example:
      要滑 200 cm → 需要 sqrt(2 × 60 × 200) = 154.9 cm/s
    """
    import math
    return math.sqrt(2 * FRICTION * dist)


def max_sliding_distance(v0: float) -> float:
    """
    給定初速，最多能滑多遠？
    
    推導：v(t) = v0 - ft → 停止時 t = v0/f
          s = v0×t - ½ft² = v0²/(2f)
    """
    return (v0 * v0) / (2 * FRICTION)


def segment_into_reachable(dist: float, v_max: float = None) -> int:
    """
    目標距離需要分幾段打？
    （每次從靜止出發，用 v_max 的力道）
    
    Example:
      600 cm 遠，單次最大滑行 333 cm → 需要 2 段
    """
    if v_max is None:
        v_max = MAX_VELOCITY
    max_dist = max_sliding_distance(v_max)
    import math
    return math.ceil(dist / max_dist)


def can_single_hit(dist: float, v_max: float = None) -> bool:
    """一次打能得到目標距離嗎？"""
    if v_max is None:
        v_max = MAX_VELOCITY
    return dist <= max_sliding_distance(v_max)


def time_to_stop(v0: float) -> float:
    """從 v0 減速到 0 需要多久（秒）"""
    return v0 / FRICTION


def distance_to_stop(v0: float) -> float:
    """從 v0 到停止能滑多遠"""
    return max_sliding_distance(v0)


def velocity_at(v0: float, t: float) -> float:
    """t 秒後的速度（摩擦衰減後）"""
    return max(0.0, v0 - FRICTION * t)


def position_after(s0: float, v0: float, t: float) -> float:
    """從 s0 出發，t 秒後的位置"""
    return s0 + v0 * t - 0.5 * FRICTION * t * t


# ── 測試 ──────────────────────────────────────

if __name__ == '__main__':
    print("=== 核心公式驗證 ===")
    for d in [50, 100, 200, 333, 500]:
        v = required_velocity_for_distance(d)
        t = time_to_stop(v)
        print(f"滑 {d:4.0f} cm 需要 {v:6.1f} cm/s，停止時間 {t:.2f}s")

    print()
    print("=== 分段計算 ===")
    for d in [200, 333, 400, 500, 600, 700]:
        v = required_velocity_for_distance(d)
        segs = segment_into_reachable(d)
        print(f"距離 {d:4.0f} cm → 需要 {segs} 段（單次最大可達 {max_sliding_distance(MAX_VELOCITY):.0f} cm）")