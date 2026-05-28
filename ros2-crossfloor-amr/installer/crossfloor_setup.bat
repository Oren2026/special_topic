@echo off
:: crossfloor_setup.bat — WSL2 + ROS2 安裝工具啟動器
:: 用途：双击此文件即开女口安装向导，不需要打开终端
:: 需配合 crossfloor_setup.py 使用

title 跨樓層 AMR 環境安裝精靈

echo.
echo =============================================
echo   跨樓層 AMR 環境安裝精靈
echo   ROS2 Humble x Gazebo Harmonic
echo =============================================
echo.
echo 正在啟動 Python 安裝程式...
echo.

:: 檢查是否有 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 找不到 Python，請先安裝 Python 3.10+
    echo.
    echo 建議至 https://www.python.org/downloads/ 下戴安裝
    echo 安裝時請勾選「Add Python to PATH」
    echo.
    pause
    exit /b 1
)

:: 執行 Python 安裝程式
python "%~dp0crossfloor_setup.py"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 安裝程式異常結束
    pause
)