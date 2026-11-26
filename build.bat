@echo off
chcp 65001 >nul
title QASSIMZ Organizer - Build
echo === 1/3 Installing requirements ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller || goto :err
echo === 2/3 Building the app ===
python -m PyInstaller --noconfirm --clean qassimz-organizer.spec || goto :err
echo === 3/3 Building the installer ===
if not exist installer\Arabic.isl curl -L -o installer\Arabic.isl https://raw.githubusercontent.com/jrsoftware/issrc/main/Files/Languages/Unofficial/Arabic.isl
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo Inno Setup 6 not found. Install it from https://jrsoftware.org/isdl.php
  echo The app itself is ready in: dist\QASSIMZ Organizer\
  pause & exit /b 0
)
%ISCC% installer\setup.iss || goto :err
echo.
echo DONE  ^>^>  dist\QASSIMZ-Organizer-Setup-1.1.0.exe
pause & exit /b 0
:err
echo BUILD FAILED
pause & exit /b 1
