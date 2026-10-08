"""
tests/test_ingestion.py
Tests unitaires de l'ingestion et de la validation des classeurs Excel.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.ingestion import ExcelIngestionEngine
from core.validation import DataValidationEngine


def test_ingestion_and_validation():
    s4_file = ROOT_DIR / "data" / "samples" / "Suivi_Chantier_S4_2026.xlsx"
    assert s4_file.exists(), "Le fichier d'exemple S4 doit exister"

    engine = ExcelIngestionEngine(str(s4_file))
    inspection = engine.inspect_file()
    assert inspection["has_all_sheets"], f"Toutes les 9 feuilles doivent être présentes. Manquantes: {inspection['missing_sheets']}"

    data = engine.load_all()
    assert data["parametres"].projet == "Immeuble R+4"
    assert len(data["lots"]) == 8
    assert len(data["planning"]) >= 10
    assert len(data["budget"]) >= 10
    assert len(data["depenses"]) >= 10
    assert len(data["materiaux"]) >= 5

    validator = DataValidationEngine(data)
    report = validator.validate()
    assert report.total_lignes > 30
    assert report.nb_lots == 8
    print("[OK] Test Ingestion & Validation : Succes !")


if __name__ == "__main__":
    test_ingestion_and_validation()
