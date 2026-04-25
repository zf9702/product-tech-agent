@echo off
chcp 65001 >nul 2>&1
echo.
echo ╔══════════════════════════════════════════════╗
echo ║   产品技术资料管理系统 - 启动脚本            ║
echo ╚══════════════════════════════════════════════╝
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查并安装依赖
if not exist ".venv" (
    echo [1/3] 创建虚拟环境...
    python -m venv .venv
)

echo [2/3] 激活虚拟环境并安装依赖...
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo [3/3] 启动服务...
echo.
echo ╔══════════════════════════════════════════════╗
echo ║  服务地址: http://localhost:8080             ║
echo ║  局域网:   http://你的IP:8080               ║
echo ║  默认账号: admin / admin123                  ║
echo ║  按 Ctrl+C 停止服务                         ║
echo ╚══════════════════════════════════════════════╝
echo.

python app.py

pause
