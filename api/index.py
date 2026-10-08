"""
api/index.py
Point d'entrée Serverless Vercel pour le Copilote IA de Chantier BTP.
Expose l'API REST FastAPI, le téléversement dynamique de classeurs Excel,
et sert l'interface web responsive complète.
"""
import sys
import io
import os
import json
import uuid
import re
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
from pydantic import BaseModel

# Configuration du PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.models import KPISummary
from core.ingestion import ExcelIngestionEngine
from core.validation import DataValidationEngine
from core.calculations import ConstructionCalculationEngine
from core.alert_engine import AlertEngine
from core.excel_generator import create_sample_s4_workbook, create_sample_s1_workbook, create_template_workbook
from ai_agents.orchestrator import CopilotOrchestrator
from reports.pdf_generator import PDFReportGenerator
from reports.excel_exporter import ExcelExporter


app = FastAPI(title="Copilote IA Chantier BTP", version="1.0.0")


@app.middleware("http")
async def vercel_routing_middleware(request: Request, call_next):
    """
    Intercepte et normalise les chemins réécrits par Vercel Serverless.
    Vercel transmet l'URL d'origine dans x-matched-path.
    """
    matched_path = request.headers.get("x-matched-path")
    if matched_path:
        request.scope["path"] = matched_path
    elif request.scope.get("path") in ("/api/index", "/api/index/", "/api", "/api/"):
        request.scope["path"] = "/"
    return await call_next(request)


# Cache global en mémoire
DATA_CACHE = {}


