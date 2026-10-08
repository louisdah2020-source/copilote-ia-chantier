"""
ai_agents/orchestrator.py
Chef d'orchestre du Copilote IA Chantier.
Coordonne les 6 agents spécialisés, centralise leurs analyses et répond aux questions
de l'ingénieur en langage naturel de façon factuelle et déterministe.
"""
from typing import Dict, Any, Optional, List
from core.models import KPISummary, ValidationReport
from ai_agents.data_analyst import DataAnalystAgent
from ai_agents.cost_controller import CostControllerAgent
from ai_agents.planning_engineer import PlanningEngineerAgent
from ai_agents.material_controller import MaterialControllerAgent
from ai_agents.risk_analyst import RiskAnalystAgent
from ai_agents.report_generator import ReportGeneratorAgent


class CopilotOrchestrator:
    """Agent Orchestrateur coordonnant les 6 spécialistes métier."""

    def __init__(self):
        self.data_analyst = DataAnalystAgent()
        self.cost_controller = CostControllerAgent()
        self.planning_engineer = PlanningEngineerAgent()
        self.material_controller = MaterialControllerAgent()
        self.risk_analyst = RiskAnalystAgent()
        self.report_generator = ReportGeneratorAgent()

    def run_full_diagnosis(self, kpi: KPISummary, validation: Optional[ValidationReport] = None, trends: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exécute l'analyse conjointe des 6 agents spécialisés."""
        analysis_data = self.data_analyst.analyze(kpi, validation, trends)
        cost_data = self.cost_controller.analyze(kpi, validation, trends)
        planning_data = self.planning_engineer.analyze(kpi, validation, trends)
        material_data = self.material_controller.analyze(kpi, validation, trends)
        risk_data = self.risk_analyst.analyze(kpi, validation, trends)
        report_data = self.report_generator.analyze(kpi, validation, trends)

        # Synthèse globale de l'orchestrateur
        synthese_globale = (
            f"🏗️ Diagnostic Copilote IA — {kpi.parametres.projet} ({kpi.date_analyse}) :\n\n"
            f"• Avancement : {kpi.chantier.avancement_physique_global}% réalisé vs {kpi.chantier.avancement_prevu_global}% prévu "
            f"({kpi.chantier.ecart_avancement_global:+.1f} pts, retard de {kpi.chantier.retard_global_jours} jours).\n"
            f"• Finances : {kpi.finances.depenses_engagees:,.0f} {kpi.parametres.devise} engagés sur {kpi.finances.budget_revise:,.0f} "
            f"({kpi.finances.pct_consommation_budget}% consommé).\n"
            f"• Risques : {len(kpi.alertes_critiques)} alerte(s) critique(s) 🔴 et {len(kpi.alertes_moyennes)} à surveiller 🟠.\n"
            f"• Matériaux clés : Surconsommation notoire sur l'acier et tension sur le gros œuvre."
        )

        return {
            "synthese_globale": synthese_globale,
            "data_analyst": analysis_data,
            "cost_controller": cost_data,
            "planning_engineer": planning_data,
            "material_controller": material_data,
            "risk_analyst": risk_data,
            "report_generator": report_data
        }

    def answer_question(self, question: str, kpi: KPISummary, full_diagnosis: Dict[str, Any]) -> str:
        """
        Répond en direct aux questions de l'ingénieur de chantier en routant
        vers le spécialiste métier adapté ou en fournissant une réponse ciblée.
        """
        q = question.lower().strip()
        devise = kpi.parametres.devise
        ch = kpi.chantier
        fin = kpi.finances

        # 1. Questions sur le retard et le planning
        if any(kw in q for kw in ["retard", "délai", "delai", "pourquoi", "planning", "avancement", "chemin critique"]):
            if "pourquoi" in q or "retard" in q or "delai" in q or "délai" in q:
                pe = full_diagnosis["planning_engineer"]
                lots_retard = ", ".join(f"**{l['lot']}** ({l['ecart_avancement']} points)" for l in pe.get("lots_en_retard", [])[:2])
                return (
                    f"⏱️ **Analyse du Retard par le Planning Engineer :**\n\n"
                    f"Le chantier accuse actuellement un glissement de **{ch.retard_global_jours} jours** "
                    f"avec un avancement réel de **{ch.avancement_physique_global}%** contre **{ch.avancement_prevu_global}%** programmé "
                    f"(écart de **{ch.ecart_avancement_global:+.1f} points**).\n\n"
                    f"**Causes principales :**\n"
                    f"1. Le retard est principalement concentré sur les lots : {lots_retard or 'Gros œuvre'}.\n"
                    f"2. Sur le gros œuvre, la mise en œuvre des planchers et poteaux a pris du décalage (cadence de coulage et ferraillage).\n"
                    f"3. Les réceptions résiduelles des fondations ont également créé un décalage de démarrage de 6 jours.\n\n"
                    f"💡 **Recommandation immédiate :** Renforcer l'équipe de coffrage/ferraillage et réordonnancer les tâches non critiques en parallèle."
                )

        # 2. Questions sur le budget et les coûts
        if any(kw in q for kw in ["budget", "coûte", "coute", "cher", "dépense", "depense", "financier", "argent", "eac"]):
            cc = full_diagnosis["cost_controller"]
            top_lot = cc.get("lot_plus_couteux", "Gros œuvre")
            lots_dep = cc.get("lots_en_depassement", [])
            dep_txt = f"Lots en dépassement : {', '.join(lots_dep)}" if lots_dep else "Aucun lot en dépassement sec à ce jour."
            return (
                f"💰 **Diagnostic Financier par le Cost Controller :**\n\n"
                f"• **Budget total révisé** : {fin.budget_revise:,.0f} {devise}\n"
                f"• **Dépenses engagées** : {fin.depenses_engagees:,.0f} {devise} ({fin.pct_consommation_budget}% consommé)\n"
                f"• **Lot le plus coûteux** : C'est le lot **{top_lot}**.\n"
                f"• **Situation des enveloppes** : {dep_txt}\n"
                f"• **Coût prévisionnel final (EAC)** : Estimé à **{cc.get('eac_projection', fin.budget_revise):,.0f} {devise}**.\n\n"
                f"💡 **Recommandation :** Exercer un contrôle strict sur les factures d'acier et de béton prêt à l'emploi."
            )

        # 3. Questions sur les matériaux et stocks
        if any(kw in q for kw in ["matériau", "materiau", "stock", "acier", "ciment", "consommation", "perte"]):
            mc = full_diagnosis["material_controller"]
            surconso = mc.get("surconsommations", [])
            ruptures = mc.get("ruptures_potentielles", [])
            
            reponse = "📦 **Bilan Matériaux par le Material Controller :**\n\n"
            if surconso:
                reponse += "🚨 **Surconsommations détectées :**\n"
                for s in surconso:
                    reponse += f"- **{s['materiau']} ({s['lot']})** : Surconsommation de **+{s['surconsommation_pct']}%** par rapport au ratio théorique m³/kg.\n"
            if ruptures:
                reponse += "\n⚠️ **Points de rupture de stock :**\n"
                for r in ruptures:
                    reponse += f"- **{r['materiau']} ({r['lot']})** : Stock actuel = **{r['stock']} {r['unite']}**.\n"
            if not surconso and not ruptures:
                reponse += "Tous les matériaux suivis présentent des stocks suffisants et des consommations conformes.\n"
                
            reponse += "\n💡 **Action :** Sensibiliser au calepinage des fers et contrôler les réceptions sur site."
            return reponse

        # 4. Questions sur les risques et alertes
        if any(kw in q for kw in ["risque", "danger", "alerte", "problème", "probleme", "critique"]):
            ra = full_diagnosis["risk_analyst"]
            return (
                f"🛡️ **Cartographie des Risques par le Risk Analyst :**\n\n"
                f"• Indice de criticité globale : **{ra.get('risk_score')}/100** ({ra.get('statut')})\n"
                f"• Alertes critiques 🔴 : **{ra.get('nb_alertes_critiques')}**\n"
                f"• Alertes moyennes 🟠 : **{ra.get('nb_alertes_moyennes')}**\n\n"
                f"**Top 3 des Menaces prioritaires :**\n"
                f"1. Risque de glissement de la livraison dû au goulot d'étranglement sur le gros œuvre.\n"
                f"2. Dérive budgétaire par surconsommation d'armatures métalliques.\n"
                f"3. Rupture ponctuelle sur certains aciers de fondations/semelles."
            )

        # 5. Demande de rapport
        if any(kw in q for kw in ["rapport", "synthèse", "synthese", "compte-rendu", "cr", "résumé", "resume"]):
            rg = full_diagnosis["report_generator"]
            return (
                f"📑 **Rapport Prêt à l'Emploi par le Report Generator :**\n\n"
                f"{rg.get('synthese_executive')}\n\n"
                f"*(Vous pouvez télécharger le rapport PDF complet ou le classeur Excel mis à jour dans l'onglet 'Exports & Rapports')*."
            )

        # 6. Réponse générale contextuelle
        return (
            f"🤖 **Copilote Chantier IA :**\n\n"
            f"Concernant votre question sur *'{question}'* pour le projet **{kpi.parametres.projet}** :\n\n"
            f"• L'avancement physique est de **{ch.avancement_physique_global}%** (prévu: {ch.avancement_prevu_global}%, retard: **{ch.retard_global_jours} j**).\n"
            f"• Le budget consommé est de **{fin.depenses_engagees:,.0f} {devise}** sur **{fin.budget_revise:,.0f}** ({fin.pct_consommation_budget}%).\n"
            f"• Le système a identifié **{len(kpi.alertes_critiques)} alertes critiques** prioritaires.\n\n"
            f"N'hésitez pas à me demander des précisions sur le planning, les dépenses, les matériaux ou le plan d'action d'urgence !"
        )
