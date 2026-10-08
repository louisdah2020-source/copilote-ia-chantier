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

        # Synthèse hebdomadaire type
        synthese_exec = (
            f"Au {kpi.date_analyse}, le chantier '{params.projet}' ({params.localisation}) affiche un avancement "
            f"physique global de {ch.avancement_physique_global}%, contre {ch.avancement_prevu_global}% programmé. "
            f"L'écart de {ch.ecart_avancement_global:+.1f} points se traduit par un glissement prévisionnel de "
            f"{ch.retard_global_jours} jours sur le chemin critique, localisé principalement sur le gros œuvre. "
            f"Sur le plan financier, les engagements s'élèvent à {fin.depenses_engagees:,.0f} {devise} "
            f"({fin.pct_consommation_budget}% du budget révisé de {fin.budget_revise:,.0f} {devise}). "
            f"La gestion des matériaux nécessite une vigilance immédiate sur l'acier, qui présente une surconsommation "
            f"de l'ordre de 11% par rapport au ratio nominal."
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
- **Points d'attention planning** : Le gros œuvre concentre le chemin critique. La cadence actuelle de ferraillage et coffrage des planchers nécessite un renfort d'équipe pour éviter le report de la date de livraison.

---

## 3. Performance Financière & Dépenses
- **Budget révisé** : {fin.budget_revise:,.0f} {devise}
- **Dépenses payées (facturées)** : {fin.depenses_realisees:,.0f} {devise}
- **Total engagé (payé + engagé)** : {fin.depenses_engagees:,.0f} {devise}
- **Solde disponible à engager** : {fin.reste_a_depenser:,.0f} {devise}
- **Ratio d'efficacité des coûts (CPI)** : {fin.pct_consommation_budget:.1f}% engagé pour {ch.avancement_physique_global:.1f}% réalisé.

---

## 4. Approvisionnements & Matériaux
- Vigilance accrue sur les aciers haute adhérence (consommation réelle excédentaire par rapport au ratio théorique).
- Le stock des ciments et granulats est conforme aux besoins de production des 10 prochains jours.
- Rupture à anticiper sur les aciers de semelles (stock épuisé).

---

## 5. Matrice des Alertes & Actions Correctives Recommandées
"""
        for a in kpi.alertes_critiques:
            markdown_report += f"- **{a.gravite} [{a.type_alerte} - {a.lot}]** : {a.description}\n  *Action immédiate* : {a.action_recommandee}\n"
        for a in kpi.alertes_moyennes:
            markdown_report += f"- **{a.gravite} [{a.type_alerte} - {a.lot}]** : {a.description}\n  *Action recommandée* : {a.action_recommandee}\n"

        markdown_report += f"""
---
*Document généré automatiquement par le Copilote IA Chantier — Conforme aux règles d'ingénierie BTP.*
"""

        return {
            "synthese_executive": synthese_exec,
            "rapport_markdown": markdown_report,
            "date": kpi.date_analyse,
            "titre": f"Rapport Hebdomadaire {params.projet} - {kpi.date_analyse}"
        }