def _safe_download_name(value: str, fallback: str = "chantier") -> str:
    """Produit un nom de fichier sans séparateur ni caractère d'en-tête dangereux."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value or "").strip("_")[:80]
    return cleaned or fallback


def get_current_data(filepath: Optional[str] = None, force_refresh: bool = False):
    """Charge et calcule les indicateurs en mémoire cache."""
    target_path = filepath
    if not target_path or not Path(target_path).exists():
        s4_sample = ROOT_DIR / "data" / "samples" / "Suivi_Chantier_S4_2026.xlsx"
        if not s4_sample.exists():
            s4_sample.parent.mkdir(parents=True, exist_ok=True)
            create_sample_s4_workbook(str(s4_sample))
        target_path = str(s4_sample)

    cache_key = str(target_path)
    if not force_refresh and cache_key in DATA_CACHE:
        return DATA_CACHE[cache_key]

    ingestion = ExcelIngestionEngine(target_path)
    data = ingestion.load_all()

    validator = DataValidationEngine(data)
    val_report = validator.validate()

    calc = ConstructionCalculationEngine(data)
    kpi = calc.calculate_all()

    alert_engine = AlertEngine(kpi, val_report)
    alerts = alert_engine.evaluate_all(today_str=kpi.date_analyse)

    orchestrator = CopilotOrchestrator()
    diagnosis = orchestrator.run_full_diagnosis(kpi, val_report)

    result = {
        "path": target_path,
        "data": data,
        "val_report": val_report,
        "kpi": kpi,
        "alerts": alerts,
        "diagnosis": diagnosis,
        "orchestrator": orchestrator
    }
    DATA_CACHE[cache_key] = result
    return result


def _format_kpi_payload(state):
    kpi: KPISummary = state["kpi"]
    diag = state["diagnosis"]
    val = state["val_report"]
    return {
        "filepath": state["path"],
        "projet": kpi.parametres.projet,
        "client": kpi.parametres.client,
        "localisation": kpi.parametres.localisation,
        "ingenieur": kpi.parametres.ingenieur,
        "date_analyse": kpi.date_analyse,
        "devise": kpi.parametres.devise,
        "avancement_physique": kpi.chantier.avancement_physique_global,
        "avancement_prevu": kpi.chantier.avancement_prevu_global,
        "ecart_avancement": kpi.chantier.ecart_avancement_global,
        "retard_jours": kpi.chantier.retard_global_jours,
        "budget_initial": kpi.finances.budget_initial,
        "budget_revise": kpi.finances.budget_revise,
        "depenses_engagees": kpi.finances.depenses_engagees,
        "depenses_realisees": kpi.finances.depenses_realisees,
        "reste_a_depenser": kpi.finances.reste_a_depenser,
        "pct_consommation": kpi.finances.pct_consommation_budget,
        "eac": diag["cost_controller"]["eac_projection"],
        "repartition_lots": kpi.repartition_lots,
        "materiaux": kpi.materiaux_alertes,
        "alertes": [
            {
                "type": a.type_alerte,
                "lot": a.lot,
                "gravite": a.gravite,
                "description": a.description,
                "action": a.action_recommandee
            }
            for a in state["alerts"]
        ],
        "nb_critiques": len(kpi.alertes_critiques),
        "nb_moyennes": len(kpi.alertes_moyennes),
        "nb_normales": len(kpi.alertes_normales),
        "synthese_executive": diag["report_generator"]["synthese_executive"],
        "lignes_auditees": val.total_lignes,
        "lots_detectes": val.nb_lots,
        "taches_detectees": val.nb_taches,
        "fournisseurs_detectes": val.nb_fournisseurs
    }


class ChatRequest(BaseModel):
    question: str
    filepath: Optional[str] = None


@app.get("/api/kpi")
@app.get("/kpi")
def get_kpi_api(file: Optional[str] = None):
    """Retourne les métriques calculées et les diagnostics du chantier."""
    state = get_current_data(file)
    return _format_kpi_payload(state)


@app.post("/api/upload")
@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    """
    Permet à l'ingénieur de déposer son propre classeur Excel de chantier.
    Lit, valide, recalcule et renvoie immédiatement l'état dynamique mis à jour.
    """
    filename = file.filename or ""
    if Path(filename).suffix.lower() not in (".xlsx", ".xlsm"):
        raise HTTPException(status_code=400, detail="Format invalide. Veuillez déposer un fichier .xlsx ou .xlsm.")

    # Déterminer un répertoire temporaire d'écriture (supporte Vercel /tmp)
    target_dir = Path("/tmp") if Path("/tmp").exists() and os.access("/tmp", os.W_OK) else ROOT_DIR / "data" / "uploads"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    clean_name = Path(filename).name.replace(" ", "_")
    target_path = target_dir / f"user_{uuid.uuid4().hex}_{clean_name}"
    
    max_upload_bytes = 25 * 1024 * 1024
    content = await file.read(max_upload_bytes + 1)
    if len(content) > max_upload_bytes:
        raise HTTPException(status_code=413, detail="Le classeur dépasse la limite de 25 Mo.")
    with open(target_path, "wb") as f_out:
        f_out.write(content)

    try:
        state = get_current_data(str(target_path), force_refresh=True)
        return {
            "success": True,
            "message": f"Classeur '{file.filename}' ingéré et analysé avec succès !",
            "data": _format_kpi_payload(state)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'ingestion du classeur : {str(e)}")


@app.get("/api/dataset/{dataset_id}")
def load_sample_dataset(dataset_id: str):
    """Bascule entre les jeux de données de test S1 et S4."""
    if dataset_id == "s1":
        p = ROOT_DIR / "data" / "samples" / "Suivi_Chantier_S1_2026.xlsx"
        if not p.exists():
            create_sample_s1_workbook(str(p))
    else:
        p = ROOT_DIR / "data" / "samples" / "Suivi_Chantier_S4_2026.xlsx"
        if not p.exists():
            create_sample_s4_workbook(str(p))

    state = get_current_data(str(p), force_refresh=True)
    return {
        "success": True,
        "data": _format_kpi_payload(state)
    }


@app.post("/api/chat")
@app.post("/chat")
def chat_api(req: ChatRequest):
    """Point d'accès du Copilote IA conversationnel."""
    state = get_current_data(req.filepath)
    orchestrator: CopilotOrchestrator = state["orchestrator"]
    kpi: KPISummary = state["kpi"]
    diagnosis = state["diagnosis"]

    reponse = orchestrator.answer_question(req.question, kpi, diagnosis)
    return {"question": req.question, "reponse": reponse}


@app.get("/api/template")
def download_template():
    """Télécharge le modèle Excel vierge officiel."""
    tpl_path = ROOT_DIR / "data" / "templates" / "Suivi_Chantier_Template.xlsx"
    if not tpl_path.exists():
        tpl_path.parent.mkdir(parents=True, exist_ok=True)
        create_template_workbook(str(tpl_path))
        
    with open(tpl_path, "rb") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Suivi_Chantier_Template.xlsx"'}
    )


