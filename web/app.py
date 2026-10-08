"""
web/app.py
Application Web interactive principale du Copilote IA Chantier.
Fournit le tableau de bord 6 zones, la visualisation graphique Plotly,
le radar des alertes, le copilote IA conversationnel et l'export PDF / Excel.
"""
import os
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Ajouter le répertoire racine au PATH
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.ingestion import ExcelIngestionEngine
from core.validation import DataValidationEngine
from core.calculations import ConstructionCalculationEngine
from core.alert_engine import AlertEngine
from core.history_store import HistoryStore
from core.excel_generator import create_template_workbook, create_sample_s1_workbook, create_sample_s4_workbook
from ai_agents.orchestrator import CopilotOrchestrator
from reports.pdf_generator import PDFReportGenerator
from reports.excel_exporter import ExcelExporter


# Configuration de la page Streamlit
st.set_page_config(
    page_title="Copilote IA — Chantier BTP",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injection de styles CSS professionnels BTP
st.markdown("""
<style>
    /* Thème BTP & Ingénierie */
    .main {
        background-color: #F8FAFC;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border-left: 5px solid #1E3A8A;
        margin-bottom: 12px;
    }
    .metric-val {
        font-size: 26px;
        font-weight: 700;
        color: #1E3A8A;
        line-height: 1.2;
    }
    .metric-label {
        font-size: 13px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-sub {
        font-size: 12px;
        color: #94A3B8;
        margin-top: 4px;
    }
    .badge-critical {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
    }
    .badge-warning {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
    }
    .badge-normal {
        background-color: #DCFCE7;
        color: #166534;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
    }
    .agent-box {
        background: #EFF6FF;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #BFDBFE;
        margin-bottom: 16px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #FFFFFF;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 16px;
        border: 1px solid #E2E8F0;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_and_process_workbook(filepath: str):
    """Charge le classeur, valide et calcule tous les indicateurs."""
    ingestion = ExcelIngestionEngine(filepath)
    data = ingestion.load_all()
    
    validator = DataValidationEngine(data)
    val_report = validator.validate()
    
    calc_engine = ConstructionCalculationEngine(data)
    kpi = calc_engine.calculate_all(date_analyse=data["parametres"].date_debut or "2027-02-08")
    
    alert_engine = AlertEngine(kpi, val_report)
    alerts = alert_engine.evaluate_all(today_str=kpi.date_analyse)
    
    history_store = HistoryStore()
    trends = history_store.calculate_trends(kpi.parametres.projet)
    
    orchestrator = CopilotOrchestrator()
    diagnosis = orchestrator.run_full_diagnosis(kpi, val_report, trends)
    
    return data, val_report, kpi, alerts, trends, diagnosis, orchestrator


def main():
    # En-tête
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown("<h2 style='color:#1E3A8A; margin-bottom:0;'>🏗️ COPILOTE IA — PILOTAGE DE CHANTIER</h2>", unsafe_allow_html=True)
        st.caption("Assistant décisionnel et analytique pour Ingénieur BTP & Conducteur de Travaux")
    with col_t2:
        st.markdown("<div style='text-align:right; padding-top:10px;'><span class='badge-normal'>Système Actif</span></div>", unsafe_allow_html=True)

    # Barre latérale : Gestion du classeur Excel
    st.sidebar.markdown("### 📁 Source de Données Chantier")
    
    sample_dir = ROOT_DIR / "data" / "samples"
    template_dir = ROOT_DIR / "data" / "templates"
    
    # Assurer la création des fichiers si non existants
    s4_file = sample_dir / "Suivi_Chantier_S4_2026.xlsx"
    s1_file = sample_dir / "Suivi_Chantier_S1_2026.xlsx"
    tpl_file = template_dir / "Suivi_Chantier_Template.xlsx"
    
    if not s4_file.exists():
        create_sample_s4_workbook(str(s4_file))
    if not s1_file.exists():
        create_sample_s1_workbook(str(s1_file))
    if not tpl_file.exists():
        create_template_workbook(str(tpl_file))

    source_option = st.sidebar.radio(
        "Sélectionnez le classeur :",
        [
            "Semaine 4 — Chantier en cours (Écarts & Dérives réelles)",
            "Semaine 1 — Démarrage du chantier",
            "Importer un fichier Excel (.xlsx)"
        ],
        index=0
    )

    uploaded_file = None
    if "Importer" in source_option:
        uploaded_file = st.sidebar.file_uploader("Déposer le fichier Excel du chantier", type=["xlsx", "xlsm"])
        if uploaded_file is not None:
            temp_path = ROOT_DIR / "data" / "temp_uploaded.xlsx"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            current_path = str(temp_path)
        else:
            st.sidebar.info("Veuillez téléverser un fichier pour démarrer l'analyse.")
            current_path = str(s4_file)
    elif "Semaine 1" in source_option:
        current_path = str(s1_file)
    else:
        current_path = str(s4_file)

    # Chargement et calcul
    try:
        data, val_report, kpi, alerts, trends, diagnosis, orchestrator = load_and_process_workbook(current_path)
    except Exception as e:
        st.error(f"Erreur lors du traitement du classeur : {e}")
        return

    # Infos du projet dans la sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Projet :** {kpi.parametres.projet}")
    st.sidebar.markdown(f"**Client :** {kpi.parametres.client}")
    st.sidebar.markdown(f"**Site :** {kpi.parametres.localisation}")
    st.sidebar.markdown(f"**Ingénieur :** {kpi.parametres.ingenieur}")
    st.sidebar.markdown(f"**Date Arrêté :** `{kpi.date_analyse}`")
    st.sidebar.markdown(f"**Devise :** {kpi.parametres.devise}")

    # Enregistrer le snapshot dans l'historique
    if st.sidebar.button("💾 Enregistrer dans l'historique SQLite"):
        store = HistoryStore()
        store.save_snapshot(kpi)
        st.sidebar.success("Snapshot archivé avec succès !")

    # Modèle vierge à télécharger
    with open(tpl_file, "rb") as f_tpl:
        st.sidebar.download_button(
            label="📥 Télécharger Modèle Vierge (.xlsx)",
            data=f_tpl,
            file_name="Suivi_Chantier_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ONGLET PRINCIPAL
    tabs = st.tabs([
        "📊 Dashboard",
        "📅 Planning & Gantt",
        "💰 Budget & Finances",
        "📦 Matériaux & Stocks",
        "👷 Main-d'œuvre",
        "⚠️ Radar des Alertes",
        "🤖 Copilote IA (Chat)",
        "📑 Exports & Rapports"
    ])

    # ----------------------------------------------------
    # TAB 1 : DASHBOARD GÉNÉRAL (6 ZONES)
    # ----------------------------------------------------
    with tabs[0]:
        # Zone A : Vue générale (4 KPI Cards)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            ecart_sign = f"{kpi.chantier.ecart_avancement_global:+.1f}%"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Avancement Physique</div>
                <div class="metric-val">{kpi.chantier.avancement_physique_global} %</div>
                <div class="metric-sub">Prévu: {kpi.chantier.avancement_prevu_global}% | Écart: <b>{ecart_sign}</b></div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Budget Global</div>
                <div class="metric-val">{kpi.finances.budget_revise / 1e6:,.1f} M</div>
                <div class="metric-sub">{kpi.parametres.devise} (Initial: {kpi.finances.budget_initial / 1e6:,.1f} M)</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Dépenses Engagées</div>
                <div class="metric-val" style="color:#D97706;">{kpi.finances.depenses_engagees / 1e6:,.1f} M</div>
                <div class="metric-sub">Conso: <b>{kpi.finances.pct_consommation_budget}%</b> | Payé: {kpi.finances.depenses_realisees / 1e6:,.1f} M</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            delay_col = "#DC2626" if kpi.chantier.retard_global_jours >= 5 else "#10B981"
            st.markdown(f"""
            <div class="metric-card" style="border-left-color:{delay_col};">
                <div class="metric-label">Glissement Délais</div>
                <div class="metric-val" style="color:{delay_col};">+{kpi.chantier.retard_global_jours} jours</div>
                <div class="metric-sub">Chemin critique : {kpi.chantier.nb_taches_en_retard} tâches en retard</div>
            </div>
            """, unsafe_allow_html=True)

        # Synthèse IA & Badges alertes
        nb_crit = len(kpi.alertes_critiques)
        nb_moy = len(kpi.alertes_moyennes)
        nb_norm = len(kpi.alertes_normales) or 12

        st.markdown(f"""
        <div style="margin: 10px 0 16px 0; display:flex; gap:12px; align-items:center;">
            <span class="badge-critical">🔴 {nb_crit} Alertes critiques</span>
            <span class="badge-warning">🟠 {nb_moy} Alertes à surveiller</span>
            <span class="badge-normal">🟢 {nb_norm} Indicateurs normaux</span>
        </div>
        """, unsafe_allow_html=True)

        # Commentaire de l'Orchestrateur IA
        st.markdown(f"""
        <div class="agent-box">
            <b>🤖 Diagnostic Automatique du Copilote IA :</b><br/>
            {diagnosis['report_generator']['synthese_executive']}
        </div>
        """, unsafe_allow_html=True)

        # Graphiques du Dashboard : Avancement par Lot & Répartition Budgétaire
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            st.markdown("##### 📈 Avancement Réel vs Prévu par Lot")
            df_lots = pd.DataFrame(kpi.repartition_lots)
            if not df_lots.empty:
                fig_av = go.Figure()
                fig_av.add_trace(go.Bar(
                    name="Prévu",
                    x=df_lots["lot"],
                    y=df_lots["pct_prevu"],
                    marker_color="#94A3B8"
                ))
                fig_av.add_trace(go.Bar(
                    name="Réalisé",
                    x=df_lots["lot"],
                    y=df_lots["pct_reel"],
                    marker_color="#1E3A8A"
                ))
                fig_av.update_layout(
                    barmode="group",
                    yaxis_title="% d'avancement",
                    yaxis_range=[0, 105],
                    legend=dict(orientation="h", y=1.1),
                    margin=dict(l=20, r=20, t=30, b=50),
                    height=320
                )
                st.plotly_chart(fig_av, use_container_width=True)

        with g_col2:
            st.markdown("##### 💰 Budget Alloué vs Dépenses par Lot")
            if not df_lots.empty:
                fig_bud = go.Figure()
                fig_bud.add_trace(go.Bar(
                    name="Budget",
                    x=df_lots["lot"],
                    y=df_lots["budget"],
                    marker_color="#3B82F6"
                ))
                fig_bud.add_trace(go.Bar(
                    name="Dépenses",
                    x=df_lots["lot"],
                    y=df_lots["depenses"],
                    marker_color="#F59E0B"
                ))
                fig_bud.update_layout(
                    barmode="group",
                    yaxis_title=f"Montant ({kpi.parametres.devise})",
                    legend=dict(orientation="h", y=1.1),
                    margin=dict(l=20, r=20, t=30, b=50),
                    height=320
                )
                st.plotly_chart(fig_bud, use_container_width=True)

        # Matériaux & Main-d'œuvre aperçu
        c_m1, c_m2 = st.columns([3, 2])
        with c_m1:
            st.markdown("##### 📦 Matériaux Clés & Surconsommations")
            df_mat = pd.DataFrame(kpi.materiaux_alertes)
            if not df_mat.empty:
                st.dataframe(
                    df_mat[["materiau", "lot", "quantite_prevue", "quantite_consommee", "stock", "unite", "surconsommation_pct"]],
                    column_config={
                        "materiau": "Matériau",
                        "lot": "Lot",
                        "quantite_prevue": st.column_config.NumberColumn("Prévu", format="%d"),
                        "quantite_consommee": st.column_config.NumberColumn("Consommé", format="%d"),
                        "stock": st.column_config.NumberColumn("Stock", format="%d"),
                        "surconsommation_pct": st.column_config.NumberColumn("Surconso (%)", format="+%.1f %%")
                    },
                    use_container_width=True,
                    hide_index=True
                )

        with c_m2:
            st.markdown("##### 👷 Pointage Main-d'œuvre")
            mo = kpi.main_oeuvre_stats
            st.write(f"• **Ouvriers mobilisés :** {mo.get('nb_ouvriers_total_pointe', 0)} personnes")
            st.write(f"• **Volume total d'heures :** {mo.get('total_heures', 0):,.0f} h")
            st.write(f"• **Coût global :** {mo.get('total_cout', 0):,.0f} {kpi.parametres.devise}")
            st.write(f"• **Coût moyen horaire :** {mo.get('cout_moyen_horaire', 0):,.0f} {kpi.parametres.devise}/h")

    # ----------------------------------------------------
    # TAB 2 : PLANNING & GANTT
    # ----------------------------------------------------
    with tabs[1]:
        st.markdown("### 📅 Suivi du Planning & Diagramme de Gantt")
        pe = diagnosis["planning_engineer"]
        
        st.info(f"💡 **Avis du Planning Engineer :** {pe['synthese']}")

        tasks = data.get("planning", [])
        if tasks:
            df_tasks = pd.DataFrame([
                {
                    "ID": t.id_tache,
                    "Tâche": t.tache,
                    "Lot": t.lot,
                    "Début prévu": t.debut_prevu,
                    "Fin prévue": t.fin_prevue,
                    "Début réel": t.debut_reel or t.debut_prevu,
                    "% Prévu": t.pct_prevu,
                    "% Réel": t.pct_reel,
                    "Écart": t.ecart,
                    "Statut": t.statut
                }
                for t in tasks
            ])

            # Diagramme de Gantt
            try:
                fig_gantt = px.timeline(
                    df_tasks,
                    x_start="Début prévu",
                    x_end="Fin prévue",
                    y="Tâche",
                    color="Lot",
                    hover_data=["% Réel", "Statut"],
                    title="Calendrier des Travaux (Jalons Contractuels)"
                )
                fig_gantt.update_yaxes(autorange="reversed")
                fig_gantt.update_layout(height=420, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_gantt, use_container_width=True)
            except Exception:
                st.warning("Diagramme de Gantt en cours de synchronisation...")

            st.markdown("##### 📋 Détail des Tâches de Planning")
            st.dataframe(
                df_tasks[["ID", "Lot", "Tâche", "Début prévu", "Fin prévue", "% Prévu", "% Réel", "Écart", "Statut"]],
                use_container_width=True,
                hide_index=True
            )

    # ----------------------------------------------------
    # TAB 3 : BUDGET & FINANCES
    # ----------------------------------------------------
    with tabs[2]:
        st.markdown("### 💰 Performance Financière & Contrôle des Coûts")
        cc = diagnosis["cost_controller"]
        
        st.info(f"💡 **Avis du Cost Controller :** {cc['synthese']}")

        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Budget Révisé", f"{kpi.finances.budget_revise / 1e6:,.1f} M {kpi.parametres.devise}")
        f2.metric("Dépenses Engagées", f"{kpi.finances.depenses_engagees / 1e6:,.1f} M {kpi.parametres.devise}")
        f3.metric("Reste à Dépenser", f"{kpi.finances.reste_a_depenser / 1e6:,.1f} M {kpi.parametres.devise}")
        f4.metric("Coût Final Estimé (EAC)", f"{cc.get('eac_projection', 0) / 1e6:,.1f} M {kpi.parametres.devise}")

        # Liste des dépenses
        dep = data.get("depenses", [])
        if dep:
            st.markdown("##### 🧾 Journal des Dépenses & Factures")
            df_dep = pd.DataFrame([
                {
                    "Date": d.date,
                    "Lot": d.lot,
                    "Poste": d.poste,
                    "Fournisseur": d.fournisseur,
                    "Référence": d.reference,
                    "Montant": d.montant,
                    "Statut": d.statut
                }
                for d in dep
            ])
            st.dataframe(
                df_dep,
                column_config={"Montant": st.column_config.NumberColumn(format="%d FCFA")},
                use_container_width=True,
                hide_index=True
            )

    # ----------------------------------------------------
    # TAB 4 : MATÉRIAUX & STOCKS
    # ----------------------------------------------------
    with tabs[3]:
        st.markdown("### 📦 Suivi des Matériaux & Contrôle des Pertes")
        mc = diagnosis["material_controller"]
        st.info(f"💡 **Avis du Material Controller :** {mc['synthese']}")

        df_m = pd.DataFrame(kpi.materiaux_alertes)
        if not df_m.empty:
            # Graphique de surconsommation
            fig_sc = px.bar(
                df_m,
                x="materiau",
                y="surconsommation_pct",
                color="surconsommation_pct",
                color_continuous_scale="Reds",
                title="Écart de Consommation Réelle vs Théorique (%)",
                labels={"surconsommation_pct": "Surconsommation (%)", "materiau": "Matériau"}
            )
            fig_sc.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_sc, use_container_width=True)

    # ----------------------------------------------------
    # TAB 5 : MAIN D'OEUVRE
    # ----------------------------------------------------
    with tabs[4]:
        st.markdown("### 👷 Main-d'œuvre & Productivité des Équipes")
        mo_data = data.get("main_oeuvre", [])
        if mo_data:
            df_mo = pd.DataFrame([
                {
                    "Date": w.date,
                    "Lot": w.lot,
                    "Équipe": w.equipe,
                    "Ouvriers": w.nb_ouvriers,
                    "Heures": w.heures,
                    "Coût": w.cout,
                    "Tâche": w.tache_associee
                }
                for w in mo_data
            ])
            st.dataframe(df_mo, use_container_width=True, hide_index=True)

    # ----------------------------------------------------
    # TAB 6 : RADAR DES ALERTES
    # ----------------------------------------------------
    with tabs[5]:
        st.markdown("### ⚠️ Radar des Risques & Alertes Métiers")
        ra = diagnosis["risk_analyst"]
        st.warning(f"🛡️ **Analyse du Risk Analyst :** {ra['synthese']}")

        filtre_gravite = st.multiselect(
            "Filtrer par gravité :",
            ["🔴 Haute", "🟠 Moyenne", "🟢 Faible"],
            default=["🔴 Haute", "🟠 Moyenne"]
        )

        filtered_alerts = [a for a in alerts if any(g in a.gravite for g in filtre_gravite)]
        
        for a in filtered_alerts:
            badge_class = "badge-critical" if "🔴" in a.gravite else ("badge-warning" if "🟠" in a.gravite else "badge-normal")
            st.markdown(f"""
            <div style="background:white; border-radius:8px; padding:12px 16px; margin-bottom:10px; border-left:4px solid {'#DC2626' if '🔴' in a.gravite else '#F59E0B'}; box-shadow:0 1px 2px rgba(0,0,0,0.05);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b>[{a.type_alerte}] {a.lot}</b>
                    <span class="{badge_class}">{a.gravite}</span>
                </div>
                <div style="margin-top:6px; color:#374151;">{a.description}</div>
                <div style="margin-top:6px; font-size:13px; color:#1E3A8A;"><b>Action recommandée :</b> {a.action_recommandee}</div>
            </div>
            """, unsafe_allow_html=True)

    # ----------------------------------------------------
    # TAB 7 : COPILOTE IA CONVERSATIONNEL
    # ----------------------------------------------------
    with tabs[6]:
        st.markdown("### 💬 Poser une Question au Copilote IA")
        st.caption("Interrogez directement les 6 agents sur les causes des retards, les dérives de coûts, ou demandez des synthèses.")

        # Suggestions rapides de questions
        st.markdown("**Questions rapides d'ingénierie :**")
        q_cols = st.columns(4)
        selected_q = None
        if q_cols[0].button("⏱️ Pourquoi le retard ?"):
            selected_q = "Pourquoi avons-nous du retard ?"
        if q_cols[1].button("💰 Lot le plus cher ?"):
            selected_q = "Quel lot coûte le plus cher ?"
        if q_cols[2].button("🛡️ Risque budgétaire ?"):
            selected_q = "Quel est le risque budgétaire ?"
        if q_cols[3].button("📦 Stock & Acier ?"):
            selected_q = "Où en est la consommation d'acier et le stock ?"

        # Zone de texte utilisateur
        user_prompt = st.text_input(
            "Votre question :",
            value=selected_q if selected_q else "",
            placeholder="Ex : Quel est le plan d'action pour résorber le retard sur le gros œuvre ?"
        )

        if user_prompt:
            with st.spinner("Analyse par le comité multi-agents en cours..."):
                response = orchestrator.answer_question(user_prompt, kpi, diagnosis)
                st.markdown(f"""
                <div style="background:white; border-radius:10px; padding:16px 20px; border:1px solid #CBD5E1; margin-top:12px; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                    {response}
                </div>
                """, unsafe_allow_html=True)

    # ----------------------------------------------------
    # TAB 8 : EXPORTS & RAPPORTS
    # ----------------------------------------------------
    with tabs[7]:
        st.markdown("### 📑 Exports & Rapports de Direction")
        st.write("Téléchargez les livrables officiels prêts à être transmis au Maître d'Ouvrage ou à la Direction Générale :")

        rep_col1, rep_col2 = st.columns(2)
        
        # 1. Génération PDF
        pdf_out = ROOT_DIR / "data" / "exports" / f"Rapport_Chantier_{kpi.parametres.projet.replace(' ', '_')}.pdf"
        with rep_col1:
            st.markdown("#### 📄 Rapport Exécutif PDF")
            st.write("Mise en page certifiée avec indicateurs clés, analyse des lots, suivi matériaux et alertes.")
            if st.button("🔄 Générer le Rapport PDF"):
                pdf_gen = PDFReportGenerator(kpi, alerts, diagnosis)
                pdf_gen.generate(str(pdf_out))
                st.success("Rapport PDF généré avec succès !")
                
            if pdf_out.exists():
                with open(pdf_out, "rb") as f_pdf:
                    st.download_button(
                        label="⬇️ Télécharger le PDF Officiel",
                        data=f_pdf,
                        file_name=f"Rapport_Chantier_{kpi.date_analyse}.pdf",
                        mime="application/pdf"
                    )

        # 2. Export Excel enrichi
        xlsx_out = ROOT_DIR / "data" / "exports" / f"Suivi_Chantier_{kpi.parametres.projet.replace(' ', '_')}_Consolide.xlsx"
        with rep_col2:
            st.markdown("#### 📊 Classeur Excel Mis à Jour")
            st.write("Classeur Excel avec les feuilles **AVANCEMENT** et **ALERTES** automatiquement complétées.")
            if st.button("🔄 Régénérer l'Excel Enrichi"):
                ex_exporter = ExcelExporter(current_path, kpi, alerts)
                ex_exporter.export(str(xlsx_out))
                st.success("Classeur Excel consolidé généré avec succès !")
                
            if xlsx_out.exists():
                with open(xlsx_out, "rb") as f_xlsx:
                    st.download_button(
                        label="⬇️ Télécharger l'Excel Enrichi",
                        data=f_xlsx,
                        file_name=f"Suivi_Chantier_Consolide_{kpi.date_analyse}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        st.markdown("---")
        st.markdown("##### 📝 Aperçu Markdown du Rapport de Direction")
        st.text_area("Rapport brut :", diagnosis["report_generator"]["rapport_markdown"], height=300)


if __name__ == "__main__":
    main()
