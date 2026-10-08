"""
core/alert_engine.py
Moteur d'alertes déterministe pour le pilotage de chantier.
Génère et classifie automatiquement les alertes métiers selon leur niveau de gravité :
🔴 Haute (Critique), 🟠 Moyenne (À surveiller), 🟢 Faible (Conforme).
"""
from datetime import datetime
from typing import List, Dict, Any
from core.models import AlertItem, KPISummary, ValidationReport


class AlertEngine:
    """Moteur de détection et de scoring des risques du chantier."""

    def __init__(self, kpi: KPISummary, validation_report: ValidationReport = None):
        self.kpi = kpi
        self.validation = validation_report
        self.alerts: List[AlertItem] = []

    def evaluate_all(self, today_str: str = None) -> List[AlertItem]:
        """Évalue l'ensemble des règles métiers et produit la liste ordonnée des alertes."""
        today_str = today_str or self.kpi.date_analyse
        self.alerts = []
        self._check_budget_alerts(today_str)
        self._check_planning_alerts(today_str)
        self._check_materials_alerts(today_str)
        self._check_validation_alerts(today_str)
        
        # Séparer dans le KPI summary
        self.kpi.alertes_critiques = [a for a in self.alerts if "🔴" in a.gravite]
        self.kpi.alertes_moyennes = [a for a in self.alerts if "🟠" in a.gravite]
        self.kpi.alertes_normales = [a for a in self.alerts if "🟢" in a.gravite]

        return self.alerts

    def _check_budget_alerts(self, today_str: str):
        """Vérifie les dépassements budgétaires globaux et par lot."""
        # 1. Alerte par lot
        for lot_data in self.kpi.repartition_lots:
            budget = lot_data["budget"]
            depenses = lot_data["depenses"]
            nom_lot = lot_data["lot"]
            
            if budget > 0:
                taux_conso = (depenses / budget) * 100.0
                avancement_reel = lot_data["pct_reel"]
                
                # Cas 1 : Dépassement effectif du budget total du lot
                if depenses > budget:
                    depassement_pct = round(((depenses - budget) / budget) * 100.0, 1)
                    self.alerts.append(AlertItem(
                        date=today_str,
                        type_alerte="Budget",
                        lot=nom_lot,
                        gravite="🔴 Haute",
                        description=f"Dépassement du budget contractuel de +{depassement_pct}% ({depenses:,.0f} / {budget:,.0f} {self.kpi.parametres.devise}).",
                        action_recommandee="Geler les engagements non essentiels et auditer les factures du lot immédiatement."
                    ))
                # Cas 2 : Dépenses disproportionnées par rapport à l'avancement physique
                elif taux_conso > (avancement_reel + 15.0) and avancement_reel < 90:
                    derive_pct = round(taux_conso - avancement_reel, 1)
                    self.alerts.append(AlertItem(
                        date=today_str,
                        type_alerte="Budget",
                        lot=nom_lot,
                        gravite="🟠 Moyenne",
                        description=f"Dérive financière : budget engagé à {taux_conso:.1f}% pour un avancement physique de seulement {avancement_reel:.1f}% (+{derive_pct} pts).",
                        action_recommandee="Contrôler les attachements contradictoires et valider l'avancement réel avant nouveau paiement."
                    ))

        # 2. Alerte globale
        if self.kpi.finances.budget_revise > 0:
            taux_global = self.kpi.finances.pct_consommation_budget
            av_global = self.kpi.chantier.avancement_physique_global
            if taux_global > (av_global + 10.0):
                self.alerts.append(AlertItem(
                    date=today_str,
                    type_alerte="Budget",
                    lot="Global Chantier",
                    gravite="🟠 Moyenne",
                    description=f"Consommation budgétaire globale ({taux_global}%) supérieure à l'avancement physique global ({av_global}%).",
                    action_recommandee="Mettre en place un plan de trésorerie prévisionnel et analyser les restes à dépenser."
                ))

    def _check_planning_alerts(self, today_str: str):
        """Vérifie les retards de planning et les dérives des jalons critiques."""
        for lot_data in self.kpi.repartition_lots:
            nom_lot = lot_data["lot"]
            ecart = lot_data["ecart_avancement"]
            
            # Écart critique (< -10 points)
            if ecart <= -10.0:
                self.alerts.append(AlertItem(
                    date=today_str,
                    type_alerte="Planning",
                    lot=nom_lot,
                    gravite="🔴 Haute",
                    description=f"Retard critique d'avancement de {abs(ecart):.1f} points sur le lot (Prévu: {lot_data['pct_prevu']}%, Réalisé: {lot_data['pct_reel']}%).",
                    action_recommandee="Renforcer immédiatement les effectifs sur le chemin critique et planifier des heures supplémentaires."
                ))
            # Écart modéré (-5 à -10 points)
            elif -10.0 < ecart <= -5.0:
                self.alerts.append(AlertItem(
                    date=today_str,
                    type_alerte="Planning",
                    lot=nom_lot,
                    gravite="🟠 Moyenne",
                    description=f"Retard modéré d'avancement de {abs(ecart):.1f} points par rapport au planning initial.",
                    action_recommandee="Réorganiser la rotation des équipes et sécuriser l'approvisionnement des postes suivants."
                ))

        # Retard global
        if self.kpi.chantier.retard_global_jours >= 5:
            self.alerts.append(AlertItem(
                date=today_str,
                type_alerte="Planning",
                lot="Gros œuvre / Chemin critique",
                gravite="🔴 Haute",
                description=f"Retard estimé à {self.kpi.chantier.retard_global_jours} jours d'après les dates et écarts disponibles dans le classeur.",
                action_recommandee="Vérifier les tâches concernées et recalculer les impacts à partir du planning détaillé et de ses dépendances."
            ))

    def _check_materials_alerts(self, today_str: str):
        """Vérifie la surconsommation des matériaux et les risques de rupture de stock."""
        for mat in self.kpi.materiaux_alertes:
            nom_mat = mat["materiau"]
            nom_lot = mat["lot"]
            surconso = mat["surconsommation_pct"]
            stock = mat["stock"]
            unite = mat["unite"]
            
            # Surconsommation critique (> +8%)
            if surconso >= 8.0:
                self.alerts.append(AlertItem(
                    date=today_str,
                    type_alerte="Matériau",
                    lot=nom_lot,
                    gravite="🔴 Haute",
                    description=f"Surconsommation anormale de {nom_mat} de +{surconso:.1f}% par rapport aux ratios théoriques d'ingénierie.",
                    action_recommandee="Vérifier la conformité du ferraillage/dosage, limiter les longueurs de recouvrement et contrôler les vols/pertes."
                ))
            elif 3.0 <= surconso < 8.0:
                self.alerts.append(AlertItem(
                    date=today_str,
                    type_alerte="Matériau",
                    lot=nom_lot,
                    gravite="🟠 Moyenne",
                    description=f"Légère surconsommation de {nom_mat} (+{surconso:.1f}%).",
                    action_recommandee="Sensibiliser les chefs d'équipe sur le gaspillage et surveiller les livraisons suivantes."
                ))
                
            # Rupture de stock
            if stock == 0 and mat["quantite_consommee"] < mat["quantite_prevue"]:
                self.alerts.append(AlertItem(
                    date=today_str,
                    type_alerte="Matériau",
                    lot=nom_lot,
                    gravite="🟠 Moyenne",
                    description=f"Rupture de stock imminente : Stock de {nom_mat} = 0 {unite}.",
                    action_recommandee="Passer commande de réapprovisionnement immédiatement pour éviter l'arrêt du poste."
                ))

    def _check_validation_alerts(self, today_str: str):
        """Intègre les anomalies de saisie détectées par le validateur."""
        if not self.validation:
            return
        if self.validation.doublons:
            for d in self.validation.doublons:
                self.alerts.append(AlertItem(
                    date=today_str,
                    type_alerte="Données",
                    lot="Contrôle Saisie",
                    gravite="🟠 Moyenne",
                    description=d,
                    action_recommandee="Supprimer ou corriger la ligne dupliquée dans le classeur Excel."
                ))
        if self.validation.anomalies_prix:
            for p in self.validation.anomalies_prix:
                self.alerts.append(AlertItem(
                    date=today_str,
                    type_alerte="Données",
                    lot="Contrôle Saisie",
                    gravite="🔴 Haute",
                    description=p,
                    action_recommandee="Vérifier le bordereau de prix unitaires dans la feuille BUDGET."
                ))
        for anomaly in self.validation.anomalies_dates:
            self.alerts.append(AlertItem(
                date=today_str, type_alerte="Données", lot="Contrôle Saisie",
                gravite="🔴 Haute", description=anomaly,
                action_recommandee="Corriger les dates dans le classeur avant d'interpréter les délais."
            ))
        for missing in self.validation.valeurs_manquantes:
            self.alerts.append(AlertItem(
                date=today_str, type_alerte="Données", lot="Contrôle Saisie",
                gravite="🟠 Moyenne", description=missing,
                action_recommandee="Compléter les champs requis puis relancer l'analyse."
            ))
