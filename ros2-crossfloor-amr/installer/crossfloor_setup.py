#!/usr/bin/env python3
"""
crossfloor_setup.py — WSL2 + ROS2 環境一鍵安裝工具（Windows 端）

功能：
1. 檢查 WSL2 是否已啟用，若無則自動啟用（需要 admin）
2. 檢查 Ubuntu 22.04 是否已安裝，若無則自動安裝
3. 開啟 WSL Ubuntu 並執行安裝腳本

使用方式：
- 直接執行：python crossfloor_setup.py
- 封裝成 exe：pyinstaller --onefile --icon=app.ico crossfloor_setup.py
"""

import subprocess
import sys
import os
import time
import ctypes
from pathlib import Path


# ─── 顏色（ANSI，但 Windows CMD 不支援，所以同時輸出無色版本）───
def log_info(msg):   print(f"[INFO]  {msg}")
def log_ok(msg):     print(f"[OK]    {msg}")
def log_warn(msg):   print(f"[WARN]  {msg}")
def log_error(msg):  print(f"[ERROR] {msg}")


# ─── 系統需求 ───
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_cmd(cmd, capture=True, shell=True, check=False):
    """執行 Windows 命令，回傳 (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd, capture_output=capture, text=True, shell=shell
        )
        if check and result.returncode != 0:
            log_error(f"命令失敗：{' '.join(cmd) if isinstance(cmd, list) else cmd}")
            log_error(result.stderr)
        return result.returncode, result.stdout or "", result.stderr or ""
    except FileNotFoundError:
        return -1, "", "Command not found"


def is_wsl_installed():
    """檢查 WSL 是否可用"""
    code, out, _ = run_cmd("wsl --list --quiet")
    if code != 0:
        return False
    return True


def is_ubuntu_installed():
    """檢查 Ubuntu 22.04 是否已安裝"""
    code, out, _ = run_cmd("wsl --list --quiet")
    if code != 0:
        return False
    return "Ubuntu-22.04" in out or "Ubuntu" in out


def is_wsl2_enabled():
    """檢查 WSL2 功能是否已啟用（透過 registry）"""
    code, out, _ = run_cmd(
        'reg query "HKLM\\SOFTWARE/Microsoft/Windows/CurrentVersion/Run" /v wsl',
        capture=True
    )
    return code == 0


def install_wsl():
    """安裝 WSL2 + Ubuntu 22.04"""
    log_info("正在啟用 WSL2 功能...")

    # 1. 啟用 WSL 功能
    run_cmd("dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart", check=True)
    run_cmd("dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart", check=True)

    # 2. 設定 WSL2 為預設
    log_info("設定 WSL2 為預設版本...")
    run_cmd("wsl --set-default-version 2", check=True)

    # 3. 安裝 Ubuntu 22.04
    log_info("正在安裝 Ubuntu 22.04 LTS（約 1-2GB，第一次需要數分鐘）...")
    log_info("請在跳出視窗時選擇建立帳號和密碼。")
    code, out, err = run_cmd("wsl --install -d Ubuntu-22.04", capture=True)
    if code != 0:
        log_error(f"安裝失敗：{err}")
        return False

    log_ok("Ubuntu 22.04 安裝完成！")
    log_info("請在 Ubuntu 視窗中設定您的使用者名稱和密碼")
    time.sleep(2)
    return True


# ─── 在 WSL 中執行 bash 指令 ───
def wsl_exec(command: str, capture=True) -> tuple:
    """
    在 WSL 中執行 bash 指令
    用法：wsl_exec("curl -sL https://.../install.sh | bash")
    """
    return run_cmd(f'wsl -d Ubuntu-22.04 -- bash -c "{command}"', capture=capture)


def wsl_file_exists(path: str) -> bool:
    """檢查 WSL 中檔案是否存在"""
    code, _, _ = wsl_exec(f'test -f "{path}" && echo exists || echo missing')
    return "exists" in code


# ─── 主安裝流程 ───
def install_ros2_environment():
    print("")
    print("╔═══════════════════════════════════════════╗")
    print("║   跨樓層 AMR 環境安裝精靈                  ║")
    print("║   ROS2 Humble × Gazebo Harmonic            ║")
    print("╚═══════════════════════════════════════════╝")
    print("")

    # Step 1: Admin check
    if not is_admin():
        log_error("需要系統管理員權限！")
        log_info("請在開始選單搜尋「PowerShell」，按右鍵選擇「系統管理員」，")
        log_info("然後執行：")
        print("")
        print("    python crossfloor_setup.py")
        print("")
        input("按 Enter 離開...")
        return

    log_info("管理員權限確認")
    log_ok("準備就緒")

    # Step 2: WSL check
    print("")
    log_info("檢查 WSL2 環境...")

    if not is_wsl_installed():
        log_warn("WSL2 未安裝，即將開始安裝...")
        if not install_wsl():
            log_error("WSL 安裝失敗，請稍後重試")
            input("按 Enter 離開...")
            return
    else:
        log_ok("WSL2 已安裝")

    # Step 3: Ubuntu check
    print("")
    log_info("檢查 Ubuntu 22.04...")

    if not is_ubuntu_installed():
        log_warn("Ubuntu 22.04 未安裝，正在安裝...")
        install_wsl()
    else:
        log_ok("Ubuntu 22.04 已安裝")

    # Step 4: 等待 WSL 啟動
    print("")
    log_info("等待 WSL 啟動...")
    time.sleep(3)

    # Step 5: Clone repo 並執行安裝
    print("")
    log_info("Clone 程式碼...")

    # 安裝指引腳本 URL（raw GitHub）
    repo_url = "https://github.com/Oren2026/special_topic"
    branch = "ros2-crossfloor-amr"
    install_script_url = (
        f"{repo_url}/raw/{branch}/ros2-crossfloor-amr/installer/install.sh"
    )
    workspace_dir = "/home/ros2_ws"

    # 先 clone repo
    clone_cmd = (
        f"cd /tmp && "
        f"git clone -b {branch} --depth 1 {repo_url} {workspace_dir} 2>&1"
    )
    code, out, err = wsl_exec(clone_cmd)
    if code != 0:
        log_error(f"Clone 失敗：{err}")
        input("按 Enter 離開...")
        return

    log_ok("程式碼已Clone")

    # Step 6: 執行安裝腳本
    print("")
    log_info("開始安裝 ROS2 環境（約 30-60 分鐘）...")
    log_warn("請保持網路連線，不要關閉視窗")
    print("")

    install_cmd = (
        f"cd {workspace_dir}/ros2-crossfloor-amr && "
        f"chmod +x installer/*.sh installer/lib/*.sh && "
        f"bash installer/install.sh 2>&1"
    )
    code, out, err = wsl_exec(install_cmd, capture=False)

    if code == 0:
        print("")
        print("╔═══════════════════════════════════════════╗")
        print("║   ✅ 安裝完成！                            ║")
        print("╚═══════════════════════════════════════════╝")
        print("")
        log_ok("在 Ubuntu 中執行以下指令啟動：")
        print("    source ~/.bashrc")
        print("    cdr")
        print("    ./installer/launcher.sh")
    else:
        print("")
        log_error("安裝過程有錯誤，請查看上方輸出或查看 log")
        print(f"錯誤摘要：{err[-500:]}")

    input("按 Enter 結束...")


# ─── 入口 ───
if __name__ == "__main__":
    # 避免 Python 自動關閉
    import atexit

    def cleanup():
        print("")
        print("安裝精靈已結束。")
        input("按 Enter 關閉...")

    try:
        install_ros2_environment()
    except KeyboardInterrupt:
        print("")
        log_warn("安裝已中斷")
    except Exception as e:
        log_error(f"發生未預期錯誤：{e}")
        input("按 Enter 結束...")