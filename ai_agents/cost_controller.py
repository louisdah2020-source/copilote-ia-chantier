"""
ai_agents/cost_controller.py
Agent 2 — Cost Controller
Spécialiste du contrôle de gestion de chantier : analyse budgétaire, dépenses,
écarts financiers et prévisions de coût à l'achèvement (EAC).
"""
from typing import Dict, Any, Optional
from ai_agents.base_agent import BaseChantierAgent
from core.models import KPISummary, ValidationReport


class CostControllerAgent(BaseChantierAgent):
    """Spécialiste du suivi financier et de la maîtrise des coûts de construction."""

    def __init__(self):
        super().__init__(name="Cost Controller", role="Contrôle budgétaire, dépenses et prévisions")

    def analyze(self, kpi: KPISummary, validation: Optional[ValidationReport] = None, trends: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        fin = kpi.finances
        devise = kpi.parametres.devise
        
        # Trouver les lots les plus coûteux et les plus en dépassement
        sorted_by_dep = sorted(kpi.repartition_lots, key=lambda x: x["depenses"], reverse=True)
        top_cost_lot = sorted_by_dep[0] if sorted_by_dep else None

        lots_depassement = [l for l in kpi.repartition_lots if l["depenses"] > l["budget"]]
        lots_en_tension = [l for l in kpi.repartition_lots if l["pct_conso"] > 80 and l["pct_reel"] < 70]

        # Calcul du CPI et projection EAC
        cpi = (kpi.chantier.avancement_physique_global / fin.pct_consommation_budget) if fin.pct_consommation_budget > 0 else 1.0
        eac = fin.budget_revise / cpi if cpi > 0 else fin.budget_revise
        ecart_prev_final = eac - fin.budget_revise

        # Gravité du diagnostic
        if fin.pct_consommation_budget > 90 or len(lots_depassement) > 0:
            gravite = "🔴 Tension budgétaire forte"
        elif fin.pct_consommation_budget > 70:
            gravite = "🟠 Consommation modérée à surveiller"
        else:
            gravite = "🟢 Budget maîtrisé"

        # Interprétation rédigée
        commentaire = (
            f"Le budget initial alloué s'élève à {fin.budget_initial:,.0f} {devise}. "
            f"À ce stade, les engagements totaux atteignent {fin.depenses_engagees:,.0f} {devise}, "
            f"soit un taux de consommation budgétaire de {fin.pct_consommation_budget}%. "
            f"Le solde restant à engager est de {fin.reste_a_depenser:,.0f} {devise}. "
        )

        if top_cost_lot:
            commentaire += (
                f"Le lot le plus consommateur est '{top_cost_lot['lot']}' avec {top_cost_lot['depenses']:,.0f} {devise} "
                f"dépensés ({top_cost_lot['pct_conso']}% de son enveloppe). "
            )

        if lots_depassement:
            noms = ", ".join(l['lot'] for l in lots_depassement)
            commentaire += f"Attention : un dépassement de budget effectif est constaté sur {noms}. "
        elif lots_en_tension:
            noms = ", ".join(l['lot'] for l in lots_en_tension)
            commentaire += f"Point de vigilance : dérive financière détectée sur {noms} où les dépenses devancent l'avancement physique. "
        else:
            commentaire += "L'ensemble des lots respecte pour l'instant leurs enveloppes allouées."

        if ecart_prev_final > 0:
            commentaire += f" La projection du coût final à l'achèvement (EAC) est estimée à {eac:,.0f} {devise} (+{ecart_prev_final:,.0f} {devise})."

        recommandations = []
        if lots_depassement:
            recommandations.append("Bloquer toute commande supplémentaire hors avenant formel sur les lots en dépassement.")
        if lots_en_tension:
            recommandations.append("Effectuer un audit contradictoire des factures en attente et des quantités réelles mises en œuvre.")
        recommandations.append("Négocier des remises de volume avec les principaux fournisseurs de gros œuvre.")

        return {
            "statut": gravite,
            "synthese": commentaire,
            "budget_initial": fin.budget_initial,
            "depenses_engagees": fin.depenses_engagees,
            "depenses_realisees": fin.depenses_realisees,
            "reste_a_depenser": fin.reste_a_depenser,
            "pct_consommation": fin.pct_consommation_budget,
            "cpi": round(cpi, 2),
            "eac_projection": round(eac, 0),
            "lot_plus_couteux": top_cost_lot["lot"] if top_cost_lot else "N/A",
            "lots_en_depassement": [l["lot"] for l in lots_depassement],
            "lots_en_tension": [l["lot"] for l in lots_en_tension],
            "recommandations": recommandations
        }
