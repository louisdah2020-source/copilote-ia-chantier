"""
tests/test_agents.py
Tests unitaires de l'orchestration multi-agents et des exports PDF / Excel.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.ingestion import ExcelIngestionEngine
from core.calculations import ConstructionCalculationEngine
from core.alert_engine import AlertEngine
from ai_agents.orchestrator import CopilotOrchestrator
from reports.pdf_generator import PDFReportGenerator
from reports.excel_exporter import ExcelExporter


def test_agents_and_exports():
    s4_file = ROOT_DIR / "data" / "samples" / "Suivi_Chantier_S4_2026.xlsx"
    engine = ExcelIngestionEngine(str(s4_file))
    data = engine.load_all()

    calc = ConstructionCalculationEngine(data)
    kpi = calc.calculate_all(date_analyse="2027-02-08")

    alert_engine = AlertEngine(kpi)
    alerts = alert_engine.evaluate_all(today_str="2027-02-08")

    # 1. Test Orchestrateur
    orchestrator = CopilotOrchestrator()
    diagnosis = orchestrator.run_full_diagnosis(kpi)
    assert "report_generator" in diagnosis
    assert "cost_controller" in diagnosis
    assert "planning_engineer" in diagnosis

    # 2. Test Q&A
    ans_delay = orchestrator.answer_question("Pourquoi avons-nous du retard ?", kpi, diagnosis)
    assert "Planning Engineer" in ans_delay or "retard" in ans_delay.lower()

    ans_cost = orchestrator.answer_question("Quel lot coûte le plus cher ?", kpi, diagnosis)
    assert "Gros" in ans_cost or "Cost Controller" in ans_cost

    # 3. Test Génération PDF
    pdf_out = ROOT_DIR / "data" / "exports" / "test_report.pdf"
    pdf_gen = PDFReportGenerator(kpi, alerts, diagnosis)
    pdf_path = pdf_gen.generate(str(pdf_out))
    assert Path(pdf_path).exists() and Path(pdf_path).stat().st_size > 1000

    # 4. Test Export Excel consolidé
    xlsx_out = ROOT_DIR / "data" / "exports" / "test_consolidated.xlsx"
    ex_exporter = ExcelExporter(str(s4_file), kpi, alerts)
    ex_path = ex_exporter.export(str(xlsx_out))
    assert Path(ex_path).exists() and Path(ex_path).stat().st_size > 1000

    print("[OK] Test Agents & Exports : Succes !")


if __name__ == "__main__":
    test_agents_and_exports()
