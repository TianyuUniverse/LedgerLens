@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 软件启动后，请在浏览器打开 http://127.0.0.1:8765
echo 使用时请保持此窗口打开；按 Ctrl+C 停止服务。
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 app.py
) else (
  python app.py
)
pause
