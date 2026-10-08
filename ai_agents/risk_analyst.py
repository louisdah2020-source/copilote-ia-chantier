"""
ai_agents/risk_analyst.py
Agent 5 — Risk Analyst
Spécialiste de la gestion des risques de chantier BTP.
Identifie les corrélations, les risques croisés (retard -> surcoût)
et hiérarchise les menaces selon une matrice de criticité.
"""
from typing import Dict, Any, Optional, List
from ai_agents.base_agent import BaseChantierAgent
from core.models import KPISummary, ValidationReport


class RiskAnalystAgent(BaseChantierAgent):
    """Spécialiste de la cartographie des risques et des scénarios d'impact."""

    def __init__(self):
        super().__init__(name="Risk Analyst", role="Évaluation et cartographie des risques globaux")

    def analyze(self, kpi: KPISummary, validation: Optional[ValidationReport] = None, trends: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        nb_critiques = len(kpi.alertes_critiques)
        nb_moyennes = len(kpi.alertes_moyennes)
        nb_normales = len(kpi.alertes_normales)

        # Calcul du score de risque global (sur 100)
        risk_score = min(100, (nb_critiques * 25) + (nb_moyennes * 8) + max(0, kpi.chantier.retard_global_jours * 2))

        if risk_score >= 60 or nb_critiques >= 2:
            niveau = "🔴 Risque Élevé — Actions correctives immédiates requises"
        elif risk_score >= 30 or nb_critiques >= 1:
            niveau = "🟠 Risque Modéré — Surveillance rapprochée"
        else:
            niveau = "🟢 Risque Faible — Chantier sous contrôle"

        # Analyse des impacts croisés (ex: retard gros oeuvre -> pénalités / coût fixe des grues)
        impacts_croises = []
        if kpi.chantier.retard_global_jours > 0:
            impacts_croises.append(
                f"Impact potentiel délai : un écart de {kpi.chantier.retard_global_jours} jours peut affecter les tâches suivantes. "
                "Les dépendances entre tâches et les coûts d'immobilisation ne sont pas fournis, leur impact ne peut donc pas être chiffré."
            )

        if any(m["surconsommation_pct"] > 5 for m in kpi.materiaux_alertes):
            impacts_croises.append(
                "Impact financier matière : La dérive de consommation matière non répercutable sur le client "
                "réduit directement la marge nette de l'entreprise générale."
            )

        top_risques = []
        for a in kpi.alertes_critiques:
            top_risques.append({
                "type": a.type_alerte,
                "lot": a.lot,
                "description": a.description,
                "action": a.action_recommandee
            })

        commentaire = (
            f"L'indice de risque global du chantier est établi à {risk_score}/100 ({niveau}). "
            f"Le système dénombre {nb_critiques} alerte(s) critique(s) 🔴, {nb_moyennes} alerte(s) à surveiller 🟠 "
            f"et {nb_normales} indicateur(s) normaux 🟢. "
        )
        if impacts_croises:
            commentaire += " " + " ".join(impacts_croises)

        return {
            "statut": niveau,
            "risk_score": risk_score,
            "synthese": commentaire,
            "nb_alertes_critiques": nb_critiques,
            "nb_alertes_moyennes": nb_moyennes,
            "nb_alertes_normales": nb_normales,
            "impacts_croises": impacts_croises,
            "top_risques": top_risques
        }
