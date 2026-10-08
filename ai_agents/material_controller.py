"""
ai_agents/material_controller.py
Agent 4 — Material Controller
Spécialiste de la gestion des approvisionnements, des stocks de chantier,
du contrôle des ratios de consommation et de la détection du gaspillage.
"""
from typing import Dict, Any, Optional
from ai_agents.base_agent import BaseChantierAgent
from core.models import KPISummary, ValidationReport


class MaterialControllerAgent(BaseChantierAgent):
    """Spécialiste du suivi des matériaux, du contrôle des ratios et de la gestion des stocks."""

    def __init__(self):
        super().__init__(name="Material Controller", role="Gestion des stocks, consommations et surconsommations")

    def analyze(self, kpi: KPISummary, validation: Optional[ValidationReport] = None, trends: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        mat_list = kpi.materiaux_alertes
        
        surconso_items = [m for m in mat_list if m["surconsommation_pct"] > 5.0]
        rupture_items = [m for m in mat_list if m["stock"] <= 0 or m["alerte_stock_faible"]]

        if any(m["surconsommation_pct"] >= 10.0 for m in mat_list) or len(rupture_items) > 1:
            statut = "🔴 Anomalie critique de consommation / stock"
        elif surconso_items or rupture_items:
            statut = "🟠 Surconsommations ou stocks faibles à surveiller"
        else:
            statut = "🟢 Approvisionnements et consommations sous contrôle"

        commentaire = f"{len(mat_list)} matériaux principaux sont sous surveillance active. "

        if surconso_items:
            details = ", ".join(f"{m['materiau']} (+{m['surconsommation_pct']}%)" for m in surconso_items)
            commentaire += (
                f"Une surconsommation anormale est mise en évidence sur : {details}. "
                f"Pour l'acier par exemple, la consommation réelle dépasse les ratios théoriques de ferraillage. "
                f"Cela peut s'expliquer par des chutes excessives lors du façonnage, des erreurs de calepinage "
                f"ou des longueurs de recouvrement non optimisées sur les armatures. "
            )
        else:
            commentaire += "Les consommations réelles respectent les ratios prévus au devis quantitatif. "

        if rupture_items:
            noms_rupture = ", ".join(m['materiau'] for m in rupture_items)
            commentaire += f"Alerte approvisionnement : risque de rupture immédiat sur {noms_rupture} (stock nul ou critique)."

        recommandations = []
        if surconso_items:
            recommandations.append("Sensibiliser les ferrailleurs et maçons au recyclage des chutes et au respect strict des plans d'armatures.")
            recommandations.append("Mettre en place un contrôle contradictoire systématique des bons de livraison avec pesée sur pont-bascule.")
        if rupture_items:
            recommandations.append("Déclencher un bon de commande de réapprovisionnement d'urgence pour les matériaux à stock épuisé.")

        return {
            "statut": statut,
            "synthese": commentaire,
            "materiaux_suivis": len(mat_list),
            "surconsommations": surconso_items,
            "ruptures_potentielles": rupture_items,
            "recommandations": recommandations
        }
