# 🏗️ Copilote IA — Pilotage de Chantier BTP

> **Assistant décisionnel et analytique pour Ingénieur en Bâtiment & Conducteur de Travaux.**  
> *Excel reste la source unique de vérité terrain ; l'IA et Python se chargent de contrôler, calculer, alerter, interpréter et produire les rapports.*

---

## 🌟 Points Forts du Système
1. **Zéro Hallucination sur les Chiffres** : Tous les calculs d'avancement physique pondéré, de consommations, de délais et de finances sont assurés par un moteur déterministe Python.
2. **Architecture Multi-Agents Spécialisée** : 6 rôles d'ingénierie (Data Analyst, Cost Controller, Planning Engineer, Material Controller, Risk Analyst, Report Generator) orchestrés en continu.
3. **Classeur Excel Standardisé en 9 Feuilles** : Un modèle professionnel prêt à l'emploi (`PARAMETRES`, `LOTS`, `PLANNING`, `BUDGET`, `DEPENSES`, `MATERIAUX`, `MAIN_OEUVRE`, `AVANCEMENT`, `ALERTES`).
4. **Moteur d'Alertes Métier (🔴 / 🟠 / 🟢)** : Détection proactive des retards sur chemin critique, des surconsommations d'acier ou de béton, et des ruptures de stock.
5. **Tableau de Bord Web Interactif (Streamlit & Plotly)** : Gantt interactif, S-Curves, répartition budgétaire, pointage des équipes et chat conversationnel avec l'IA.
6. **Livrables Automatisés** : Export en un clic de rapports PDF exécutifs pour la direction et ré-export de classeurs Excel consolidés avec feuilles d'alertes à jour.

---

## 🚀 Démarrage Rapide (Windows)

### Option 1 : Lancement en 1 Clic
Double-cliquez simplement sur le fichier **`run.bat`** à la racine du projet.  
Le script configurera l'environnement virtuel et ouvrira directement l'application dans votre navigateur :
```text
http://localhost:8501
```

### Option 2 : Lancement en Ligne de Commande
```powershell
# 1. Créer l'environnement virtuel et installer les dépendances avec uv
& "C:\Users\LOUIS\.local\bin\uv.exe" venv .venv --python 3.12
& "C:\Users\LOUIS\.local\bin\uv.exe" pip install -r requirements.txt --python .venv

# 2. Lancer l'application web
.venv\Scripts\streamlit.exe run web\app.py
```

---

## 📂 Architecture du Projet

```text
pojet pp/
│
├── data/
│   ├── templates/
│   │   └── Suivi_Chantier_Template.xlsx      # Modèle vierge préformaté (9 feuilles avec formules)
│   ├── samples/
│   │   ├── Suivi_Chantier_S1_2026.xlsx       # Semaine 1 (Démarrage nominal des travaux)
│   │   └── Suivi_Chantier_S4_2026.xlsx       # Semaine 4 (Avancement 68%, Retard 8j, Acier +11%)
│   ├── exports/                              # Rapports PDF et classeurs Excel consolidés générés
│   └── chantier_history.db                   # Base SQLite des snapshots hebdomadaires
│
├── core/
│   ├── models.py                             # Modèles de données (Dataclasses)
│   ├── excel_generator.py                    # Générateur automatisé des fichiers Excel avec styles
│   ├── ingestion.py                          # Ingestion et normalisation des 9 feuilles
│   ├── validation.py                         # Moteur de contrôle qualité (doublons, prix, dates)
│   ├── calculations.py                       # Moteur de calcul déterministe (Avancement, SPI, CPI)
│   ├── alert_engine.py                       # Moteur d'alertes déterministe (🔴/🟠/🟢)
│   └── history_store.py                      # Gestionnaire SQLite des snapshots et tendances
│
├── ai_agents/
│   ├── base_agent.py                         # Classe mère pour les agents
│   ├── data_analyst.py                       # Agent 1 : Contrôle qualité des données
│   ├── cost_controller.py                    # Agent 2 : Budget, dépenses, EAC et écarts financiers
│   ├── planning_engineer.py                  # Agent 3 : Délais, chemin critique et projections
│   ├── material_controller.py                # Agent 4 : Stocks, pertes et surconsommations
│   ├── risk_analyst.py                       # Agent 5 : Matrice des risques et impacts croisés
│   ├── report_generator.py                   # Agent 6 : Synthèses managériales et rapports
│   └── orchestrator.py                       # Chef d'orchestre & Assistant IA conversationnel
│
├── reports/
│   ├── pdf_generator.py                      # Générateur de rapport PDF professionnel (ReportLab)
│   └── excel_exporter.py                     # Ré-exportateur Excel avec feuilles AVANCEMENT & ALERTES
│
├── web/
│   └── app.py                                # Interface Web Streamlit (Dashboard 6 zones + Chat)
│
├── tests/
│   ├── test_ingestion.py                     # Tests unitaires de lecture et validation
│   ├── test_calculations.py                  # Tests unitaires des calculs et alertes
│   └── test_agents.py                        # Tests unitaires multi-agents et exports
│
├── requirements.txt                          # Dépendances Python
└── run.bat                                   # Lanceur Windows en 1 clic
```

