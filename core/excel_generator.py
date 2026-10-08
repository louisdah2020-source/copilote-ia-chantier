"""
core/excel_generator.py
Générateur de classeurs Excel standardisés pour le pilotage de chantier.
Permet de créer le gabarit vierge (Template) et les jeux de données de test (S1 et S4).
"""
import os
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Bleu Nuit BTP
SUBHEADER_FILL = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid") # Bleu Royal
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
REGULAR_FONT = Font(name="Calibri", size=11)
BOLD_FONT = Font(name="Calibri", size=11, bold=True)
ITALIC_FONT = Font(name="Calibri", size=10, italic=True, color="555555")

THIN_BORDER = Border(
    left=Side(style="thin", color="D1D5DB"),
    right=Side(style="thin", color="D1D5DB"),
    top=Side(style="thin", color="D1D5DB"),
    bottom=Side(style="thin", color="D1D5DB")
)


def _apply_table_styling(ws, header_row=1):
    """Applique un style professionnel aux en-têtes et bordures d'une feuille."""
    ws.views.sheetView[0].showGridLines = True
    
    # Styliser les en-têtes
    for col_idx in range(1, ws.max_column + 1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    ws.row_dimensions[header_row].height = 26
    
    # Styliser les données et ajuster la largeur des colonnes
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row > header_row and cell.value is not None:
                cell.font = REGULAR_FONT
                cell.border = THIN_BORDER
                val_str = str(cell.value)
                max_len = max(max_len, len(val_str))
            elif cell.row == header_row and cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 13)


def create_template_workbook(output_path: str):
    """Crée le classeur modèle vierge avec les 9 feuilles."""
    wb = openpyxl.Workbook()
    # Supprimer la feuille par défaut
    wb.remove(wb.active)
    
    # 1. PARAMETRES
    ws_param = wb.create_sheet(title="PARAMETRES")
    ws_param.append(["Champ", "Valeur", "Description"])
    params_data = [
        ["Projet", "Immeuble R+4", "Nom de l'opération de construction"],
        ["Client", "Société XYZ", "Maître d'ouvrage"],
        ["Localisation", "Abidjan, Cocody", "Site des travaux"],
        ["Ingénieur", "Ing. Koffi", "Responsable de suivi de chantier"],
        ["Date début", "2026-10-01", "Date contractuelle de démarrage (YYYY-MM-DD)"],
        ["Date fin prévue", "2027-06-30", "Date contractuelle de livraison (YYYY-MM-DD)"],
        ["Budget initial", 350000000, "Budget global alloué au projet"],
        ["Budget révisé", 350000000, "Budget après avenants validés"],
        ["Devise", "FCFA", "Unité monétaire"]
    ]
    for row in params_data:
        ws_param.append(row)
    _apply_table_styling(ws_param)
    
    # 2. LOTS
    ws_lots = wb.create_sheet(title="LOTS")
    ws_lots.append(["ID_Lot", "Lot", "Responsable", "Budget", "Début prévu", "Fin prévue"])
    lots_data = [
        ["LOT01", "Terrassement", "Chef Amadou", 15000000, "2026-10-01", "2026-10-20"],
        ["LOT02", "Fondations", "Chef Bakayoko", 45000000, "2026-10-15", "2026-11-20"],
        ["LOT03", "Gros œuvre", "Chef Cissé", 120000000, "2026-11-20", "2027-02-15"],
        ["LOT04", "Électricité & Courants faibles", "Chef Diabaté", 35000000, "2027-02-01", "2027-04-15"],
        ["LOT05", "Plomberie & Climatisation", "Chef Émile", 25000000, "2027-02-10", "2027-04-20"],
        ["LOT06", "Étanchéité & Couverture", "Chef Fofana", 20000000, "2027-02-15", "2027-03-30"],
        ["LOT07", "Second œuvre & Finitions", "Chef Gnahoré", 70000000, "2027-03-15", "2027-06-15"],
        ["LOT08", "VRD & Espaces extérieurs", "Chef Hien", 20000000, "2027-05-01", "2027-06-30"]
    ]
    for row in lots_data:
        ws_lots.append(row)
    _apply_table_styling(ws_lots)
    
    # 3. PLANNING
    ws_planning = wb.create_sheet(title="PLANNING")
    ws_planning.append(["ID", "Lot", "Tâche", "Début prévu", "Fin prévue", "Début réel", "Fin réelle", "% prévu", "% réel", "Statut"])
    _apply_table_styling(ws_planning)
    
    # 4. BUDGET
    ws_budget = wb.create_sheet(title="BUDGET")
    ws_budget.append(["ID", "Lot", "Poste", "Quantité prévue", "Unité", "Prix unitaire", "Budget"])
    _apply_table_styling(ws_budget)
    
    # 5. DEPENSES
    ws_depenses = wb.create_sheet(title="DEPENSES")
    ws_depenses.append(["Date", "Lot", "Poste", "Fournisseur", "Référence", "Quantité", "Montant", "Statut"])
    _apply_table_styling(ws_depenses)
    
    # 6. MATERIAUX
    ws_materiaux = wb.create_sheet(title="MATERIAUX")
    ws_materiaux.append(["Date", "Lot", "Matériau", "Quantité prévue", "Quantité reçue", "Quantité consommée", "Stock", "Unité"])
    _apply_table_styling(ws_materiaux)
    
    # 7. MAIN_OEUVRE
    ws_mo = wb.create_sheet(title="MAIN_OEUVRE")
    ws_mo.append(["Date", "Lot", "Équipe", "Nombre ouvriers", "Heures", "Coût", "Tâche associée"])
    _apply_table_styling(ws_mo)
    
    # 8. AVANCEMENT
    ws_av = wb.create_sheet(title="AVANCEMENT")
    ws_av.append(["Date", "Lot", "% prévu", "% réalisé", "Écart", "Tendance"])
    _apply_table_styling(ws_av)
    
    # 9. ALERTES
    ws_alt = wb.create_sheet(title="ALERTES")
    ws_alt.append(["Date", "Type", "Lot", "Gravité", "Description", "Action recommandée"])
    _apply_table_styling(ws_alt)
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


