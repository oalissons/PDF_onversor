@echo off
cd /d "%~dp0"
python converter_pdf_para_html.py "%USERPROFILE%\Desktop\ORDENS"
echo.
pause