---

## 📊 Les 9 Feuilles du Classeur Excel Standard

| Feuille | Description | Exemple de Colonnes |
| :--- | :--- | :--- |
| **`PARAMETRES`** | Métadonnées du projet | Projet, Client, Localisation, Ingénieur, Dates, Budget initial, Devise |
| **`LOTS`** | Liste des lots de travaux | ID_Lot, Lot, Responsable, Budget, Début prévu, Fin prévue |
| **`PLANNING`** | Suivi physique par tâche | ID, Lot, Tâche, Début/Fin prévu(e), Début/Fin réel(le), % prévu, % réel, Statut |
| **`BUDGET`** | Postes de dépenses prévisionnels | ID, Lot, Poste, Quantité prévue, Unité, Prix unitaire, Budget |
| **`DEPENSES`** | Factures et engagements | Date, Lot, Poste, Fournisseur, Référence, Quantité, Montant, Statut |
| **`MATERIAUX`** | Suivi des stocks et consommations | Date, Lot, Matériau, Quantité prévue, reçue, consommée, Stock, Unité |
| **`MAIN_OEUVRE`** | Pointage des équipes sur site | Date, Lot, Équipe, Nombre d'ouvriers, Heures, Coût |
| **`AVANCEMENT`** | *Alimentée automatiquement* | Date, Lot, % prévu, % réalisé, Écart, Tendance (🟢/🟠/🔴) |
| **`ALERTES`** | *Alimentée automatiquement* | Date, Type, Lot, Gravité, Description, Action recommandée |

---

## 🧮 Formules et Indicateurs Clés

1. **Avancement Physique Pondéré** :
   $$\text{Avancement Global} = \frac{\sum (\% \text{Réalisé}_{\text{lot}} \times \text{Budget}_{\text{lot}})}{\text{Budget Total}}$$
2. **Consommation Budgétaire** :
   $$\text{Taux Conso} = \frac{\text{Dépenses Engagées}}{\text{Budget Révisé}} \times 100$$
3. **Surconsommation Matériau** :
   $$\text{Quantité Théorique} = \text{Quantité Prévue} \times \left(\frac{\% \text{Réalisé}_{\text{lot}}}{100}\right)$$
   $$\text{Surconsommation (\%)} = \left(\frac{\text{Quantité Consommée} - \text{Quantité Théorique}}{\text{Quantité Théorique}}\right) \times 100$$
4. **Coût Estimé à l'Achèvement (EAC)** :
   $$\text{CPI} = \frac{\text{Avancement Physique (\%)}}{\text{Consommation Budgétaire (\%)}}$$
   $$\text{EAC} = \frac{\text{Budget Révisé}}{\text{CPI}}$$
