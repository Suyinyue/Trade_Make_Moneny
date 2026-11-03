@echo off
cd /d "%~dp0"

echo 当前目录: %CD%

call venv\Scripts\activate
python get_eastmoney_imformation.py
pause