def create_sample_s4_workbook(output_path: str):
    """
    Crée le classeur de test réaliste correspondant exactement au scénario du prompt :
    - Date d'analyse : 08/10/2026 (ou semaine 4 d'avancement gros oeuvre)
    - Budget initial : 350 M FCFA
    - Avancement global : 68% vs 72% prévu (écart -4% global, gros oeuvre retard de 8 jours)
    - Dépenses engagées / réalisées : ~225 M FCFA
    - Acier : surconsommation +11%
    - Fondations : retard 6 jours
    - Alertes critiques : 3
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    
    # 1. PARAMETRES
    ws_param = wb.create_sheet(title="PARAMETRES")
    ws_param.append(["Champ", "Valeur", "Description"])
    for row in [
        ["Projet", "Immeuble R+4", "Résidence Les Jardins du Plateau"],
        ["Client", "Société XYZ", "Maître d'Ouvrage Délégué"],
        ["Localisation", "Abidjan, Cocody", "Parcelle B12 - Lotissement Panorama"],
        ["Ingénieur", "Ing. Koffi Marc", "Chef de Projet Suivi & Contrôle"],
        ["Date début", "2026-10-01", "Démarrage des terrassements"],
        ["Date fin prévue", "2027-06-30", "Livraison des clés"],
        ["Budget initial", 350000000, "Montant du marché HT"],
        ["Budget révisé", 350000000, "Budget contractuel en vigueur"],
        ["Devise", "FCFA", "Francs CFA BCEAO"]
    ]:
        ws_param.append(row)
    _apply_table_styling(ws_param)
    
    # 2. LOTS
    ws_lots = wb.create_sheet(title="LOTS")
    ws_lots.append(["ID_Lot", "Lot", "Responsable", "Budget", "Début prévu", "Fin prévue"])
    for row in [
        ["LOT01", "Terrassement", "Chef Amadou", 15000000, "2026-10-01", "2026-10-20"],
        ["LOT02", "Fondations", "Chef Bakayoko", 45000000, "2026-10-15", "2026-11-20"],
        ["LOT03", "Gros œuvre", "Chef Cissé", 120000000, "2026-11-20", "2027-02-15"],
        ["LOT04", "Électricité", "Chef Diabaté", 35000000, "2027-02-01", "2027-04-15"],
        ["LOT05", "Plomberie", "Chef Émile", 25000000, "2027-02-10", "2027-04-20"],
        ["LOT06", "Étanchéité", "Chef Fofana", 20000000, "2027-02-15", "2027-03-30"],
        ["LOT07", "Finitions", "Chef Gnahoré", 70000000, "2027-03-15", "2027-06-15"],
        ["LOT08", "VRD & Extérieurs", "Chef Hien", 20000000, "2027-05-01", "2027-06-30"]
    ]:
        ws_lots.append(row)
    _apply_table_styling(ws_lots)
    
    # 3. PLANNING
    ws_planning = wb.create_sheet(title="PLANNING")
    ws_planning.append(["ID", "Lot", "Tâche", "Début prévu", "Fin prévue", "Début réel", "Fin réelle", "% prévu", "% réel", "Statut"])
    planning_rows = [
        ["T001", "Terrassement", "Fouilles et terrassements généraux", "2026-10-01", "2026-10-20", "2026-10-01", "2026-10-19", 100, 100, "Terminé"],
        ["T002", "Fondations", "Semelles et longrines béton armé", "2026-10-15", "2026-11-20", "2026-10-15", "2026-11-26", 100, 100, "Terminé"],
        ["T003", "Gros œuvre", "Poteaux et voiles RDC", "2026-11-20", "2026-12-10", "2026-11-20", "2026-12-09", 100, 100, "Terminé"],
        ["T004", "Gros œuvre", "Plancher haut RDC et R+1", "2026-12-10", "2027-01-05", "2026-12-12", "2027-01-04", 100, 100, "Terminé"],
        ["T005", "Gros œuvre", "Poteaux et poutres R+2 et R+3", "2027-01-05", "2027-01-25", "2027-01-06", "2027-01-24", 100, 100, "Terminé"],
        ["T006", "Gros œuvre", "Plancher haut R+4 et acrotères", "2027-01-20", "2027-02-15", "2027-01-26", "", 96, 88, "En retard"],
        ["T007", "Électricité", "Incorporation gaines et filerie RDC à R+2", "2027-02-01", "2027-03-15", "2027-02-03", "", 75, 65, "En retard"],
        ["T008", "Plomberie", "Colonnes montantes et évacuations", "2027-02-10", "2027-03-20", "2027-02-10", "", 60, 50, "En cours"],
        ["T009", "Étanchéité", "Forme de pente et étanchéité terrasse", "2027-02-15", "2027-03-30", "2027-02-15", "", 65, 60, "En cours"],
        ["T010", "Finitions", "Enduits intérieurs, cloisons et chapes", "2027-03-15", "2027-05-15", "2027-03-18", "", 33, 35, "En cours"],
        ["T011", "VRD & Extérieurs", "Raccordements réseaux et voirie", "2027-05-01", "2027-06-30", "", "", 0, 0, "Non démarré"]
    ]
    for row in planning_rows:
        ws_planning.append(row)
    _apply_table_styling(ws_planning)

    # 4. BUDGET
    ws_budget = wb.create_sheet(title="BUDGET")
    ws_budget.append(["ID", "Lot", "Poste", "Quantité prévue", "Unité", "Prix unitaire", "Budget"])
    budget_rows = [
        ["B001", "Terrassement", "Décapage et terrassement en masse", 2500, "m³", 6000, 15000000],
        ["B002", "Fondations", "Béton armé fondations B25", 400, "m³", 75000, 30000000],
        ["B003", "Fondations", "Aciers pour armatures semelles", 18, "tonnes", 833333, 15000000],
        ["B004", "Gros œuvre", "Béton prêt à l'emploi structure B25", 800, "m³", 75000, 60000000],
        ["B005", "Gros œuvre", "Acier haute adhérence structure", 70, "tonnes", 850000, 59500000],
        ["B006", "Gros œuvre", "Coffrage métallique et bois", 1500, "m²", 333, 500000],
        ["B007", "Électricité", "Câblage, tableaux divisionnaires et appareillage", 1, "forfait", 35000000, 35000000],
        ["B008", "Plomberie", "Réseau alimentation cuivre & sanitaires", 1, "forfait", 25000000, 25000000],
        ["B009", "Étanchéité", "Complexe bitumineux bicouche auto-protégé", 450, "m²", 44444, 20000000],
        ["B010", "Finitions", "Revêtements sols, faïences et peintures", 1, "forfait", 70000000, 70000000],
        ["B011", "VRD & Extérieurs", "Canalisations, voirie pavée et clôtures", 1, "forfait", 20000000, 20000000]
    ]
    for row in budget_rows:
        ws_budget.append(row)
    _apply_table_styling(ws_budget)

    # 5. DEPENSES (Total = 225 000 000 FCFA = 64.3% de 350M)
    ws_depenses = wb.create_sheet(title="DEPENSES")
    ws_depenses.append(["Date", "Lot", "Poste", "Fournisseur", "Référence", "Quantité", "Montant", "Statut"])
    depenses_rows = [
        ["2026-10-05", "Terrassement", "Engins de terrassement", "SOTRAB CI", "FAC-0012", 1, 7800000, "Payé"],
        ["2026-10-18", "Terrassement", "Évacuation déblais et remblais", "SOTRAB CI", "FAC-0019", 1, 7200000, "Payé"],
        ["2026-10-22", "Fondations", "Ciment CPA 42.5", "CIMAF", "FAC-0104", 1200, 11000000, "Payé"],
        ["2026-10-28", "Fondations", "Gravier et sable lagune", "CARRIÈRE DIBY", "FAC-0145", 350, 5200000, "Payé"],
        ["2026-11-04", "Fondations", "Acier HA 10/12/16", "AFRIC-ACIER", "FAC-0210", 18, 15500000, "Payé"],
        ["2026-11-12", "Fondations", "Main d'œuvre coulage et coffrage", "ST-Fondations", "FAC-0255", 1, 13300000, "Payé"],
        ["2026-11-25", "Gros œuvre", "Béton prêt à l'emploi centrale", "IVOGRAN Béton", "FAC-0310", 250, 18750000, "Payé"],
        ["2026-12-05", "Gros œuvre", "Béton prêt à l'emploi centrale", "IVOGRAN Béton", "FAC-0388", 220, 16500000, "Payé"],
        ["2026-12-14", "Gros œuvre", "Acier HA structure - Lot 1", "AFRIC-ACIER", "FAC-0412", 35, 31000000, "Payé"],
        ["2027-01-08", "Gros œuvre", "Acier HA structure - Lot 2 (surcoût +11%)", "AFRIC-ACIER", "FAC-0501", 38, 38750000, "Payé"],
        ["2027-01-18", "Gros œuvre", "Béton planchers R+3/R+4", "IVOGRAN Béton", "FAC-0560", 200, 15000000, "Engagé"],
        ["2027-01-26", "Gros œuvre", "Location banches et étais", "LOCAMAT", "FAC-0599", 1, 9000000, "Payé"],
        ["2027-02-02", "Électricité", "Gaines ICTA et câbles cuivre", "ELECPHOENIX", "FAC-0640", 1, 14000000, "Payé"],
        ["2027-02-05", "Plomberie", "Tuyauterie PPR & évacuation PVC", "IVOIRE-PLOMB", "FAC-0675", 1, 9000000, "Engagé"],
        ["2027-02-08", "Étanchéité", "Rouleaux bitume SBS et primaire", "SOPREMA CI", "FAC-0711", 1, 7000000, "Engagé"],
        ["2027-02-08", "Finitions", "Acompte carrelages et enduits", "COBAT CI", "FAC-0801", 1, 6000000, "Engagé"]
    ]
    for row in depenses_rows:
        ws_depenses.append(row)
    _apply_table_styling(ws_depenses)

    # 6. MATERIAUX
    ws_materiaux = wb.create_sheet(title="MATERIAUX")
    ws_materiaux.append(["Date", "Lot", "Matériau", "Quantité prévue", "Quantité reçue", "Quantité consommée", "Stock", "Unité"])
    materiaux_rows = [
        ["2027-02-08", "Gros œuvre", "Ciment CPA 42.5", 8500, 5000, 4200, 800, "sacs"],
        ["2027-02-08", "Gros œuvre", "Acier haute adhérence", 70, 75, 68.4, 6.6, "tonnes"], # 68.4t pour 88% avancement = +11% surconso
        ["2027-02-08", "Gros œuvre", "Sable de lagune lavé", 600, 420, 390, 30, "m³"],
        ["2027-02-08", "Gros œuvre", "Gravier concassé 15/25", 950, 700, 640, 60, "m³"],
        ["2027-02-08", "Fondations", "Acier semelles", 18, 18, 18, 0, "tonnes"],
        ["2027-02-08", "Électricité", "Câbles R2V 3G2.5", 4500, 2500, 1800, 700, "mètres"],
        ["2027-02-08", "Plomberie", "Tubes PVC évacuation Ø100", 350, 200, 140, 60, "barres"]
    ]
    for row in materiaux_rows:
        ws_materiaux.append(row)
    _apply_table_styling(ws_materiaux)

    # 7. MAIN_OEUVRE
    ws_mo = wb.create_sheet(title="MAIN_OEUVRE")
    ws_mo.append(["Date", "Lot", "Équipe", "Nombre ouvriers", "Heures", "Coût", "Tâche associée"])
    mo_rows = [
        ["2027-02-02", "Gros œuvre", "Équipe Ferraillage Cissé", 12, 96, 360000, "Poteaux R+4"],
        ["2027-02-03", "Gros œuvre", "Équipe Coffrage Bakary", 15, 120, 450000, "Plancher R+4"],
        ["2027-02-04", "Gros œuvre", "Équipe Coulage Béton", 18, 144, 540000, "Dalle R+4"],
        ["2027-02-05", "Électricité", "Équipe Câblage Diabaté", 6, 48, 220000, "Incorporation gaines"],
        ["2027-02-06", "Plomberie", "Équipe Tuyauterie Émile", 5, 40, 185000, "Colonnes montantes"],
        ["2027-02-07", "Gros œuvre", "Équipe Ferraillage Cissé", 12, 96, 360000, "Acrotères"],
        ["2027-02-08", "Gros œuvre", "Équipe Maçonnerie & Finition", 14, 112, 420000, "Voiles périphériques"]
    ]
    for row in mo_rows:
        ws_mo.append(row)
    _apply_table_styling(ws_mo)

    # 8. AVANCEMENT (Moyenne pondérée = 68% réalisé vs 72% prévu)
    ws_av = wb.create_sheet(title="AVANCEMENT")
    ws_av.append(["Date", "Lot", "% prévu", "% réalisé", "Écart", "Tendance"])
    av_rows = [
        ["2027-02-08", "Terrassement", 1.00, 1.00, 0.00, "🟢"],
        ["2027-02-08", "Fondations", 1.00, 1.00, 0.00, "🟢"],
        ["2027-02-08", "Gros œuvre", 0.96, 0.88, -0.08, "🔴"],
        ["2027-02-08", "Électricité", 0.75, 0.65, -0.10, "🟠"],
        ["2027-02-08", "Plomberie", 0.60, 0.50, -0.10, "🟠"],
        ["2027-02-08", "Étanchéité", 0.65, 0.60, -0.05, "🟠"],
        ["2027-02-08", "Finitions", 0.33, 0.35, +0.02, "🟢"],
        ["2027-02-08", "VRD & Extérieurs", 0.00, 0.00, 0.00, "🟢"]
    ]
    for row in av_rows:
        ws_av.append(row)
    _apply_table_styling(ws_av)
    
    # 9. ALERTES
    ws_alt = wb.create_sheet(title="ALERTES")
    ws_alt.append(["Date", "Type", "Lot", "Gravité", "Description", "Action recommandée"])
    alert_rows = [
        ["2027-02-08", "Budget", "Gros œuvre", "🔴 Haute", "Dépassement prévisionnel budget gros œuvre (+8.2%) dû aux aciers", "Audit immédiat du ferraillage et contrôle des chutes"],
        ["2027-02-08", "Planning", "Gros œuvre", "🔴 Haute", "Retard critique de 8 jours sur plancher R+2 impactant le chemin critique", "Renforcer équipe coffrage et autoriser heures supplémentaires samedi"],
        ["2027-02-08", "Matériau", "Gros œuvre", "🔴 Haute", "Surconsommation d'acier de +11% par rapport au ratio théorique m3/kg", "Vérifier conformité des longueurs de recouvrement et réceptions"],
        ["2027-02-08", "Planning", "Fondations", "🟠 Moyenne", "Retard résiduel de 6 jours sur réceptions de fin de lot", "Clôturer le PV de réception avec le bureau de contrôle SOCOTEC"],
        ["2027-02-08", "Matériau", "Fondations", "🟠 Moyenne", "Stock acier semelles épuisé (0 tonne restante)", "Valider que le lot est définitivement coulé ou réapprovisionner"],
        ["2027-02-08", "Budget", "Électricité", "🟠 Moyenne", "Factures engagées à 41% pour un avancement physique de 25%", "Exiger les attachements contradictoires avant paiement"]
    ]
    for row in alert_rows:
        ws_alt.append(row)
    _apply_table_styling(ws_alt)
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


def create_sample_s1_workbook(output_path: str):
    """Crée le classeur de la Semaine 1 pour comparaison historique."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    
    # PARAMETRES
    ws_param = wb.create_sheet(title="PARAMETRES")
    ws_param.append(["Champ", "Valeur", "Description"])
    for row in [
        ["Projet", "Immeuble R+4", "Résidence Les Jardins du Plateau"],
        ["Client", "Société XYZ", "Maître d'Ouvrage Délégué"],
        ["Localisation", "Abidjan, Cocody", "Parcelle B12 - Panorama"],
        ["Ingénieur", "Ing. Koffi Marc", "Chef de Projet"],
        ["Date début", "2026-10-01", "Démarrage des travaux"],
        ["Date fin prévue", "2027-06-30", "Livraison prévue"],
        ["Budget initial", 350000000, "Budget global HT"],
        ["Budget révisé", 350000000, "Budget révisé"],
        ["Devise", "FCFA", "Francs CFA"]
    ]:
        ws_param.append(row)
    _apply_table_styling(ws_param)
    
    # LOTS
    ws_lots = wb.create_sheet(title="LOTS")
    ws_lots.append(["ID_Lot", "Lot", "Responsable", "Budget", "Début prévu", "Fin prévue"])
    for row in [
        ["LOT01", "Terrassement", "Chef Amadou", 15000000, "2026-10-01", "2026-10-20"],
        ["LOT02", "Fondations", "Chef Bakayoko", 45000000, "2026-10-15", "2026-11-20"],
        ["LOT03", "Gros œuvre", "Chef Cissé", 120000000, "2026-11-20", "2027-02-15"],
        ["LOT04", "Électricité", "Chef Diabaté", 35000000, "2027-02-01", "2027-04-15"],
        ["LOT05", "Plomberie", "Chef Émile", 25000000, "2027-02-10", "2027-04-20"],
        ["LOT06", "Étanchéité", "Chef Fofana", 20000000, "2027-02-15", "2027-03-30"],
        ["LOT07", "Finitions", "Chef Gnahoré", 70000000, "2027-03-15", "2027-06-15"],
        ["LOT08", "VRD & Extérieurs", "Chef Hien", 20000000, "2027-05-01", "2027-06-30"]
    ]:
        ws_lots.append(row)
    _apply_table_styling(ws_lots)
    
    # PLANNING S1 (terrassement démarré conformément)
    ws_planning = wb.create_sheet(title="PLANNING")
    ws_planning.append(["ID", "Lot", "Tâche", "Début prévu", "Fin prévue", "Début réel", "Fin réelle", "% prévu", "% réel", "Statut"])
    planning_s1 = [
        ["T001", "Terrassement", "Fouilles générales en pleine masse", "2026-10-01", "2026-10-10", "2026-10-01", "", 70, 75, "En cours"],
        ["T002", "Terrassement", "Nivellement et compactage fond de fouille", "2026-10-10", "2026-10-20", "", "", 0, 0, "Non démarré"],
        ["T003", "Fondations", "Béton de propreté et traçage", "2026-10-15", "2026-10-22", "", "", 0, 0, "Non démarré"]
    ]
    for row in planning_s1:
        ws_planning.append(row)
    _apply_table_styling(ws_planning)
    
    # BUDGET S1
    ws_budget = wb.create_sheet(title="BUDGET")
    ws_budget.append(["ID", "Lot", "Poste", "Quantité prévue", "Unité", "Prix unitaire", "Budget"])
    for row in [
        ["B001", "Terrassement", "Décapage et terrassement en masse", 2500, "m³", 6000, 15000000],
        ["B002", "Fondations", "Béton armé fondations B25", 400, "m³", 75000, 30000000],
        ["B003", "Gros œuvre", "Béton B25 structure", 800, "m³", 75000, 60000000]
    ]:
        ws_budget.append(row)
    _apply_table_styling(ws_budget)
    
    # DEPENSES S1
    ws_depenses = wb.create_sheet(title="DEPENSES")
    ws_depenses.append(["Date", "Lot", "Poste", "Fournisseur", "Référence", "Quantité", "Montant", "Statut"])
    for row in [
        ["2026-10-05", "Terrassement", "Engins de terrassement", "SOTRAB CI", "FAC-0012", 1, 7500000, "Payé"]
    ]:
        ws_depenses.append(row)
    _apply_table_styling(ws_depenses)
    
    # MATERIAUX S1
    ws_materiaux = wb.create_sheet(title="MATERIAUX")
    ws_materiaux.append(["Date", "Lot", "Matériau", "Quantité prévue", "Quantité reçue", "Quantité consommée", "Stock", "Unité"])
    for row in [
        ["2026-10-08", "Terrassement", "Gasoil engins", 5000, 3000, 1800, 1200, "litres"]
    ]:
        ws_materiaux.append(row)
    _apply_table_styling(ws_materiaux)
    
    # MAIN_OEUVRE S1
    ws_mo = wb.create_sheet(title="MAIN_OEUVRE")
    ws_mo.append(["Date", "Lot", "Équipe", "Nombre ouvriers", "Heures", "Coût", "Tâche associée"])
    for row in [
        ["2026-10-05", "Terrassement", "Équipe Conduite Engins", 4, 32, 120000, "Fouilles générales"]
    ]:
        ws_mo.append(row)
    _apply_table_styling(ws_mo)
    
    # AVANCEMENT S1
    ws_av = wb.create_sheet(title="AVANCEMENT")
    ws_av.append(["Date", "Lot", "% prévu", "% réalisé", "Écart", "Tendance"])
    for row in [
        ["2026-10-08", "Terrassement", 0.05, 0.06, 0.01, "🟢"]
    ]:
        ws_av.append(row)
    _apply_table_styling(ws_av)
    
    # ALERTES S1
    ws_alt = wb.create_sheet(title="ALERTES")
    ws_alt.append(["Date", "Type", "Lot", "Gravité", "Description", "Action recommandée"])
    for row in [
        ["2026-10-08", "Planning", "Terrassement", "🟢 Faible", "Avancement conforme au planning initial (+1%)", "Poursuivre le rythme actuel"]
    ]:
        ws_alt.append(row)
    _apply_table_styling(ws_alt)
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    t_path = base_dir / "data" / "templates" / "Suivi_Chantier_Template.xlsx"
    s1_path = base_dir / "data" / "samples" / "Suivi_Chantier_S1_2026.xlsx"
    s4_path = base_dir / "data" / "samples" / "Suivi_Chantier_S4_2026.xlsx"
    
    print(f"Génération Template -> {create_template_workbook(str(t_path))}")
    print(f"Génération S1 -> {create_sample_s1_workbook(str(s1_path))}")
    print(f"Génération S4 -> {create_sample_s4_workbook(str(s4_path))}")
