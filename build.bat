@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Kafa Kafaya - EXE olusturucu

echo.
echo  ==== KAFA KAFAYA - EXE OLUSTURUCU ====
echo  Bu islem internetli bir Windows bilgisayarda BIR KEZ yapilir.
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo  [HATA] Python bulunamadi!
    echo  https://www.python.org/downloads/ adresinden Python 3.12 kurun.
    echo  Kurulumda "Add python.exe to PATH" kutusunu isaretlemeyi unutmayin.
    pause
    exit /b 1
)

echo  [1/3] Gerekli paketler kuruluyor...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo  [HATA] Paketler kurulamadi. Internet baglantisini kontrol edin.
    pause
    exit /b 1
)

echo  [2/3] Exe olusturuluyor (1-2 dakika surebilir)...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name KafaKafaya --icon assets\icon.ico --add-data "assets;assets" main.py
if errorlevel 1 (
    echo  [HATA] Exe olusturulamadi.
    pause
    exit /b 1
)

echo  [3/3] Kopyalaniyor...
copy /y dist\KafaKafaya.exe KafaKafaya.exe >nul

echo.
echo  TAMAM!  KafaKafaya.exe bu klasorde hazir.
echo  Bu tek dosyayi iki bilgisayara kopyalayip calistirabilirsiniz.
echo.
pause
