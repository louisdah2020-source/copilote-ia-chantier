"""
tests/test_calculations.py
Tests unitaires des calculs des KPI de chantier et du moteur d'alertes.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.ingestion import ExcelIngestionEngine
from core.validation import DataValidationEngine
from core.calculations import ConstructionCalculationEngine
from core.alert_engine import AlertEngine


def test_calculations_and_alerts():
    s4_file = ROOT_DIR / "data" / "samples" / "Suivi_Chantier_S4_2026.xlsx"
    engine = ExcelIngestionEngine(str(s4_file))
    data = engine.load_all()

    calc = ConstructionCalculationEngine(data)
    kpi = calc.calculate_all(date_analyse="2027-02-08")

    # Vérifications des KPI financiers
    assert kpi.finances.budget_revise == 350_000_000
    assert kpi.finances.depenses_engagees > 150_000_000
    assert 50.0 <= kpi.finances.pct_consommation_budget <= 80.0

    # Vérifications de l'avancement physique
    assert 50.0 <= kpi.chantier.avancement_physique_global <= 80.0
    assert kpi.chantier.retard_global_jours >= 6

    # Vérifications des alertes
    alert_engine = AlertEngine(kpi)
    alerts = alert_engine.evaluate_all(today_str="2027-02-08")
    assert len(kpi.alertes_critiques) >= 2, "Au moins 2 alertes critiques doivent être déclenchées"
    
    # Vérifier qu'une alerte surconsommation acier est présente
    acier_alerts = [a for a in alerts if "acier" in a.description.lower() or "acier" in a.action_recommandee.lower()]
    assert len(acier_alerts) > 0, "L'alerte acier doit être présente"

    print("[OK] Test Calculations & Alerts : Succes !")


if __name__ == "__main__":
    test_calculations_and_alerts()
