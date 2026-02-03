@echo off
echo ========================================================
echo        X Article 手动登录启动器 (无自动化干扰)
echo ========================================================
echo.
echo 正在启动 Chrome...
echo 使用数据目录: %~dp0chrome_data_mirror
echo.
echo [操作指南]
echo 1. 浏览器打开后，请访问 x.com
echo 2. 登录你的账号 (现在应该不会提示不安全了)
echo 3. 确保能打开 https://x.com/compose/articles
echo 4. 登录成功后，关闭浏览器窗口
echo.

:: 查找 Chrome 路径
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else (
    echo ❌ 未找到 Chrome，请手动修改脚本指定路径
    pause
    exit /b
)

:: 启动 Chrome，指定用户目录，不带任何自动化参数，但强制直连
"%CHROME_PATH%" --user-data-dir="%~dp0chrome_data_mirror" --no-proxy-server --no-first-run --no-default-browser-check "https://x.com/i/flow/login"

echo 浏览器已关闭。
echo 现在可以运行 python auto_publish.py 了！
pause
