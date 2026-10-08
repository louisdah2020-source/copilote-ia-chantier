"""
ai_agents/report_generator.py
Agent 6 — Report Generator
Générateur de rapports et synthèses managériales de chantier BTP.
Rédige des comptes-rendus hebdomadaires et notes pour la direction générale.
"""
from typing import Dict, Any, Optional
from ai_agents.base_agent import BaseChantierAgent
from core.models import KPISummary, ValidationReport


class ReportGeneratorAgent(BaseChantierAgent):
    """Spécialiste de la communication technique et de la rédaction de rapports BTP."""

    def __init__(self):
        super().__init__(name="Report Generator", role="Génération de synthèses managériales et rapports exécutifs")

    def analyze(self, kpi: KPISummary, validation: Optional[ValidationReport] = None, trends: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = kpi.parametres
        ch = kpi.chantier
        fin = kpi.finances
        devise = params.devise
        surconsommations = sorted(
            (m for m in kpi.materiaux_alertes if m["surconsommation_pct"] > 5),
            key=lambda m: m["surconsommation_pct"], reverse=True
        )
        stocks_faibles = [m for m in kpi.materiaux_alertes if m["alerte_stock_faible"]]
        lots_en_retard = [l["lot"] for l in kpi.repartition_lots if l["ecart_avancement"] < -5]
        surconso_text = ", ".join(
            "{} ({:+.1f}%)".format(m["materiau"], m["surconsommation_pct"])
            for m in surconsommations
        )
        stock_text = ", ".join(m["materiau"] for m in stocks_faibles)

        # Synthèse hebdomadaire type
        synthese_exec = (
            f"Au {kpi.date_analyse}, le chantier '{params.projet}' ({params.localisation}) affiche un avancement "
            f"physique global de {ch.avancement_physique_global}%, contre {ch.avancement_prevu_global}% programmé. "
            f"L'écart est de {ch.ecart_avancement_global:+.1f} points. Le retard estimé à partir des écarts "
            f"d'avancement et des durées renseignées est de {ch.retard_global_jours} jours. "
            f"Sur le plan financier, les engagements s'élèvent à {fin.depenses_engagees:,.0f} {devise} "
            f"({fin.pct_consommation_budget}% du budget révisé de {fin.budget_revise:,.0f} {devise}). "
            + (f"Les surconsommations supérieures à 5% concernent : {surconso_text}. " if surconsommations else "Aucune surconsommation supérieure à 5% n'est détectée dans les données. ")
            + (f"Stocks faibles : {stock_text}." if stocks_faibles else "Aucun stock faible n'est signalé selon le seuil configuré.")
        )

        # Rapport complet structuré en Markdown
        markdown_report = f"""# RAPPORT HEBDOMADAIRE DE DIRECTION — CHANTIER
**Projet** : {params.projet}  
**Maître d'Ouvrage** : {params.client}  
**Localisation** : {params.localisation}  
**Responsable Contrôle** : {params.ingenieur}  
**Date d'Arrêté** : {kpi.date_analyse}  

---

## 1. Vue d'Ensemble & Indicateurs Clés

| Indicateur | Valeur Réelle | Valeur Prévue | Écart | Statut |
| :--- | :---: | :---: | :---: | :---: |
| **Avancement Physique Global** | **{ch.avancement_physique_global}%** | {ch.avancement_prevu_global}% | {ch.ecart_avancement_global:+.1f} pts | {'🔴' if ch.ecart_avancement_global < -5 else '🟢'} |
| **Budget Alloué** | **{fin.budget_revise:,.0f} {devise}** | {fin.budget_initial:,.0f} {devise} | - | - |
| **Dépenses Engagées** | **{fin.depenses_engagees:,.0f} {devise}** | - | Consommé: {fin.pct_consommation_budget}% | {'🟠' if fin.pct_consommation_budget > 75 else '🟢'} |
| **Glissement Délais** | **+{ch.retard_global_jours} jours** | 0 jour | +{ch.retard_global_jours} j | {'🔴' if ch.retard_global_jours >= 7 else '🟢'} |

---

        ## 2. Synthèse de l'Avancement Physique
- **Tâches achevées** : {ch.nb_taches_terminees} / {ch.nb_taches_total}
- **Tâches en cours** : {ch.nb_taches_en_cours}
- **Tâches en dérive / retard** : {ch.nb_taches_en_retard}
- **Points d'attention planning** : {', '.join(lots_en_retard) if lots_en_retard else 'Aucun lot ne dépasse le seuil de retard configuré.'}

---

## 3. Performance Financière & Dépenses
- **Budget révisé** : {fin.budget_revise:,.0f} {devise}
- **Dépenses payées (facturées)** : {fin.depenses_realisees:,.0f} {devise}
- **Total engagé (payé + engagé)** : {fin.depenses_engagees:,.0f} {devise}
- **Solde disponible à engager** : {fin.reste_a_depenser:,.0f} {devise}
- **Ratio d'efficacité des coûts (CPI)** : {fin.pct_consommation_budget:.1f}% engagé pour {ch.avancement_physique_global:.1f}% réalisé.

---

## 4. Approvisionnements & Matériaux
{('Surconsommations détectées : ' + surconso_text + '.') if surconsommations else 'Aucune surconsommation supérieure à 5% détectée.'}
{('Stocks faibles : ' + stock_text + '.') if stocks_faibles else 'Aucun stock faible détecté selon le seuil configuré.'}

---

## 5. Matrice des Alertes & Actions Correctives Recommandées
"""
        for a in kpi.alertes_critiques:
            markdown_report += f"- **{a.gravite} [{a.type_alerte} - {a.lot}]** : {a.description}\n  *Action immédiate* : {a.action_recommandee}\n"
        for a in kpi.alertes_moyennes:
            markdown_report += f"- **{a.gravite} [{a.type_alerte} - {a.lot}]** : {a.description}\n  *Action recommandée* : {a.action_recommandee}\n"

        markdown_report += f"""
---
*Document généré automatiquement à partir des données du classeur fourni.*
"""

        return {
            "synthese_executive": synthese_exec,
            "rapport_markdown": markdown_report,
            "date": kpi.date_analyse,
            "titre": f"Rapport Hebdomadaire {params.projet} - {kpi.date_analyse}"
        }
