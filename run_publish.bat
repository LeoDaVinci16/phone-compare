@echo off
REM ---------------------------------------------------------------------------
REM  Double-click to update the website copy of the report: docs\index.html
REM  Then commit and push; GitHub Pages serves the docs folder as it is.
REM  (Same report as run_report.bat, with the data in data\ at this moment.)
REM ---------------------------------------------------------------------------
cd /d "%~dp0"

set "ACT="
for %%D in ("%USERPROFILE%\anaconda3" "%USERPROFILE%\miniconda3" "%LOCALAPPDATA%\anaconda3" "%LOCALAPPDATA%\miniconda3" "C:\ProgramData\anaconda3" "C:\ProgramData\miniconda3") do (
    if not defined ACT if exist "%%~D\Scripts\activate.bat" set "ACT=%%~D\Scripts\activate.bat"
)
if not defined ACT (
    echo Could not find Anaconda. Open "Anaconda Prompt", go to this folder and run:  phone-compare --no-plots
    pause
    exit /b 1
)
call "%ACT%" phone-compare || (
    echo The environment "phone-compare" does not exist yet. Follow INSTALL.md, step 3.
    pause
    exit /b 1
)

phone-compare --no-plots %*
if errorlevel 1 (
    pause
    exit /b 1
)
if not exist docs mkdir docs
copy /y "output\report.html" "docs\index.html" >nul
type nul > "docs\.nojekyll"
echo.
echo Website updated: docs\index.html
echo Now publish it:   git add docs ^&^& git commit -m "Update website" ^&^& git push
pause
