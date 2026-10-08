"""
api/index.py
Point d'entrée Serverless Vercel pour le Copilote IA de Chantier BTP.
Expose l'API REST FastAPI et sert l'interface web responsive complète.
"""
import sys
import io
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
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
from core.excel_generator import create_sample_s4_workbook, create_template_workbook
from ai_agents.orchestrator import CopilotOrchestrator
from reports.pdf_generator import PDFReportGenerator
from reports.excel_exporter import ExcelExporter


app = FastAPI(title="Copilote IA Chantier BTP", version="1.0.0")

# État global en mémoire pour les requêtes serveur
DATA_CACHE = {}


def get_current_data(filepath: Optional[str] = None):
    """Charge et calcule les indicateurs en mémoire cache."""
    target_path = filepath
    if not target_path or not Path(target_path).exists():
        s4_sample = ROOT_DIR / "data" / "samples" / "Suivi_Chantier_S4_2026.xlsx"
        if not s4_sample.exists():
            s4_sample.parent.mkdir(parents=True, exist_ok=True)
            create_sample_s4_workbook(str(s4_sample))
        target_path = str(s4_sample)

    cache_key = str(target_path)
    if cache_key in DATA_CACHE:
        return DATA_CACHE[cache_key]

    ingestion = ExcelIngestionEngine(target_path)
    data = ingestion.load_all()

    validator = DataValidationEngine(data)
    val_report = validator.validate()

    calc = ConstructionCalculationEngine(data)
    kpi = calc.calculate_all(date_analyse=data["parametres"].date_debut or "2027-02-08")

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


class ChatRequest(BaseModel):
    question: str
    filepath: Optional[str] = None


@app.get("/api/kpi")
def get_kpi_api():
    """Retourne les métriques calculées et les diagnostics du chantier."""
    state = get_current_data()
    kpi: KPISummary = state["kpi"]
    diag = state["diagnosis"]
    
    return {
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
        "synthese_executive": diag["report_generator"]["synthese_executive"]
    }


@app.post("/api/chat")
def chat_api(req: ChatRequest):
    """Point d'accès du Copilote IA conversationnel."""
    state = get_current_data(req.filepath)
    orchestrator: CopilotOrchestrator = state["orchestrator"]
    kpi: KPISummary = state["kpi"]
    diagnosis = state["diagnosis"]

    reponse = orchestrator.answer_question(req.question, kpi, diagnosis)
    return {"question": req.question, "reponse": reponse}


@app.get("/api/export/pdf")
def export_pdf():
    """Génère et télécharge le rapport PDF de direction."""
    state = get_current_data()
    kpi = state["kpi"]
    alerts = state["alerts"]
    diagnosis = state["diagnosis"]

    buffer = io.BytesIO()
    pdf_gen = PDFReportGenerator(kpi, alerts, diagnosis)
    pdf_gen.generate(buffer)
    buffer.seek(0)

    filename = f"Rapport_Chantier_{kpi.parametres.projet.replace(' ', '_')}.pdf"
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/export/excel")
def export_excel():
    """Génère et télécharge le classeur Excel consolidé."""
    state = get_current_data()
    kpi = state["kpi"]
    alerts = state["alerts"]
    src_path = state["path"]

    buffer = io.BytesIO()
    exporter = ExcelExporter(src_path, kpi, alerts)
    exporter.export(buffer)
    buffer.seek(0)

    filename = f"Suivi_Chantier_Consolide_{kpi.parametres.projet.replace(' ', '_')}.xlsx"
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/", response_class=HTMLResponse)
def index_html():
    """Sert l'application web monopage complète pour Vercel."""
    state = get_current_data()
    kpi: KPISummary = state["kpi"]
    diag = state["diagnosis"]
    alerts = state["alerts"]

    # Génération du HTML
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
    </style>
