"""
core/history_store.py
Gestionnaire de la base de données historique SQLite pour les snapshots de chantier.
Permet d'enregistrer chaque passage hebdomadaire et de calculer les tendances temporelles.
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.models import KPISummary


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chantier_history.db"


class HistoryStore:
    """Gestionnaire SQLite de l'historique des snapshots de chantier."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialise la table des snapshots hebdomadaires."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_snapshot TEXT NOT NULL,
                    projet TEXT NOT NULL,
                    avancement_physique REAL NOT NULL,
                    avancement_prevu REAL NOT NULL,
                    budget_initial REAL NOT NULL,
                    depenses_engagees REAL NOT NULL,
                    depenses_realisees REAL NOT NULL,
                    retard_jours INTEGER NOT NULL,
                    nb_alertes_critiques INTEGER NOT NULL,
                    nb_alertes_moyennes INTEGER NOT NULL,
                    lots_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date_snapshot, projet)
                )
            """)
            conn.commit()

    def save_snapshot(self, kpi: KPISummary) -> int:
        """Enregistre ou met à jour le snapshot dans la base de données."""
        lots_data = json.dumps(kpi.repartition_lots, ensure_ascii=False)
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO snapshots (
                    date_snapshot, projet, avancement_physique, avancement_prevu,
                    budget_initial, depenses_engagees, depenses_realisees,
                    retard_jours, nb_alertes_critiques, nb_alertes_moyennes, lots_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date_snapshot, projet) DO UPDATE SET
                    avancement_physique = excluded.avancement_physique,
                    avancement_prevu = excluded.avancement_prevu,
                    depenses_engagees = excluded.depenses_engagees,
                    depenses_realisees = excluded.depenses_realisees,
                    retard_jours = excluded.retard_jours,
                    nb_alertes_critiques = excluded.nb_alertes_critiques,
                    nb_alertes_moyennes = excluded.nb_alertes_moyennes,
                    lots_json = excluded.lots_json
            """, (
                kpi.date_analyse,
                kpi.parametres.projet,
                kpi.chantier.avancement_physique_global,
                kpi.chantier.avancement_prevu_global,
                kpi.finances.budget_initial,
                kpi.finances.depenses_engagees,
                kpi.finances.depenses_realisees,
                kpi.chantier.retard_global_jours,
                len(kpi.alertes_critiques),
                len(kpi.alertes_moyennes),
                lots_data
            ))
            conn.commit()
            return cursor.lastrowid

    def get_history(self, projet: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère la chronologie de tous les snapshots enregistrés."""
        with self._get_connection() as conn:
            if projet:
                rows = conn.execute(
                    "SELECT * FROM snapshots WHERE projet = ? ORDER BY date_snapshot ASC",
                    (projet,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM snapshots ORDER BY date_snapshot ASC"
                ).fetchall()
                
            history = []
            for r in rows:
                history.append({
                    "id": r["id"],
                    "date": r["date_snapshot"],
                    "projet": r["projet"],
                    "avancement_physique": r["avancement_physique"],
                    "avancement_prevu": r["avancement_prevu"],
                    "budget_initial": r["budget_initial"],
                    "depenses_engagees": r["depenses_engagees"],
                    "depenses_realisees": r["depenses_realisees"],
                    "retard_jours": r["retard_jours"],
                    "nb_alertes_critiques": r["nb_alertes_critiques"],
                    "nb_alertes_moyennes": r["nb_alertes_moyennes"],
                    "lots": json.loads(r["lots_json"]) if r["lots_json"] else []
                })
            return history

    def calculate_trends(self, projet: Optional[str] = None) -> Dict[str, Any]:
        """Calcule la vélocité et les tendances entre le dernier snapshot et le précédent."""
        history = self.get_history(projet)
        if len(history) < 2:
            return {
                "has_trend": False,
                "delta_avancement": 0.0,
                "delta_depenses": 0.0,
                "delta_retard": 0,
                "velocite_hebdo": 0.0,
                "message": "Un seul snapshot disponible. Historique insuffisant pour calculer une tendance."
            }

        prev = history[-2]
        curr = history[-1]

        delta_av = curr["avancement_physique"] - prev["avancement_physique"]
        delta_dep = curr["depenses_engagees"] - prev["depenses_engagees"]
        delta_retard = curr["retard_jours"] - prev["retard_jours"]

        return {
            "has_trend": True,
            "date_precedente": prev["date"],
            "date_actuelle": curr["date"],
            "delta_avancement": round(delta_av, 1),
            "delta_depenses": round(delta_dep, 1),
            "delta_retard": delta_retard,
            "velocite_hebdo": round(delta_av, 1),
            "tendance_retard": "En aggravation" if delta_retard > 0 else ("En résorption" if delta_retard < 0 else "Stable")
        }
