@echo off
REM ---------------------------------------------------------------------------
REM  Double-click this file to open the phone comparison APP in your browser.
REM  In the app you can add phones, choose which phones/specs to compare,
REM  and save that choice. Keep this black window open while you use it;
REM  close it (or press Ctrl+C) to stop the app.
REM ---------------------------------------------------------------------------
cd /d "%~dp0"
title Phone comparison app (close this window to stop)

set "ACT="
for %%D in ("%USERPROFILE%\anaconda3" "%USERPROFILE%\miniconda3" "%LOCALAPPDATA%\anaconda3" "%LOCALAPPDATA%\miniconda3" "C:\ProgramData\anaconda3" "C:\ProgramData\miniconda3") do (
    if not defined ACT if exist "%%~D\Scripts\activate.bat" set "ACT=%%~D\Scripts\activate.bat"
)
if not defined ACT (
    echo Could not find Anaconda. Open "Anaconda Prompt", go to this folder and run:  phone-compare --serve
    pause
    exit /b 1
)
call "%ACT%" phone-compare || (
    echo The environment "phone-compare" does not exist yet. Follow INSTALL.md, step 3.
    pause
    exit /b 1
)

phone-compare --serve %*
pause
