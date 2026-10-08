@echo off
chcp 65001 > nul
title Copilote IA - Pilotage de Chantier BTP

echo ====================================================================
echo             🏗️ COPILOTE IA - PILOTAGE DE CHANTIER BTP
echo ====================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creation de l'environnement virtuel avec Python 3.12...
    "C:\Users\LOUIS\.local\bin\uv.exe" venv .venv --python 3.12
    if errorlevel 1 (
        echo Erreur lors de la creation de l'environnement virtuel.
        pause
        exit /b 1
    )
    
    echo [2/3] Installation des dependances (pandas, openpyxl, streamlit, plotly, reportlab)...
    "C:\Users\LOUIS\.local\bin\uv.exe" pip install -r requirements.txt --python .venv
    if errorlevel 1 (
        echo Erreur lors de l'installation des dependances.
        pause
        exit /b 1
    )
) else (
    echo [1/2] Environnement virtuel detecte.
)

echo [2/2] Lancement de l'application Web interactive (Streamlit)...
echo.
echo L'application va s'ouvrir dans votre navigateur web (http://localhost:8501)...
echo Appuyez sur Ctrl+C dans ce terminal pour arreter le serveur.
echo.

.venv\Scripts\streamlit.exe run web\app.py --server.headless=false --browser.gatherUsageStats=false

pause