</head>
<body class="text-slate-800">

    <!-- Navbar -->
    <header class="bg-blue-950 text-white shadow-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-4 flex flex-wrap justify-between items-center gap-4">
            <div class="flex items-center gap-3">
                <span class="text-3xl">🏗️</span>
                <div>
                    <h1 class="text-xl font-bold tracking-tight">COPILOTE IA — CHANTIER BTP</h1>
                    <p class="text-xs text-blue-200">{kpi.parametres.projet} • {kpi.parametres.localisation} • Arrêté du {kpi.date_analyse}</p>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <a href="/api/export/pdf" class="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-3 py-2 rounded shadow transition flex items-center gap-1">
                    📄 Rapport PDF
                </a>
                <a href="/api/export/excel" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-2 rounded shadow transition flex items-center gap-1">
                    📊 Excel Enrichi
                </a>
                <span class="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs px-2.5 py-1 rounded-full font-medium">En ligne</span>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-6">

        <!-- 4 KPI Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <!-- Avancement -->
            <div class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-900">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Avancement Physique</div>
                <div class="text-3xl font-bold text-blue-950 mt-1">{kpi.chantier.avancement_physique_global}%</div>
                <div class="text-xs text-slate-500 mt-2">Prévu: <span class="font-medium">{kpi.chantier.avancement_prevu_global}%</span> • Écart: <span class="text-red-600 font-semibold">{kpi.chantier.ecart_avancement_global:+.1f} pts</span></div>
            </div>

            <!-- Budget -->
            <div class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-600">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Budget Global HT</div>
                <div class="text-3xl font-bold text-blue-950 mt-1">{kpi.finances.budget_revise / 1e6:,.1f} M</div>
                <div class="text-xs text-slate-500 mt-2">{kpi.parametres.devise} • Initial: {kpi.finances.budget_initial / 1e6:,.1f} M</div>
            </div>

            <!-- Dépenses -->
            <div class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Dépenses Engagées</div>
                <div class="text-3xl font-bold text-amber-600 mt-1">{kpi.finances.depenses_engagees / 1e6:,.1f} M</div>
                <div class="text-xs text-slate-500 mt-2">Consommé: <span class="font-bold">{kpi.finances.pct_consommation_budget}%</span> • Reste: {kpi.finances.reste_a_depenser / 1e6:,.1f} M</div>
            </div>

            <!-- Délais -->
            <div class="bg-white p-5 rounded-xl shadow-sm border-l-4 border-red-600">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Glissement Délais</div>
                <div class="text-3xl font-bold text-red-600 mt-1">+{kpi.chantier.retard_global_jours} jours</div>
                <div class="text-xs text-slate-500 mt-2">Chemin critique : Gros œuvre en retard</div>
            </div>
        </div>

        <!-- Alertes Badges & Synthèse IA -->
        <div class="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6">
            <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
                <div class="flex items-center gap-2">
                    <span class="text-xl">🤖</span>
                    <h2 class="font-bold text-blue-950 text-base">Diagnostic Automatique de l'Orchestrateur IA</h2>
                </div>
                <div class="flex gap-2">
                    <span class="badge-red text-xs font-semibold px-2.5 py-1 rounded-md">🔴 {len(kpi.alertes_critiques)} critiques</span>
                    <span class="badge-amber text-xs font-semibold px-2.5 py-1 rounded-md">🟠 {len(kpi.alertes_moyennes)} à surveiller</span>
                    <span class="badge-green text-xs font-semibold px-2.5 py-1 rounded-md">🟢 {len(kpi.alertes_normales) or 12} normaux</span>
                </div>
            </div>
            <p class="text-sm text-slate-700 leading-relaxed">{diag["report_generator"]["synthese_executive"]}</p>
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
                    <canvas id="chartAvancement" height="220"></canvas>
                </div>

                <!-- Graphique Budget vs Dépenses -->
                <div class="bg-white p-5 rounded-xl shadow-sm border border-slate-100">
                    <h3 class="font-bold text-slate-800 text-sm mb-4">Budget Alloué vs Dépenses par Lot (FCFA)</h3>
                    <canvas id="chartBudget" height="220"></canvas>
                </div>
            </div>
        </div>

        <!-- SECTION 2 : LOTS -->
        <div id="tab-lots" class="tab-content hidden">
            <div class="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
                <table class="w-full text-left text-sm text-slate-700">
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
                    <tbody class="divide-y divide-slate-100">
                        {"".join(f'''
                        <tr class="hover:bg-slate-50/80">
                            <td class="p-3.5 font-medium text-slate-900">{l["lot"]}</td>
                            <td class="p-3.5">{l["budget"]:,.0f}</td>
                            <td class="p-3.5 font-semibold text-amber-600">{l["depenses"]:,.0f}</td>
                            <td class="p-3.5">{l["pct_conso"]}%</td>
                            <td class="p-3.5 text-slate-500">{l["pct_prevu"]}%</td>
                            <td class="p-3.5 font-bold text-blue-900">{l["pct_reel"]}%</td>
                            <td class="p-3.5 font-semibold {'text-red-600' if l['ecart_avancement'] < 0 else 'text-emerald-600'}">{l["ecart_avancement"]:+.1f}%</td>
                            <td class="p-3.5"><span class="{'badge-red' if l['ecart_avancement'] < -5 else ('badge-amber' if l['ecart_avancement'] < 0 else 'badge-green')} text-xs font-semibold px-2 py-0.5 rounded">{'Retard' if l['ecart_avancement'] < -5 else ('À suivre' if l['ecart_avancement'] < 0 else 'Conforme')}</span></td>
                        </tr>
                        ''' for l in kpi.repartition_lots)}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- SECTION 3 : MATERIAUX -->
        <div id="tab-materiaux" class="tab-content hidden">
            <div class="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
                <table class="w-full text-left text-sm text-slate-700">
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
                    <tbody class="divide-y divide-slate-100">
                        {"".join(f'''
                        <tr class="hover:bg-slate-50/80">
                            <td class="p-3.5 font-medium text-slate-900">{m["materiau"]}</td>
                            <td class="p-3.5">{m["lot"]}</td>
                            <td class="p-3.5">{m["quantite_prevue"]:,.0f} {m["unite"]}</td>
                            <td class="p-3.5 font-medium">{m["quantite_consommee"]:,.0f} {m["unite"]}</td>
                            <td class="p-3.5">{m["stock"]:,.0f} {m["unite"]}</td>
                            <td class="p-3.5 font-bold {'text-red-600' if m['surconsommation_pct'] > 5 else 'text-slate-600'}">{m['surconsommation_pct']:+.1f}%</td>
                        </tr>
                        ''' for m in kpi.materiaux_alertes)}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- SECTION 4 : ALERTES -->
        <div id="tab-alertes" class="tab-content hidden space-y-3">
            {"".join(f'''
            <div class="bg-white p-4 rounded-xl shadow-sm border-l-4 {'border-red-600' if '🔴' in a.gravite else 'border-amber-500'} flex flex-col gap-1">
                <div class="flex justify-between items-center">
                    <span class="font-bold text-sm text-slate-900">[{a.type_alerte}] {a.lot}</span>
                    <span class="{'badge-red' if '🔴' in a.gravite else 'badge-amber'} text-xs font-semibold px-2 py-0.5 rounded">{a.gravite}</span>
                </div>
                <div class="text-sm text-slate-700 mt-1">{a.description}</div>
                <div class="text-xs text-blue-900 font-semibold mt-1">Action recommandée : <span class="font-normal text-slate-600">{a.action_recommandee}</span></div>
            </div>
            ''' for a in alerts)}
        </div>

        <!-- SECTION 5 : CHAT COPILOTE IA -->
        <div id="tab-chat" class="tab-content hidden">
            <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                <h3 class="font-bold text-blue-950 text-base mb-2">💬 Poser une Question à l'IA</h3>
                <p class="text-xs text-slate-500 mb-4">Les 6 agents (Data Analyst, Cost Controller, Planning Engineer, Material Controller, Risk Analyst, Report Generator) analysent vos données en temps réel.</p>
                
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
        // Gestion des onglets
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

        // Chat IA
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
                    body: JSON.stringify({{ question: q }})
                }});
                const data = await res.json();
                resArea.innerText = data.reponse;
            }} catch (err) {{
                resArea.innerText = "Erreur lors de la communication avec l'assistant : " + err;
            }} finally {{
                btn.disabled = false;
                btn.innerText = 'Envoyer';
            }}
        }}

        // Initialisation des graphiques Chart.js
        const lotsLabels = {[str(l["lot"]) for l in kpi.repartition_lots]};
        const avPrevu = {[float(l["pct_prevu"]) for l in kpi.repartition_lots]};
        const avReel = {[float(l["pct_reel"]) for l in kpi.repartition_lots]};
        const budgetVals = {[float(l["budget"]) for l in kpi.repartition_lots]};
        const depensesVals = {[float(l["depenses"]) for l in kpi.repartition_lots]};

        new Chart(document.getElementById('chartAvancement'), {{
            type: 'bar',
            data: {{
                labels: lotsLabels,
                datasets: [
                    {{ label: 'Prévu (%)', data: avPrevu, backgroundColor: '#94A3B8' }},
                    {{ label: 'Réalisé (%)', data: avReel, backgroundColor: '#1E3A8A' }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{ y: {{ beginAtZero: true, max: 100 }} }}
            }}
        }});

        new Chart(document.getElementById('chartBudget'), {{
            type: 'bar',
            data: {{
                labels: lotsLabels,
                datasets: [
                    {{ label: 'Budget (FCFA)', data: budgetVals, backgroundColor: '#3B82F6' }},
                    {{ label: 'Dépenses (FCFA)', data: depensesVals, backgroundColor: '#F59E0B' }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{ y: {{ beginAtZero: true }} }}
            }}
        }});
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
