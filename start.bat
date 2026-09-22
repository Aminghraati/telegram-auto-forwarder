@echo off
chcp 65001 >nul
title Telegram Auto Forwarder
cd /d "%~dp0"
echo ============================================
echo   Telegram Auto Forwarder - start
echo   Stop: Ctrl+C or send /stop in Saved Messages
echo ============================================
python send_to_folder.py
pause
