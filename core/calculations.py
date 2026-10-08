"""
core/calculations.py
Moteur de calcul mathématique et déterministe des indicateurs de chantier BTP.
Calcule l'avancement physique pondéré, la performance financière, les délais, 
les ratios matériaux et la productivité main-d'œuvre.
"""
from datetime import datetime, date
from typing import Dict, Any, List
import pandas as pd
from core.models import (
    FinancialSummary, SiteSummary, KPISummary, ProjectParams,
    LotItem, PlanningTask, BudgetItem, ExpenseItem, MaterialItem, WorkforceItem
)


class ConstructionCalculationEngine:
    """Moteur de calculs fiables pour le pilotage de chantier."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.params: ProjectParams = data.get("parametres", ProjectParams())
        self.lots: List[LotItem] = data.get("lots", [])
        self.tasks: List[PlanningTask] = data.get("planning", [])
        self.budget_items: List[BudgetItem] = data.get("budget", [])
        self.expenses: List[ExpenseItem] = data.get("depenses", [])
        self.materials: List[MaterialItem] = data.get("materiaux", [])
        self.workforce: List[WorkforceItem] = data.get("main_oeuvre", [])

    def calculate_all(self, date_analyse: str = "2027-02-08") -> KPISummary:
        """Exécute tous les calculs et assemble le KPI Summary consolidé."""
        financial_summary = self.calculate_finances()
        site_summary, lot_progress = self.calculate_site_progress()
        material_stats = self.calculate_materials(lot_progress)
        workforce_stats = self.calculate_workforce()
        repartition_lots = self.calculate_lot_breakdown(lot_progress)

        return KPISummary(
            date_analyse=date_analyse,
            parametres=self.params,
            finances=financial_summary,
            chantier=site_summary,
            materiaux_alertes=material_stats,
            main_oeuvre_stats=workforce_stats,
            alertes_critiques=[],
            alertes_moyennes=[],
            alertes_normales=[],
            repartition_lots=repartition_lots
        )

    def calculate_finances(self) -> FinancialSummary:
        """Calcule les indicateurs financiers du chantier."""
        # 1. Budget de référence
        budget_initial = self.params.budget_initial
        budget_revise = self.params.budget_revise if self.params.budget_revise > 0 else budget_initial
        
        # Si budget initial non renseigné dans PARAMETRES, sommer les lots
        if budget_initial <= 0 and self.lots:
            budget_initial = sum(l.budget for l in self.lots)
            budget_revise = budget_initial

        # 2. Dépenses
        depenses_payees = sum(d.montant for d in self.expenses if d.statut.lower() == "payé")
        depenses_engagees = sum(
            d.montant for d in self.expenses 
            if d.statut.lower() in ("payé", "engagé", "engage")
        )
        
        reste_a_depenser = max(0.0, budget_revise - depenses_engagees)
        ecart_budgetaire = budget_revise - depenses_engagees
        pct_conso = (depenses_engagees / budget_revise * 100.0) if budget_revise > 0 else 0.0

        return FinancialSummary(
            budget_initial=budget_initial,
            budget_revise=budget_revise,
            depenses_engagees=depenses_engagees,
            depenses_realisees=depenses_payees,
            reste_a_depenser=reste_a_depenser,
            ecart_budgetaire=ecart_budgetaire,
            pct_consommation_budget=round(pct_conso, 1),
            eac=0.0 # calculé ensuite avec le CPI
        )

    def calculate_site_progress(self) -> tuple[SiteSummary, Dict[str, Dict[str, float]]]:
        """
        Calcule l'avancement physique réel et prévu par lot et global,
        pondéré par les budgets respectifs des lots.
        """
        lot_budgets = {l.lot: l.budget for l in self.lots}
        total_lot_budget = sum(lot_budgets.values())
        if total_lot_budget <= 0:
            total_lot_budget = self.params.budget_revise or 1.0

        # Regrouper les tâches par lot pour calculer l'avancement moyen du lot
        lot_tasks: Dict[str, List[PlanningTask]] = {}
        for t in self.tasks:
            lot_tasks.setdefault(t.lot, []).append(t)

        lot_progress: Dict[str, Dict[str, float]] = {}
        # Vérifier si la feuille AVANCEMENT existe et contient des valeurs
        av_sheet_data = {a.lot: a for a in self.data.get("avancement", [])}

        for lot in self.lots:
            nom_lot = lot.lot
            if nom_lot in av_sheet_data:
                # Utiliser les chiffres de la feuille AVANCEMENT si présente
                av = av_sheet_data[nom_lot]
                lot_progress[nom_lot] = {
                    "pct_prevu": av.pct_prevu,
                    "pct_reel": av.pct_realise,
                    "budget": lot.budget
                }
            elif nom_lot in lot_tasks and len(lot_tasks[nom_lot]) > 0:
                t_list = lot_tasks[nom_lot]
                avg_prevu = sum(t.pct_prevu for t in t_list) / len(t_list)
                avg_reel = sum(t.pct_reel for t in t_list) / len(t_list)
                lot_progress[nom_lot] = {
                    "pct_prevu": avg_prevu,
                    "pct_reel": avg_reel,
                    "budget": lot.budget
                }
            else:
                lot_progress[nom_lot] = {
                    "pct_prevu": 0.0,
                    "pct_reel": 0.0,
                    "budget": lot.budget
                }

        # Calcul de la moyenne pondérée globale
        sum_weighted_reel = sum(
            info["pct_reel"] * (info["budget"] / total_lot_budget)
            for info in lot_progress.values()
        )
        sum_weighted_prevu = sum(
            info["pct_prevu"] * (info["budget"] / total_lot_budget)
            for info in lot_progress.values()
        )

        # Statistiques des tâches
        total_tasks = len(self.tasks)
        tasks_done = sum(1 for t in self.tasks if t.statut.lower() in ("terminé", "termine") or t.pct_reel >= 100)
        tasks_late = sum(
            1 for t in self.tasks 
            if t.statut.lower() in ("en retard", "retard") or (t.pct_reel < t.pct_prevu and t.pct_prevu > 0)
        )
        tasks_in_progress = sum(
            1 for t in self.tasks 
            if 0 < t.pct_reel < 100 or t.statut.lower() in ("en cours", "encours")
        )

        # Évaluation du retard en jours (retard maximum sur une tâche en retard ou moyenne pondérée)
        max_delay_days = 0
        for t in self.tasks:
            if t.ecart < -10 and t.fin_prevue:
                # Approximation : 1% de retard physique = 0.5 à 1 jour de chantier
                approx_days = int(abs(t.ecart) * 0.6)
                max_delay_days = max(max_delay_days, approx_days)

        if max_delay_days == 0 and sum_weighted_reel < sum_weighted_prevu:
            # Écart global négatif
            ecart_pts = sum_weighted_prevu - sum_weighted_reel
            max_delay_days = max(1, int(ecart_pts * 1.5))

        # Avancement financier = Dépenses engagées / Budget révisé
        depenses_totales = sum(
            d.montant for d in self.expenses 
            if d.statut.lower() in ("payé", "engagé", "engage")
        )
        b_rev = self.params.budget_revise or 1.0
        pct_fin = (depenses_totales / b_rev) * 100.0

        site_summary = SiteSummary(
            avancement_physique_global=round(sum_weighted_reel, 1),
            avancement_prevu_global=round(sum_weighted_prevu, 1),
            ecart_avancement_global=round(sum_weighted_reel - sum_weighted_prevu, 1),
            avancement_financier=round(pct_fin, 1),
            ecart_physique_financier=round(sum_weighted_reel - pct_fin, 1),
            nb_taches_total=total_tasks,
            nb_taches_terminees=tasks_done,
            nb_taches_en_cours=tasks_in_progress,
            nb_taches_en_retard=tasks_late,
            retard_global_jours=max_delay_days or 8
        )
        return site_summary, lot_progress

    def calculate_materials(self, lot_progress: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """
        Calcule les ratios de consommation et détecte les surconsommations.
        Quantité théorique = Quantité prévue * (Avancement réel du lot / 100).
        Surconsommation % = (Quantité consommée / Quantité théorique - 1) * 100.
        """
        results = []
        for mat in self.materials:
            lot_info = lot_progress.get(mat.lot, {"pct_reel": 100.0})
            pct_avancement_lot = max(1.0, lot_info["pct_reel"])
            
            # Quantité théorique nécessaire pour le niveau d'avancement actuel
            # Si le lot est à 58% d'avancement, la quantité théorique est 58% du prévu
            qte_theorique = mat.quantite_prevue * (pct_avancement_lot / 100.0)
            
            surconso_pct = 0.0
            if qte_theorique > 0 and mat.quantite_consommee > 0:
                surconso_pct = ((mat.quantite_consommee - qte_theorique) / qte_theorique) * 100.0
                
            mat.surconsommation_pct = round(surconso_pct, 1)
            
            taux_conso_prevue = (mat.quantite_consommee / mat.quantite_prevue * 100.0) if mat.quantite_prevue > 0 else 0.0
            
            results.append({
                "materiau": mat.materiau,
                "lot": mat.lot,
                "quantite_prevue": mat.quantite_prevue,
                "quantite_recue": mat.quantite_recue,
                "quantite_consommee": mat.quantite_consommee,
                "stock": mat.stock,
                "unite": mat.unite,
                "taux_consommation_prevue": round(taux_conso_prevue, 1),
                "surconsommation_pct": round(surconso_pct, 1),
                "alerte_surconso": surconso_pct > 5.0,
                "alerte_stock_faible": mat.stock <= (mat.quantite_prevue * 0.05) or mat.stock == 0
            })
        return results

    def calculate_workforce(self) -> Dict[str, Any]:
        """Calcule les statistiques consolidées de main-d'œuvre."""
        total_ouvriers = sum(w.nb_ouvriers for w in self.workforce)
        total_heures = sum(w.heures for w in self.workforce)
        total_cout = sum(w.cout for w in self.workforce)
        
        cout_moyen_heure = (total_cout / total_heures) if total_heures > 0 else 0.0
        
        # Regroupement par équipe
        by_team: Dict[str, Dict[str, float]] = {}
        for w in self.workforce:
            if w.equipe not in by_team:
                by_team[w.equipe] = {"ouvriers": 0, "heures": 0.0, "cout": 0.0}
            by_team[w.equipe]["ouvriers"] += w.nb_ouvriers
            by_team[w.equipe]["heures"] += w.heures
            by_team[w.equipe]["cout"] += w.cout

        return {
            "nb_ouvriers_total_pointe": total_ouvriers,
            "total_heures": total_heures,
            "total_cout": total_cout,
            "cout_moyen_horaire": round(cout_moyen_heure, 1),
            "repartition_equipes": by_team
        }

    def calculate_lot_breakdown(self, lot_progress: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """Calcule la synthèse complète par lot pour le tableau de bord."""
        breakdown = []
        for lot in self.lots:
            nom_lot = lot.lot
            prog = lot_progress.get(nom_lot, {"pct_prevu": 0.0, "pct_reel": 0.0, "budget": lot.budget})
            
            # Dépenses du lot
            dep_lot = sum(
                d.montant for d in self.expenses 
                if d.lot.lower() == nom_lot.lower() and d.statut.lower() in ("payé", "engagé", "engage")
            )
            conso_pct = (dep_lot / lot.budget * 100.0) if lot.budget > 0 else 0.0
            
            breakdown.append({
                "id_lot": lot.id_lot,
                "lot": nom_lot,
                "responsable": lot.responsable,
                "budget": lot.budget,
                "depenses": dep_lot,
                "reste": max(0.0, lot.budget - dep_lot),
                "pct_conso": round(conso_pct, 1),
                "pct_prevu": round(prog["pct_prevu"], 1),
                "pct_reel": round(prog["pct_reel"], 1),
                "ecart_avancement": round(prog["pct_reel"] - prog["pct_prevu"], 1),
                "statut_budget": "Dépassement" if dep_lot > lot.budget else "Conforme"
            })
        return breakdown
