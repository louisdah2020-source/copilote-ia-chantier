"""
core/validation.py
Moteur de validation et de contrôle qualité des données de chantier.
Détecte les doublons, valeurs manquantes, incohérences de dates, quantités et prix.
"""
from typing import Dict, Any, List
from core.models import ValidationReport


class DataValidationEngine:
    """Contrôle la conformité et l'intégrité des données d'un classeur chantier."""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.report = ValidationReport()
        
    def validate(self) -> ValidationReport:
        """Exécute tous les contrôles qualité sur les feuilles."""
        self._count_entities()
        self._check_duplicates()
        self._check_dates()
        self._check_budget_and_prices()
        self._check_missing_values()
        
        # Le fichier est valide si aucune incohérence bloquante n'est détectée
        self.report.est_valide = (
            len(self.report.anomalies_prix) == 0 and 
            len(self.report.anomalies_dates) == 0
        )
        return self.report

    def _count_entities(self):
        lots = self.data.get("lots", [])
        tasks = self.data.get("planning", [])
        depenses = self.data.get("depenses", [])
        
        self.report.nb_lots = len(lots)
        self.report.nb_taches = len(tasks)
        
        # Nombre de fournisseurs uniques
        fournisseurs = {d.fournisseur for d in depenses if d.fournisseur}
        self.report.nb_fournisseurs = len(fournisseurs)
        
        # Total de lignes analysées
        raw_dfs = self.data.get("raw_dfs", {})
        total_rows = sum(len(df) for df in raw_dfs.values())
        self.report.total_lignes = total_rows

    def _check_duplicates(self):
        """Vérifie l'unicité des clés primaires (ID Lots, ID Tâches, Références factures)."""
        # 1. Doublons Lots
        lot_ids = set()
        for lot in self.data.get("lots", []):
            if lot.id_lot in lot_ids:
                self.report.doublons.append(f"Doublon ID Lot détecté : {lot.id_lot} ({lot.lot})")
            lot_ids.add(lot.id_lot)
            
        # 2. Doublons Tâches
        task_ids = set()
        for t in self.data.get("planning", []):
            if t.id_tache in task_ids:
                self.report.doublons.append(f"Doublon ID Tâche détecté : {t.id_tache} ({t.tache})")
            task_ids.add(t.id_tache)
            
        # 3. Doublons Factures (mêmes fournisseur + référence)
        invoices = set()
        for dep in self.data.get("depenses", []):
            if dep.fournisseur and dep.reference:
                key = (dep.fournisseur.lower(), dep.reference.lower())
                if key in invoices:
                    self.report.doublons.append(
                        f"Facture en doublon potentiel : {dep.reference} ({dep.fournisseur}) - Montant {dep.montant:,.0f}"
                    )
                invoices.add(key)

    def _check_dates(self):
        """Vérifie que début <= fin et cohérence chronologique."""
        # Vérification sur les lots
        for lot in self.data.get("lots", []):
            if lot.debut_prevu and lot.fin_prevue and lot.debut_prevu > lot.fin_prevue:
                self.report.anomalies_dates.append(
                    f"Lot '{lot.lot}' : Date début ({lot.debut_prevu}) postérieure à date fin ({lot.fin_prevue})"
                )
                
        # Vérification sur les tâches planning
        for t in self.data.get("planning", []):
            if t.debut_prevu and t.fin_prevue and t.debut_prevu > t.fin_prevue:
                self.report.anomalies_dates.append(
                    f"Tâche '{t.tache}' : Début prévu ({t.debut_prevu}) > Fin prévue ({t.fin_prevue})"
                )
            if t.debut_reel and t.fin_reelle and t.debut_reel > t.fin_reelle:
                self.report.anomalies_dates.append(
                    f"Tâche '{t.tache}' : Début réel ({t.debut_reel}) > Fin réelle ({t.fin_reelle})"
                )

    def _check_budget_and_prices(self):
        """Vérifie les prix unitaires aberrants, les montants négatifs ou nuls."""
        # Vérification budget
        for b in self.data.get("budget", []):
            if b.quantite_prevue <= 0:
                self.report.anomalies_prix.append(
                    f"Poste budget '{b.poste}' ({b.lot}) : Quantité prévue nulle ou négative ({b.quantite_prevue})"
                )
            if b.prix_unitaire <= 0:
                self.report.anomalies_prix.append(
                    f"Poste budget '{b.poste}' ({b.lot}) : Prix unitaire anormal ({b.prix_unitaire:,.0f})"
                )
                
        # Vérification dépenses
        for d in self.data.get("depenses", []):
            if d.montant < 0:
                self.report.anomalies_prix.append(
                    f"Dépense '{d.poste}' : Montant négatif ({d.montant:,.0f})"
                )

    def _check_missing_values(self):
        """Identifie les champs obligatoires vides."""
        for t in self.data.get("planning", []):
            if not t.lot:
                self.report.valeurs_manquantes.append(f"Tâche '{t.tache}' : Aucun lot rattaché")
            if not t.debut_prevu or not t.fin_prevue:
                self.report.valeurs_manquantes.append(f"Tâche '{t.tache}' : Dates prévues manquantes")
                
        for m in self.data.get("materiaux", []):
            if not m.unite:
                self.report.valeurs_manquantes.append(f"Matériau '{m.materiau}' : Unité manquante")
