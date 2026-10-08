"""
core/ingestion.py
Moteur d'ingestion des classeurs Excel de chantier.
Lit les 9 feuilles, normalise les noms de colonnes et charge les données en mémoire.
"""
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd
import openpyxl
from core.models import (
    ProjectParams, LotItem, PlanningTask, BudgetItem, 
    ExpenseItem, MaterialItem, WorkforceItem, ProgressItem, AlertItem
)


EXPECTED_SHEETS = [
    "PARAMETRES", "LOTS", "PLANNING", "BUDGET", 
    "DEPENSES", "MATERIAUX", "MAIN_OEUVRE", "AVANCEMENT", "ALERTES"
]


def _normalize_str(val: Any) -> str:
    """Nettoie et normalise une chaîne de caractères."""
    if val is None or pd.isna(val):
        return ""
    return str(val).strip()


def _to_float(val: Any, default: float = 0.0) -> float:
    """Convertit une valeur en float de manière sécurisée."""
    if val is None or pd.isna(val):
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        clean_val = str(val).replace(" ", "").replace("\xa0", "").replace(",", ".").replace("%", "")
        return float(clean_val)
    except (ValueError, TypeError):
        return default


def _to_int(val: Any, default: int = 0) -> int:
    """Convertit une valeur en int de manière sécurisée."""
    if val is None or pd.isna(val):
        return default
    try:
        return int(_to_float(val, default=float(default)))
    except (ValueError, TypeError):
        return default


