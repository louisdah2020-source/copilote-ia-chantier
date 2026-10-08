"""
ai_agents/data_analyst.py
Agent 1 — Data Analyst
Lit, audite et contrôle l'intégrité du classeur Excel de chantier.
"""
from typing import Dict, Any, Optional
from ai_agents.base_agent import BaseChantierAgent
from core.models import KPISummary, ValidationReport


class DataAnalystAgent(BaseChantierAgent):
    """Spécialiste de la qualité des données et de l'intégrité du classeur chantier."""

    def __init__(self):
        super().__init__(name="Data Analyst", role="Contrôle qualité et santé des données")

    def analyze(self, kpi: KPISummary, validation: Optional[ValidationReport] = None, trends: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        val = validation or ValidationReport()
        
        statut = "🟢 Données conformes" if val.est_valide and not val.doublons else "🟠 Anomalies détectées"
        
        bullet_points = [
            f"✓ {val.total_lignes} lignes analysées à travers le classeur",
            f"✓ {val.nb_lots} lots identifiés",
            f"✓ {val.nb_taches} tâches de planning recensées",
            f"✓ {val.nb_fournisseurs} fournisseurs répertoriés"
        ]
        
        alertes = []
        if val.valeurs_manquantes:
            alertes.append(f"⚠ {len(val.valeurs_manquantes)} valeurs manquantes identifiées")
        if val.doublons:
            alertes.append(f"⚠ {len(val.doublons)} doublons de clés/factures potentiels")
        if val.anomalies_prix:
            alertes.append(f"⚠ {len(val.anomalies_prix)} prix ou quantités aberrants")
        if val.anomalies_dates:
            alertes.append(f"⚠ {len(val.anomalies_dates)} incohérences chronologiques")

        commentaire = (
            f"L'ingestion du classeur pour le projet '{kpi.parametres.projet}' s'est déroulée avec succès. "
            f"Au total, {val.total_lignes} enregistrements ont été audités. "
        )
        if alertes:
            commentaire += "Certains points de vigilance nécessitent l'attention du projeteur : " + " ; ".join(alertes) + "."
        else:
            commentaire += "Aucune incohérence majeure n'a été relevée dans la structure des tables."

        return {
            "statut": statut,
            "synthese": commentaire,
            "lignes_auditees": val.total_lignes,
            "lots": val.nb_lots,
            "taches": val.nb_taches,
            "fournisseurs": val.nb_fournisseurs,
            "points_cles": bullet_points,
            "anomalies": alertes,
            "details_anomalies": {
                "manquants": val.valeurs_manquantes,
                "doublons": val.doublons,
                "prix": val.anomalies_prix,
                "dates": val.anomalies_dates
            }
        }
