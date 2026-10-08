"""
core/models.py
Modèles de données pour le Copilote IA de Chantier BTP.
Définit les structures pour les 9 feuilles Excel et les KPI calculés.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Dict, Any


@dataclass
class ProjectParams:
    """Feuille PARAMETRES"""
    projet: str = "Immeuble R+4"
    client: str = "Société XYZ"
    localisation: str = "Abidjan"
    ingenieur: str = "Ingénieur Principal"
    date_debut: Optional[str] = "2026-10-01"
    date_fin_prevue: Optional[str] = "2027-06-30"
    budget_initial: float = 350_000_000.0
    budget_revise: float = 350_000_000.0
    devise: str = "FCFA"


@dataclass
class LotItem:
    """Feuille LOTS"""
    id_lot: str
    lot: str
    responsable: str
    budget: float
    debut_prevu: str
    fin_prevue: str


@dataclass
class PlanningTask:
    """Feuille PLANNING"""
    id_tache: str
    lot: str
    tache: str
    debut_prevu: str
    fin_prevue: str
    debut_reel: Optional[str] = None
    fin_reelle: Optional[str] = None
    pct_prevu: float = 0.0      # entre 0.0 et 100.0
    pct_reel: float = 0.0       # entre 0.0 et 100.0
    statut: str = "Non démarré" # Non démarré, En cours, Terminé, En retard
    ecart: float = 0.0          # pct_reel - pct_prevu


@dataclass
class BudgetItem:
    """Feuille BUDGET"""
    id_budget: str
    lot: str
    poste: str
    quantite_prevue: float
    unite: str
    prix_unitaire: float
    budget: float = 0.0


@dataclass
class ExpenseItem:
    """Feuille DEPENSES"""
    date: str
    lot: str
    poste: str
    fournisseur: str
    reference: str
    quantite: float
    montant: float
    statut: str = "Payé" # Payé, Engagé, En attente


@dataclass
class MaterialItem:
    """Feuille MATERIAUX"""
    date: str
    lot: str
    materiau: str
    quantite_prevue: float
    quantite_recue: float
    quantite_consommee: float
    stock: float
    unite: str
    surconsommation_pct: float = 0.0


@dataclass
class WorkforceItem:
    """Feuille MAIN_OEUVRE"""
    date: str
    lot: str
    equipe: str
    nb_ouvriers: int
    heures: float
    cout: float
    tache_associee: Optional[str] = None


@dataclass
class ProgressItem:
    """Feuille AVANCEMENT (alimentée automatiquement)"""
    date: str
    lot: str
    pct_prevu: float
    pct_realise: float
    ecart: float
    tendance: str # 🟢, 🟠, 🔴


@dataclass
class AlertItem:
    """Feuille ALERTES (générée automatiquement)"""
    date: str
    type_alerte: str # Budget, Planning, Matériau, Main-d'œuvre, Données
    lot: str
    gravite: str     # 🔴 Haute, 🟠 Moyenne, 🟢 Faible
    description: str
    action_recommandee: str


@dataclass
class ValidationReport:
    """Rapport du moteur de validation des données"""
    total_lignes: int = 0
    nb_lots: int = 0
    nb_taches: int = 0
    nb_fournisseurs: int = 0
    valeurs_manquantes: List[str] = field(default_factory=list)
    doublons: List[str] = field(default_factory=list)
    anomalies_prix: List[str] = field(default_factory=list)
    anomalies_dates: List[str] = field(default_factory=list)
    est_valide: bool = True


@dataclass
class FinancialSummary:
    budget_initial: float = 0.0
    budget_revise: float = 0.0
    depenses_engagees: float = 0.0
    depenses_realisees: float = 0.0
    reste_a_depenser: float = 0.0
    ecart_budgetaire: float = 0.0
    pct_consommation_budget: float = 0.0
    eac: float = 0.0 # Estimate At Completion


@dataclass
class SiteSummary:
    avancement_physique_global: float = 0.0
    avancement_prevu_global: float = 0.0
    ecart_avancement_global: float = 0.0
    avancement_financier: float = 0.0
    ecart_physique_financier: float = 0.0
    nb_taches_total: int = 0
    nb_taches_terminees: int = 0
    nb_taches_en_cours: int = 0
    nb_taches_en_retard: int = 0
    retard_global_jours: int = 0


@dataclass
class KPISummary:
    """Tableau de bord consolidé"""
    date_analyse: str
    parametres: ProjectParams
    finances: FinancialSummary
    chantier: SiteSummary
    materiaux_alertes: List[Dict[str, Any]] = field(default_factory=list)
    main_oeuvre_stats: Dict[str, Any] = field(default_factory=list)
    alertes_critiques: List[AlertItem] = field(default_factory=list)
    alertes_moyennes: List[AlertItem] = field(default_factory=list)
    alertes_normales: List[AlertItem] = field(default_factory=list)
    repartition_lots: List[Dict[str, Any]] = field(default_factory=list)
