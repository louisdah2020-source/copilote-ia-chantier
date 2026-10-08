"""
ai_agents/planning_engineer.py
Agent 3 — Planning Engineer
Spécialiste de la planification de chantier, du chemin critique,
de la détection des retards et des projections de dates d'achèvement.
"""
from typing import Dict, Any, Optional
from ai_agents.base_agent import BaseChantierAgent
from core.models import KPISummary, ValidationReport


class PlanningEngineerAgent(BaseChantierAgent):
    """Spécialiste de l'ordonnancement, du chemin critique et du pilotage des délais."""

    def __init__(self):
        super().__init__(name="Planning Engineer", role="Pilotage des délais, planning et chemin critique")

    def analyze(self, kpi: KPISummary, validation: Optional[ValidationReport] = None, trends: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ch = kpi.chantier
        av_reel = ch.avancement_physique_global
        av_prevu = ch.avancement_prevu_global
        ecart = ch.ecart_avancement_global
        retard_jours = ch.retard_global_jours

        # Lots avec le plus de retard
        lots_retard = sorted(
            [l for l in kpi.repartition_lots if l["ecart_avancement"] < 0],
            key=lambda x: x["ecart_avancement"]
        )

        # Gravité de la situation
        if ecart <= -6.0 or retard_jours >= 7:
            statut = "🔴 Situation préoccupante (Retard critique)"
        elif ecart < 0.0 or retard_jours > 0:
            statut = "🟠 Retard modéré sous surveillance"
        else:
            statut = "🟢 Planning conforme ou en avance"

        # Synthèse rédigée
        commentaire = (
            f"Le chantier affiche un avancement physique global pondéré de {av_reel}%, "
            f"contre {av_prevu}% prévu au planning contractuel (écart de {ecart:+.1f} points). "
        )

        if lots_retard:
            noms_lots = ", ".join(f"'{l['lot']}' ({l['ecart_avancement']} pts)" for l in lots_retard[:3])
            commentaire += f"Le retard est principalement concentré sur les lots : {noms_lots}. "
            commentaire += (
                f"Le retard estimé est de {retard_jours} jours, sur la base des écarts d'avancement et des durées prévues. "
                f"Il s'agit d'une approximation : le classeur ne décrit pas les dépendances entre tâches nécessaires "
                f"au calcul d'un chemin critique ni à une date de fin recalculée."
            )
        else:
            commentaire += "Aucun lot majeur ne présente de dérive négative significative sur les jalons clés."

        recommandations = []
        if lots_retard:
            recommandations.append(f"Renforcer les effectifs sur le lot '{lots_retard[0]['lot']}' (équipes coffrage/ferraillage).")
            recommandations.append("Autoriser les plages de travail étendues (heures supplémentaires ou samedi matin).")
            recommandations.append("Renseigner les dépendances entre tâches avant de recalculer le chemin critique et les dates de livraison.")
        else:
            recommandations.append("Maintenir la cadence d'exécution et sécuriser les réceptions partielles.")

        return {
            "statut": statut,
            "synthese": commentaire,
            "avancement_physique": av_reel,
            "avancement_prevu": av_prevu,
            "ecart_points": ecart,
            "retard_estime_jours": retard_jours,
            "lots_en_retard": lots_retard,
            "taches_terminees": ch.nb_taches_terminees,
            "taches_en_cours": ch.nb_taches_en_cours,
            "taches_en_retard": ch.nb_taches_en_retard,
            "recommandations": recommandations
        }