def _to_date_str(val: Any) -> str:
    """Normalise les dates au format YYYY-MM-DD."""
    if val is None or pd.isna(val) or val == "":
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    val_str = str(val).strip()
    # Essai de parsing simple
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return pd.to_datetime(val_str, format=fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    try:
        dt = pd.to_datetime(val_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return val_str


class ExcelIngestionEngine:
    """Moteur de lecture et d'ingestion robuste de classeur chantier."""
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable : {filepath}")
        self.sheets_found: List[str] = []
        self.raw_dfs: Dict[str, pd.DataFrame] = {}
        
    def inspect_file(self) -> Dict[str, Any]:
        """Inspecte la présence et l'intégrité des feuilles."""
        wb = openpyxl.load_workbook(self.filepath, read_only=True)
        self.sheets_found = wb.sheetnames
        wb.close()
        
        missing = [s for s in EXPECTED_SHEETS if s not in self.sheets_found]
        return {
            "sheets_found": self.sheets_found,
            "missing_sheets": missing,
            "has_all_sheets": len(missing) == 0
        }
        
    def load_all(self) -> Dict[str, Any]:
        """Charge et parse l'ensemble des données du classeur."""
        self.inspect_file()
        
        # Lecture par pandas
        excel_file = pd.ExcelFile(self.filepath)
        for s in excel_file.sheet_names:
            self.raw_dfs[s] = excel_file.parse(s)
            
        data = {
            "parametres": self._parse_parametres(),
            "lots": self._parse_lots(),
            "planning": self._parse_planning(),
            "budget": self._parse_budget(),
            "depenses": self._parse_depenses(),
            "materiaux": self._parse_materiaux(),
            "main_oeuvre": self._parse_main_oeuvre(),
            "avancement": self._parse_avancement(),
            "alertes": self._parse_alertes(),
            "raw_dfs": self.raw_dfs
        }
        return data

    def _parse_parametres(self) -> ProjectParams:
        params = ProjectParams()
        if "PARAMETRES" not in self.raw_dfs:
            return params
            
        df = self.raw_dfs["PARAMETRES"]
        # On attend colonnes Champ / Valeur
        col_names = [str(c).lower().strip() for c in df.columns]
        champ_col = df.columns[0]
        val_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        
        param_dict = {}
        for _, row in df.iterrows():
            k = _normalize_str(row[champ_col]).lower()
            v = row[val_col]
            param_dict[k] = v
            
        params.projet = _normalize_str(param_dict.get("projet", params.projet))
        params.client = _normalize_str(param_dict.get("client", params.client))
        params.localisation = _normalize_str(param_dict.get("localisation", params.localisation))
        params.ingenieur = _normalize_str(param_dict.get("ingénieur", param_dict.get("ingenieur", params.ingenieur)))
        params.date_debut = _to_date_str(param_dict.get("date début", param_dict.get("date debut", params.date_debut)))
        params.date_fin_prevue = _to_date_str(param_dict.get("date fin prévue", param_dict.get("date fin prevue", params.date_fin_prevue)))
        params.budget_initial = _to_float(param_dict.get("budget initial", params.budget_initial))
        params.budget_revise = _to_float(param_dict.get("budget révisé", param_dict.get("budget revise", params.budget_initial)))
        params.devise = _normalize_str(param_dict.get("devise", params.devise)) or "FCFA"
        return params

    def _parse_lots(self) -> List[LotItem]:
        lots = []
        if "LOTS" not in self.raw_dfs:
            return lots
        df = self.raw_dfs["LOTS"]
        for _, row in df.iterrows():
            # ID_Lot, Lot, Responsable, Budget, Début prévu, Fin prévue
            id_lot = _normalize_str(row.get("ID_Lot", row.get("ID", "")))
            nom_lot = _normalize_str(row.get("Lot", ""))
            if not nom_lot and not id_lot:
                continue
            lots.append(LotItem(
                id_lot=id_lot,
                lot=nom_lot,
                responsable=_normalize_str(row.get("Responsable", "")),
                budget=_to_float(row.get("Budget", 0)),
                debut_prevu=_to_date_str(row.get("Début prévu", row.get("Debut prevu", ""))),
                fin_prevue=_to_date_str(row.get("Fin prévue", row.get("Fin prevue", "")))
            ))
        return lots

    def _parse_planning(self) -> List[PlanningTask]:
        tasks = []
        if "PLANNING" not in self.raw_dfs:
            return tasks
        df = self.raw_dfs["PLANNING"]
        for _, row in df.iterrows():
            t_id = _normalize_str(row.get("ID", row.get("ID_Tache", "")))
            t_nom = _normalize_str(row.get("Tâche", row.get("Tache", "")))
            if not t_nom and not t_id:
                continue
            pct_p = _to_float(row.get("% prévu", row.get("% prevu", row.get("Prevu", 0))))
            pct_r = _to_float(row.get("% réel", row.get("% reel", row.get("Reel", 0))))
            # Si les % sont fournis sous forme décimale (ex: 0.70 au lieu de 70), convertir
            if 0 < pct_p <= 1.0 and pct_p != 1:
                pct_p = pct_p * 100.0
            elif pct_p == 1.0 and 0 < pct_r <= 1.0: # cas ou 1 signifie 100%
                pct_p = 100.0
            if 0 < pct_r <= 1.0 and pct_r != 1:
                pct_r = pct_r * 100.0
            elif pct_r == 1.0:
                pct_r = 100.0
                
            tasks.append(PlanningTask(
                id_tache=t_id,
                lot=_normalize_str(row.get("Lot", "")),
                tache=t_nom,
                debut_prevu=_to_date_str(row.get("Début prévu", row.get("Debut prevu", ""))),
                fin_prevue=_to_date_str(row.get("Fin prévue", row.get("Fin prevue", ""))),
                debut_reel=_to_date_str(row.get("Début réel", row.get("Debut reel", ""))),
                fin_reelle=_to_date_str(row.get("Fin réelle", row.get("Fin reelle", ""))),
                pct_prevu=round(pct_p, 1),
                pct_reel=round(pct_r, 1),
                statut=_normalize_str(row.get("Statut", "Non démarré")),
                ecart=round(pct_r - pct_p, 1)
            ))
        return tasks

    def _parse_budget(self) -> List[BudgetItem]:
        items = []
        if "BUDGET" not in self.raw_dfs:
            return items
        df = self.raw_dfs["BUDGET"]
        for _, row in df.iterrows():
            b_id = _normalize_str(row.get("ID", row.get("ID_Budget", "")))
            poste = _normalize_str(row.get("Poste", ""))
            if not poste and not b_id:
                continue
            qte = _to_float(row.get("Quantité prévue", row.get("Quantite prevue", 0)))
            pu = _to_float(row.get("Prix unitaire", 0))
            b_total = _to_float(row.get("Budget", qte * pu))
            if b_total == 0 and qte > 0 and pu > 0:
                b_total = qte * pu
            items.append(BudgetItem(
                id_budget=b_id,
                lot=_normalize_str(row.get("Lot", "")),
                poste=poste,
                quantite_prevue=qte,
                unite=_normalize_str(row.get("Unité", row.get("Unite", ""))),
                prix_unitaire=pu,
                budget=b_total
            ))
        return items

    def _parse_depenses(self) -> List[ExpenseItem]:
        depenses = []
        if "DEPENSES" not in self.raw_dfs:
            return depenses
        df = self.raw_dfs["DEPENSES"]
        for _, row in df.iterrows():
            poste = _normalize_str(row.get("Poste", ""))
            fournisseur = _normalize_str(row.get("Fournisseur", ""))
            montant = _to_float(row.get("Montant", 0))
            if not poste and montant == 0:
                continue
            depenses.append(ExpenseItem(
                date=_to_date_str(row.get("Date", "")),
                lot=_normalize_str(row.get("Lot", "")),
                poste=poste,
                fournisseur=fournisseur,
                reference=_normalize_str(row.get("Référence", row.get("Reference", ""))),
                quantite=_to_float(row.get("Quantité", row.get("Quantite", 0))),
                montant=montant,
                statut=_normalize_str(row.get("Statut", "Payé"))
            ))
        return depenses

    def _parse_materiaux(self) -> List[MaterialItem]:
        materiaux = []
        if "MATERIAUX" not in self.raw_dfs:
            return materiaux
        df = self.raw_dfs["MATERIAUX"]
        for _, row in df.iterrows():
            mat = _normalize_str(row.get("Matériau", row.get("Materiau", "")))
            if not mat:
                continue
            q_prev = _to_float(row.get("Quantité prévue", row.get("Quantite prevue", 0)))
            q_rec = _to_float(row.get("Quantité reçue", row.get("Quantite recue", 0)))
            q_cons = _to_float(row.get("Quantité consommée", row.get("Quantite consommee", 0)))
            stock = _to_float(row.get("Stock", q_rec - q_cons))
            materiaux.append(MaterialItem(
                date=_to_date_str(row.get("Date", "")),
                lot=_normalize_str(row.get("Lot", "")),
                materiau=mat,
                quantite_prevue=q_prev,
                quantite_recue=q_rec,
                quantite_consommee=q_cons,
                stock=stock,
                unite=_normalize_str(row.get("Unité", row.get("Unite", "")))
            ))
        return materiaux

    def _parse_main_oeuvre(self) -> List[WorkforceItem]:
        mo_list = []
        if "MAIN_OEUVRE" not in self.raw_dfs:
            return mo_list
        df = self.raw_dfs["MAIN_OEUVRE"]
        for _, row in df.iterrows():
            equipe = _normalize_str(row.get("Équipe", row.get("Equipe", "")))
            lot = _normalize_str(row.get("Lot", ""))
            if not equipe and not lot:
                continue
            mo_list.append(WorkforceItem(
                date=_to_date_str(row.get("Date", "")),
                lot=lot,
                equipe=equipe,
                nb_ouvriers=_to_int(row.get("Nombre ouvriers", row.get("Nb ouvriers", 0))),
                heures=_to_float(row.get("Heures", 0)),
                cout=_to_float(row.get("Coût", row.get("Cout", 0))),
                tache_associee=_normalize_str(row.get("Tâche associée", row.get("Tache associee", "")))
            ))
        return mo_list

    def _parse_avancement(self) -> List[ProgressItem]:
        av_list = []
        if "AVANCEMENT" not in self.raw_dfs:
            return av_list
        df = self.raw_dfs["AVANCEMENT"]
        for _, row in df.iterrows():
            lot = _normalize_str(row.get("Lot", ""))
            if not lot:
                continue
            pct_p = _to_float(row.get("% prévu", row.get("% prevu", 0)))
            pct_r = _to_float(row.get("% réalisé", row.get("% realise", 0)))
            if 0 < pct_p <= 1.0 and pct_p != 1:
                pct_p *= 100.0
            elif pct_p == 1.0 and 0 < pct_r <= 1.0:
                pct_p = 100.0
            if 0 < pct_r <= 1.0 and pct_r != 1:
                pct_r *= 100.0
            elif pct_r == 1.0:
                pct_r = 100.0
            ecart = _to_float(row.get("Écart", row.get("Ecart", pct_r - pct_p)))
            av_list.append(ProgressItem(
                date=_to_date_str(row.get("Date", "")),
                lot=lot,
                pct_prevu=round(pct_p, 1),
                pct_realise=round(pct_r, 1),
                ecart=round(ecart, 1),
                tendance=_normalize_str(row.get("Tendance", "🟢"))
            ))
        return av_list

    def _parse_alertes(self) -> List[AlertItem]:
        alt_list = []
        if "ALERTES" not in self.raw_dfs:
            return alt_list
        df = self.raw_dfs["ALERTES"]
        for _, row in df.iterrows():
            desc = _normalize_str(row.get("Description", ""))
            if not desc:
                continue
            alt_list.append(AlertItem(
                date=_to_date_str(row.get("Date", "")),
                type_alerte=_normalize_str(row.get("Type", "Général")),
                lot=_normalize_str(row.get("Lot", "")),
                gravite=_normalize_str(row.get("Gravité", row.get("Gravite", "🟠 Moyenne"))),
                description=desc,
                action_recommandee=_normalize_str(row.get("Action recommandée", row.get("Action", "")))
            ))
        return alt_list