@app.get("/api/export/pdf")
@app.get("/export/pdf")
def export_pdf(file: Optional[str] = None):
    """Génère et télécharge le rapport PDF de direction."""
    state = get_current_data(file)
    kpi = state["kpi"]
    alerts = state["alerts"]
    diagnosis = state["diagnosis"]

    buffer = io.BytesIO()
    pdf_gen = PDFReportGenerator(kpi, alerts, diagnosis)
    pdf_gen.generate(buffer)
    buffer.seek(0)

    filename = f"Rapport_Chantier_{_safe_download_name(kpi.parametres.projet)}.pdf"
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/export/excel")
@app.get("/export/excel")
def export_excel(file: Optional[str] = None):
    """Génère et télécharge le classeur Excel consolidé."""
    state = get_current_data(file)
    kpi = state["kpi"]
    alerts = state["alerts"]
    src_path = state["path"]

    buffer = io.BytesIO()
    exporter = ExcelExporter(src_path, kpi, alerts)
    exporter.export(buffer)
    buffer.seek(0)

    filename = f"Suivi_Chantier_Consolide_{_safe_download_name(kpi.parametres.projet)}.xlsx"
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/api/index", response_class=HTMLResponse)
@app.get("/api/index/", response_class=HTMLResponse)
def index_html():
    """Sert l'application web monopage dynamique et interactive avec glisser-déposer de classeur."""
    state = get_current_data()
    initial_kpi = _format_kpi_payload(state)
    initial_json = json.dumps(initial_kpi, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Copilote IA — Chantier BTP</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: #F8FAFC; }}
        .badge-red {{ background: #FEE2E2; color: #991B1B; }}
        .badge-amber {{ background: #FEF3C7; color: #92400E; }}
        .badge-green {{ background: #DCFCE7; color: #166534; }}
        .dropzone-active {{ border-color: #1E3A8A !important; background-color: #EFF6FF !important; }}
    </style>
</head>
<body class="text-slate-800 antialiased">

    <!-- Navbar -->
    <header class="bg-blue-950 text-white shadow-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-3.5 flex flex-wrap justify-between items-center gap-4">
            <div class="flex items-center gap-3">
                <span class="text-3xl">🏗️</span>
                <div>
                    <h1 class="text-lg font-bold tracking-tight">COPILOTE IA — CHANTIER BTP</h1>
                    <p id="navSub" class="text-xs text-blue-200">Chargement des données...</p>
                </div>
            </div>

            <!-- Actions Rapides & Exports -->
            <div class="flex flex-wrap items-center gap-2 text-xs">
                <!-- Bouton Déposer Excel -->
                <label for="excelFileInput" class="cursor-pointer bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold px-3 py-2 rounded-lg shadow transition flex items-center gap-1.5">
                    <span>⬆️ Déposer mon Excel</span>
                    <input type="file" id="excelFileInput" accept=".xlsx,.xlsm" class="hidden" onchange="handleFileUpload(event)">
                </label>

                <!-- Sélecteur d'échantillons -->
                <select id="sampleSelect" onchange="switchDataset(this.value)" class="bg-blue-900 border border-blue-800 text-white text-xs rounded-lg px-2.5 py-2 font-medium focus:outline-none">
                    <option value="s4">Semaine 4 (Dérives réelles)</option>
                    <option value="s1">Semaine 1 (Démarrage)</option>
                </select>

                <!-- Télécharger Modèle Vierge -->
                <a href="/api/template" class="bg-blue-900 hover:bg-blue-800 text-blue-100 px-2.5 py-2 rounded-lg transition border border-blue-800 flex items-center gap-1">
                    📥 Modèle Vierge
                </a>

                <!-- Télécharger PDF -->
                <a id="btnPdfExport" href="/api/export/pdf" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-3 py-2 rounded-lg shadow transition flex items-center gap-1">
                    📄 PDF Direction
                </a>

                <!-- Télécharger Excel -->
                <a id="btnExcelExport" href="/api/export/excel" class="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-3 py-2 rounded-lg shadow transition flex items-center gap-1">
                    📊 Excel Enrichi
                </a>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-6">

        <!-- Notification / Bannière d'ingestion -->
        <div id="uploadBanner" class="hidden mb-6 p-4 rounded-xl border transition flex items-center justify-between"></div>

        <!-- Zone Glisser-Déposer Rapide -->
        <div id="dropzone" class="border-2 border-dashed border-slate-300 hover:border-blue-800 bg-white rounded-xl p-5 mb-6 text-center transition cursor-pointer" onclick="document.getElementById('excelFileInput').click()">
            <div class="flex flex-col items-center justify-center gap-2">
                <span class="text-3xl">📂</span>
                <p class="text-sm font-semibold text-slate-700">Glissez-déposez ici votre classeur de suivi de chantier (<span class="text-blue-900 font-bold">.xlsx</span>)</p>
                <p class="text-xs text-slate-500">Ou cliquez pour parcourir vos fichiers • Détection automatique des 9 feuilles & calcul instantané</p>
            </div>
        </div>

        <!-- 4 KPI Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <!-- Avancement -->
            <div class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-900">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Avancement Physique</div>
                <div id="kpiAvancement" class="text-3xl font-bold text-blue-950 mt-1">-- %</div>
                <div id="kpiAvancementSub" class="text-xs text-slate-500 mt-2">Prévu: -- %</div>
            </div>

            <!-- Budget -->
            <div class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-600">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Budget Global HT</div>
                <div id="kpiBudget" class="text-3xl font-bold text-blue-950 mt-1">-- M</div>
                <div id="kpiBudgetSub" class="text-xs text-slate-500 mt-2">FCFA</div>
            </div>

            <!-- Dépenses -->
            <div class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Dépenses Engagées</div>
                <div id="kpiDepenses" class="text-3xl font-bold text-amber-600 mt-1">-- M</div>
                <div id="kpiDepensesSub" class="text-xs text-slate-500 mt-2">Consommé: -- %</div>
            </div>

            <!-- Délais -->
            <div class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-red-600">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Glissement Délais</div>
                <div id="kpiRetard" class="text-3xl font-bold text-red-600 mt-1">+-- j</div>
                <div id="kpiRetardSub" class="text-xs text-slate-500 mt-2">Chemin critique</div>
            </div>
        </div>

        <!-- Synthèse IA & Badges -->
        <div class="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6">
            <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
                <div class="flex items-center gap-2">
                    <span class="text-xl">🤖</span>
                    <h2 class="font-bold text-blue-950 text-base">Diagnostic Automatique de l'Orchestrateur IA</h2>
                </div>
                <div class="flex gap-2">
                    <span id="badgeCrit" class="badge-red text-xs font-semibold px-2.5 py-1 rounded-md">🔴 0 critiques</span>
                    <span id="badgeMoy" class="badge-amber text-xs font-semibold px-2.5 py-1 rounded-md">🟠 0 à surveiller</span>
                    <span id="badgeNorm" class="badge-green text-xs font-semibold px-2.5 py-1 rounded-md">🟢 0 normaux</span>
                </div>
            </div>
            <p id="iaSynthese" class="text-sm text-slate-700 leading-relaxed">Chargement du diagnostic...</p>
        </div>

        <!-- Navigation par Onglets -->
        <div class="border-b border-slate-200 mb-6 flex space-x-2 overflow-x-auto text-sm font-semibold">
            <button onclick="switchTab('tab-dashboard')" id="btn-tab-dashboard" class="tab-btn px-4 py-2.5 border-b-2 border-blue-900 text-blue-900">📊 Dashboard</button>
            <button onclick="switchTab('tab-lots')" id="btn-tab-lots" class="tab-btn px-4 py-2.5 border-b-2 border-transparent text-slate-500 hover:text-slate-700">🏗️ Avancement par Lot</button>
            <button onclick="switchTab('tab-materiaux')" id="btn-tab-materiaux" class="tab-btn px-4 py-2.5 border-b-2 border-transparent text-slate-500 hover:text-slate-700">📦 Matériaux & Stocks</button>
            <button onclick="switchTab('tab-alertes')" id="btn-tab-alertes" class="tab-btn px-4 py-2.5 border-b-2 border-transparent text-slate-500 hover:text-slate-700">⚠️ Alertes Métiers</button>
            <button onclick="switchTab('tab-chat')" id="btn-tab-chat" class="tab-btn px-4 py-2.5 border-b-2 border-transparent text-slate-500 hover:text-slate-700">💬 Copilote IA (Chat)</button>
        </div>

        <!-- SECTION 1 : DASHBOARD (GRAPHIQUES) -->
        <div id="tab-dashboard" class="tab-content space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Graphique Avancement -->
                <div class="bg-white p-5 rounded-xl shadow-sm border border-slate-100">
                    <h3 class="font-bold text-slate-800 text-sm mb-4">Avancement Physique Réel vs Prévu par Lot (%)</h3>
                    <div class="relative h-64">
                        <canvas id="chartAvancement"></canvas>
                    </div>
                </div>

                <!-- Graphique Budget vs Dépenses -->
                <div class="bg-white p-5 rounded-xl shadow-sm border border-slate-100">
                    <h3 class="font-bold text-slate-800 text-sm mb-4">Budget Alloué vs Dépenses par Lot (FCFA)</h3>
                    <div class="relative h-64">
                        <canvas id="chartBudget"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- SECTION 2 : LOTS -->
        <div id="tab-lots" class="tab-content hidden">
            <div class="bg-white rounded-xl shadow-sm border border-slate-100 overflow-x-auto">
                <table class="w-full text-left text-sm text-slate-700 min-w-[650px]">
                    <thead class="bg-slate-50 text-xs font-semibold uppercase text-slate-500 border-b border-slate-200">
                        <tr>
                            <th class="p-3.5">Lot</th>
                            <th class="p-3.5">Budget</th>
                            <th class="p-3.5">Dépenses</th>
                            <th class="p-3.5">% Conso</th>
                            <th class="p-3.5">% Prévu</th>
                            <th class="p-3.5">% Réel</th>
                            <th class="p-3.5">Écart</th>
                            <th class="p-3.5">Statut</th>
                        </tr>
                    </thead>
                    <tbody id="lotsTableBody" class="divide-y divide-slate-100"></tbody>
                </table>
            </div>
        </div>

        <!-- SECTION 3 : MATERIAUX -->
        <div id="tab-materiaux" class="tab-content hidden">
            <div class="bg-white rounded-xl shadow-sm border border-slate-100 overflow-x-auto">
                <table class="w-full text-left text-sm text-slate-700 min-w-[650px]">
                    <thead class="bg-slate-50 text-xs font-semibold uppercase text-slate-500 border-b border-slate-200">
                        <tr>
                            <th class="p-3.5">Matériau</th>
                            <th class="p-3.5">Lot</th>
                            <th class="p-3.5">Quantité Prévue</th>
                            <th class="p-3.5">Consommée</th>
                            <th class="p-3.5">Stock</th>
                            <th class="p-3.5">Surconsommation</th>
                        </tr>
                    </thead>
                    <tbody id="materiauxTableBody" class="divide-y divide-slate-100"></tbody>
                </table>
            </div>
        </div>

        <!-- SECTION 4 : ALERTES -->
        <div id="tab-alertes" class="tab-content hidden space-y-3">
            <div id="alertesList" class="space-y-3"></div>
        </div>

        <!-- SECTION 5 : CHAT COPILOTE IA -->
        <div id="tab-chat" class="tab-content hidden">
            <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                <h3 class="font-bold text-blue-950 text-base mb-1">💬 Poser une Question à l'IA</h3>
                <p class="text-xs text-slate-500 mb-4">Les 6 agents (Data Analyst, Cost Controller, Planning Engineer, Material Controller, Risk Analyst, Report Generator) analysent vos données en direct.</p>
                
                <!-- Questions rapides -->
                <div class="flex flex-wrap gap-2 mb-4">
                    <button onclick="askPrompt('Pourquoi avons-nous du retard ?')" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-3 py-1.5 rounded-full font-medium transition">⏱️ Pourquoi le retard ?</button>
                    <button onclick="askPrompt('Quel lot coûte le plus cher ?')" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-3 py-1.5 rounded-full font-medium transition">💰 Quel lot coûte le plus cher ?</button>
                    <button onclick="askPrompt('Quel est le risque budgétaire ?')" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-3 py-1.5 rounded-full font-medium transition">🛡️ Quel est le risque budgétaire ?</button>
                    <button onclick="askPrompt('Où en est la consommation d\\'acier et le stock ?')" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-3 py-1.5 rounded-full font-medium transition">📦 Consommation d'acier & stocks</button>
                    <button onclick="askPrompt('Prépare mon rapport hebdomadaire.')" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-3 py-1.5 rounded-full font-medium transition">📑 Préparer le rapport</button>
                </div>

                <div class="flex gap-2">
                    <input type="text" id="chatInput" placeholder="Posez votre question d'ingénierie..." class="flex-1 border border-slate-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-900" onkeydown="if(event.key==='Enter') sendChat()">
                    <button onclick="sendChat()" id="sendBtn" class="bg-blue-950 hover:bg-blue-900 text-white font-semibold text-sm px-6 py-2.5 rounded-lg transition shadow">Envoyer</button>
                </div>

                <!-- Réponse -->
                <div id="chatResponseArea" class="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-xl hidden text-sm leading-relaxed text-slate-800 whitespace-pre-wrap"></div>
            </div>
        </div>

    </main>

<script>
        // Données d'état courant
        let currentData = {initial_json};
        function escapeHtml(value) {{
            return String(value ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
        }}
        let chartAvancementInstance = null;
        let chartBudgetInstance = null;

        // Glisser-Déposer
        const dropzone = document.getElementById('dropzone');
        ['dragenter', 'dragover'].forEach(eventName => {{
            dropzone.addEventListener(eventName, (e) => {{
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add('dropzone-active');
            }}, false);
        }});

        ['dragleave', 'drop'].forEach(eventName => {{
            dropzone.addEventListener(eventName, (e) => {{
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove('dropzone-active');
            }}, false);
        }});

        dropzone.addEventListener('drop', (e) => {{
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {{
                uploadFileObject(files[0]);
            }}
        }});

        function handleFileUpload(event) {{
            const file = event.target.files[0];
            if (file) {{
                uploadFileObject(file);
            }}
        }}

        async function uploadFileObject(file) {{
            const banner = document.getElementById('uploadBanner');
            banner.className = 'mb-6 p-4 rounded-xl border bg-blue-50 border-blue-200 text-blue-900 text-sm font-medium flex items-center justify-between';
            banner.innerHTML = `<span>⏳ Ingestion et analyse du classeur <b>${{escapeHtml(file.name)}}</b> en cours...</span>`;
            banner.classList.remove('hidden');

            const formData = new FormData();
            formData.append('file', file);

            try {{
                const res = await fetch('/api/upload', {{
                    method: 'POST',
                    body: formData
                }});
                const json = await res.json();
                if (res.ok && json.success) {{
                    currentData = json.data;
                    renderDashboard(currentData);
                    banner.className = 'mb-6 p-4 rounded-xl border bg-emerald-50 border-emerald-300 text-emerald-900 text-sm font-medium flex items-center justify-between';
                    banner.innerHTML = `<span>✓ <b>${{escapeHtml(file.name)}}</b> analysé avec succès ! (${{currentData.lignes_auditees}} lignes, ${{currentData.lots_detectes}} lots, ${{currentData.taches_detectees}} tâches recensées)</span><button onclick="document.getElementById('uploadBanner').classList.add('hidden')" class="text-xs text-emerald-700 font-bold hover:underline">Fermer</button>`;
                }} else {{
                    throw new Error(json.detail || 'Erreur inconnue lors du traitement.');
                }}
            }} catch (err) {{
                banner.className = 'mb-6 p-4 rounded-xl border bg-red-50 border-red-300 text-red-900 text-sm font-medium flex items-center justify-between';
                banner.innerHTML = `<span>❌ Échec du traitement : ${{escapeHtml(err.message)}}</span><button onclick="document.getElementById('uploadBanner').classList.add('hidden')" class="text-xs text-red-700 font-bold hover:underline">Fermer</button>`;
            }}
        }}

        async function switchDataset(val) {{
            const banner = document.getElementById('uploadBanner');
            try {{
                const res = await fetch('/api/dataset/' + val);
                const json = await res.json();
                if (json.success) {{
                    currentData = json.data;
                    renderDashboard(currentData);
                    banner.className = 'mb-6 p-4 rounded-xl border bg-slate-50 border-slate-200 text-slate-800 text-sm font-medium flex items-center justify-between';
                    banner.innerHTML = `<span>Échantillon <b>${{val === 's1' ? 'Semaine 1 (Démarrage)' : 'Semaine 4 (Dérives réelles)'}}</b> chargé avec succès.</span><button onclick="document.getElementById('uploadBanner').classList.add('hidden')" class="text-xs text-slate-600 font-bold hover:underline">Fermer</button>`;
                    banner.classList.remove('hidden');
                }}
            }} catch (err) {{
                console.error(err);
            }}
        }}

        function renderDashboard(data) {{
            // Metadonnées
            document.getElementById('navSub').innerText = `${{data.projet}} • ${{data.localisation}} • Arrêté du ${{data.date_analyse}}`;

            // Export links
            const pParam = encodeURIComponent(data.filepath || '');
            document.getElementById('btnPdfExport').href = `/api/export/pdf?file=${{pParam}}`;
            document.getElementById('btnExcelExport').href = `/api/export/excel?file=${{pParam}}`;

            // 4 KPI Cards
            document.getElementById('kpiAvancement').innerText = `${{data.avancement_physique}} %`;
            document.getElementById('kpiAvancementSub').innerHTML = `Prévu: <span class="font-medium">${{data.avancement_prevu}}%</span> • Écart: <span class="text-red-600 font-semibold">${{data.ecart_avancement > 0 ? '+' : ''}}${{data.ecart_avancement}} pts</span>`;

            document.getElementById('kpiBudget').innerText = `${{(data.budget_revise / 1e6).toFixed(1)}} M`;
            document.getElementById('kpiBudgetSub').innerText = `${{data.devise}} • Initial: ${{(data.budget_initial / 1e6).toFixed(1)}} M`;

            document.getElementById('kpiDepenses').innerText = `${{(data.depenses_engagees / 1e6).toFixed(1)}} M`;
            document.getElementById('kpiDepensesSub').innerHTML = `Consommé: <span class="font-bold">${{data.pct_consommation}}%</span> • Reste: ${{(data.reste_a_depenser / 1e6).toFixed(1)}} M`;

            document.getElementById('kpiRetard').innerText = `+${{data.retard_jours}} jours`;

            // Synthèse IA & Badges
            document.getElementById('badgeCrit').innerText = `🔴 ${{data.nb_critiques}} critiques`;
            document.getElementById('badgeMoy').innerText = `🟠 ${{data.nb_moyennes}} à surveiller`;
            document.getElementById('badgeNorm').innerText = `🟢 ${{data.nb_normales}} normaux`;
            document.getElementById('iaSynthese').innerText = data.synthese_executive;

            // Table Lots
            const tbodyLots = document.getElementById('lotsTableBody');
            tbodyLots.innerHTML = '';
            (data.repartition_lots || []).forEach(l => {{
                const ecart = l.ecart_avancement;
                const badgeClass = ecart < -5 ? 'badge-red' : (ecart < 0 ? 'badge-amber' : 'badge-green');
                const badgeLabel = ecart < -5 ? 'Retard' : (ecart < 0 ? 'À suivre' : 'Conforme');
                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-50/80';
                tr.innerHTML = `
                    <td class="p-3.5 font-medium text-slate-900">${{escapeHtml(l.lot)}}</td>
                    <td class="p-3.5">${{Number(l.budget).toLocaleString()}}</td>
                    <td class="p-3.5 font-semibold text-amber-600">${{Number(l.depenses).toLocaleString()}}</td>
                    <td class="p-3.5">${{l.pct_conso}}%</td>
                    <td class="p-3.5 text-slate-500">${{l.pct_prevu}}%</td>
                    <td class="p-3.5 font-bold text-blue-900">${{l.pct_reel}}%</td>
                    <td class="p-3.5 font-semibold ${{ecart < 0 ? 'text-red-600' : 'text-emerald-600'}}">${{ecart > 0 ? '+' : ''}}${{ecart}}%</td>
                    <td class="p-3.5"><span class="${{badgeClass}} text-xs font-semibold px-2 py-0.5 rounded">${{badgeLabel}}</span></td>
                `;
                tbodyLots.appendChild(tr);
            }});

            // Table Matériaux
            const tbodyMat = document.getElementById('materiauxTableBody');
            tbodyMat.innerHTML = '';
            (data.materiaux || []).forEach(m => {{
                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-50/80';
                tr.innerHTML = `
                    <td class="p-3.5 font-medium text-slate-900">${{escapeHtml(m.materiau)}}</td>
                    <td class="p-3.5">${{escapeHtml(m.lot)}}</td>
                    <td class="p-3.5">${{Number(m.quantite_prevue).toLocaleString()}} ${{escapeHtml(m.unite)}}</td>
                    <td class="p-3.5 font-medium">${{Number(m.quantite_consommee).toLocaleString()}} ${{escapeHtml(m.unite)}}</td>
                    <td class="p-3.5">${{Number(m.stock).toLocaleString()}} ${{escapeHtml(m.unite)}}</td>
                    <td class="p-3.5 font-bold ${{m.surconsommation_pct > 5 ? 'text-red-600' : 'text-slate-600'}}">${{m.surconsommation_pct > 0 ? '+' : ''}}${{m.surconsommation_pct}}%</td>
                `;
                tbodyMat.appendChild(tr);
            }});

            // Alertes
            const alertesContainer = document.getElementById('alertesList');
            alertesContainer.innerHTML = '';
            (data.alertes || []).forEach(a => {{
                const isCrit = a.gravite.includes('🔴');
                const div = document.createElement('div');
                div.className = `bg-white p-4 rounded-xl shadow-sm border-l-4 ${{isCrit ? 'border-red-600' : 'border-amber-500'}} flex flex-col gap-1`;
                div.innerHTML = `
                    <div class="flex justify-between items-center">
                         <span class="font-bold text-sm text-slate-900">[${{escapeHtml(a.type)}}] ${{escapeHtml(a.lot)}}</span>
                         <span class="${{isCrit ? 'badge-red' : 'badge-amber'}} text-xs font-semibold px-2 py-0.5 rounded">${{escapeHtml(a.gravite)}}</span>
                    </div>
                     <div class="text-sm text-slate-700 mt-1">${{escapeHtml(a.description)}}</div>
                     <div class="text-xs text-blue-900 font-semibold mt-1">Action recommandée : <span class="font-normal text-slate-600">${{escapeHtml(a.action)}}</span></div>
                `;
                alertesContainer.appendChild(div);
            }});

            // Rendu des graphiques
            renderCharts(data);
        }}

        function renderCharts(data) {{
            const labels = (data.repartition_lots || []).map(l => l.lot);
            const avPrevu = (data.repartition_lots || []).map(l => l.pct_prevu);
            const avReel = (data.repartition_lots || []).map(l => l.pct_reel);
            const budgetVals = (data.repartition_lots || []).map(l => l.budget);
            const depensesVals = (data.repartition_lots || []).map(l => l.depenses);

            if (chartAvancementInstance) chartAvancementInstance.destroy();
            if (chartBudgetInstance) chartBudgetInstance.destroy();

            const ctxAv = document.getElementById('chartAvancement').getContext('2d');
            chartAvancementInstance = new Chart(ctxAv, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [
                        {{ label: 'Prévu (%)', data: avPrevu, backgroundColor: '#94A3B8' }},
                        {{ label: 'Réalisé (%)', data: avReel, backgroundColor: '#1E3A8A' }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{ y: {{ beginAtZero: true, max: 100 }} }}
                }}
            }});

            const ctxBud = document.getElementById('chartBudget').getContext('2d');
            chartBudgetInstance = new Chart(ctxBud, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [
                        {{ label: 'Budget', data: budgetVals, backgroundColor: '#3B82F6' }},
                        {{ label: 'Dépenses', data: depensesVals, backgroundColor: '#F59E0B' }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{ y: {{ beginAtZero: true }} }}
                }}
            }});
        }}

        // Onglets
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(el => {{
                el.classList.remove('border-blue-900', 'text-blue-900');
                el.classList.add('border-transparent', 'text-slate-500');
            }});
            document.getElementById(tabId).classList.remove('hidden');
            const activeBtn = document.getElementById('btn-' + tabId);
            activeBtn.classList.add('border-blue-900', 'text-blue-900');
            activeBtn.classList.remove('border-transparent', 'text-slate-500');
        }}

        // Chat
        function askPrompt(q) {{
            document.getElementById('chatInput').value = q;
            sendChat();
        }}

        async function sendChat() {{
            const input = document.getElementById('chatInput');
            const btn = document.getElementById('sendBtn');
            const resArea = document.getElementById('chatResponseArea');
            const q = input.value.trim();
            if (!q) return;

            btn.disabled = true;
            btn.innerText = 'Analyse...';
            resArea.classList.remove('hidden');
            resArea.innerText = 'Réflexion des agents en cours...';

            try {{
                const res = await fetch('/api/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ question: q, filepath: currentData.filepath }})
                }});
                const data = await res.json();
                resArea.innerText = data.reponse;
            }} catch (err) {{
                resArea.innerText = "Erreur lors de la communication : " + err;
            }} finally {{
                btn.disabled = false;
                btn.innerText = 'Envoyer';
            }}
        }}

        // Initialisation immédiate
        window.onload = () => {{
            renderDashboard(currentData);
        }};
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
