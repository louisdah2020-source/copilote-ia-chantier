"""
streamlit_app.py
Point d'entrée racine pour le déploiement sur Streamlit Community Cloud.
Redirige automatiquement vers l'application principale située dans web/app.py.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from web.app import main

if __name__ == "__main__":
    main()
