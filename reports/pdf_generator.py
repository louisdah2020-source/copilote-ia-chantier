"""
reports/pdf_generator.py
Générateur de rapport de synthèse de chantier au format PDF professionnel.
Utilise ReportLab pour produire un document exécutif élégant et imprimable.
"""
from pathlib import Path
from xml.sax.saxutils import escape
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from core.models import KPISummary, AlertItem


class PDFReportGenerator:
    """Générateur de rapport exécutif PDF pour ingénieur de chantier BTP."""

    def __init__(self, kpi: KPISummary, alerts: List[AlertItem], diagnosis: Optional[Dict[str, Any]] = None):
        self.kpi = kpi
        self.alerts = alerts
        self.diagnosis = diagnosis or {}

    def generate(self, output_path: str) -> str:
        """Produit le fichier PDF complet."""
        if not hasattr(output_path, "write"):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm
        )

        styles = getSampleStyleSheet()
        
        # Styles personnalisés
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1E3A8A")
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#4B5563")
        )
        h1_style = ParagraphStyle(
            "H1Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1E3A8A"),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "BodyCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1F2937")
        )
        table_text = ParagraphStyle(
            "TableText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11
        )
        table_header = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white
        )

        elements = []

        # En-tête du document
        p_name = escape(self.kpi.parametres.projet)
        p_client = escape(self.kpi.parametres.client)
        p_loc = escape(self.kpi.parametres.localisation)
        p_ing = escape(self.kpi.parametres.ingenieur)
        date_str = self.kpi.date_analyse

        elements.append(Paragraph(f"🏗️ RAPPORT HEBDOMADAIRE DE PILOTAGE DE CHANTIER", title_style))
        elements.append(Paragraph(f"<b>Opération :</b> {p_name} &nbsp;|&nbsp; <b>Client :</b> {p_client} &nbsp;|&nbsp; <b>Lieu :</b> {p_loc}", subtitle_style))
        elements.append(Paragraph(f"<b>Ingénieur Suivi :</b> {p_ing} &nbsp;|&nbsp; <b>Date d'arrêté :</b> {date_str}", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceBefore=8, spaceAfter=12))

        # 1. Cartes des 4 KPI Majeurs
        kpi_table_data = [
            [
                Paragraph("<b>AVANCEMENT PHYSIQUE</b>", table_header),
                Paragraph("<b>BUDGET TOTAL ALLOUÉ</b>", table_header),
                Paragraph("<b>DÉPENSES ENGAGÉES</b>", table_header),
                Paragraph("<b>GLISSEMENT DÉLAI</b>", table_header)
            ],
            [
                Paragraph(f"<font size=14 color='#1E3A8A'><b>{self.kpi.chantier.avancement_physique_global}%</b></font><br/>(Prévu: {self.kpi.chantier.avancement_prevu_global}%)", table_text),
                Paragraph(f"<font size=13 color='#1E3A8A'><b>{self.kpi.finances.budget_revise:,.0f}</b></font><br/>{self.kpi.parametres.devise}", table_text),
                Paragraph(f"<font size=13 color='#D97706'><b>{self.kpi.finances.depenses_engagees:,.0f}</b></font><br/>({self.kpi.finances.pct_consommation_budget}%)", table_text),
                Paragraph(f"<font size=14 color='#DC2626'><b>+{self.kpi.chantier.retard_global_jours} j</b></font><br/>Chemin critique", table_text)
            ]
        ]
        kpi_t = Table(kpi_table_data, colWidths=[4.2 * cm] * 4)
        kpi_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(kpi_t)
        elements.append(Spacer(1, 12))

        # 2. Synthèse Exécutive rédigée par l'IA
        elements.append(Paragraph("1. SYNTHÈSE MANAGÉRIALE DE L'ORCHESTRATEUR IA", h1_style))
        synthese_text = self.diagnosis.get("report_generator", {}).get("synthese_executive", (
            f"Le chantier affiche un avancement physique de {self.kpi.chantier.avancement_physique_global}% "
            f"contre {self.kpi.chantier.avancement_prevu_global}% programmé. Le retard s'établit à {self.kpi.chantier.retard_global_jours} jours "
            f"avec une consommation budgétaire maîtrisée à {self.kpi.finances.pct_consommation_budget}%."
        ))
        elements.append(Paragraph(escape(str(synthese_text)), body_style))
        elements.append(Spacer(1, 10))

        # 3. Tableau de l'Avancement et des Coûts par Lot
        elements.append(Paragraph("2. SITUATION PAR LOT DE TRAVAUX", h1_style))
        lots_table_data = [
            [
                Paragraph("<b>Lot</b>", table_header),
                Paragraph("<b>Budget Alloué</b>", table_header),
                Paragraph("<b>Dépenses Engagées</b>", table_header),
                Paragraph("<b>% Conso</b>", table_header),
                Paragraph("<b>% Prévu</b>", table_header),
                Paragraph("<b>% Réel</b>", table_header),
                Paragraph("<b>Écart</b>", table_header),
                Paragraph("<b>Statut</b>", table_header)
            ]
        ]
        for l in self.kpi.repartition_lots:
            ecart_str = f"{l['ecart_avancement']:+.1f}%"
            statut_badge = "🔴 Retard" if l['ecart_avancement'] < -5 else ("🟠 Suivi" if l['ecart_avancement'] < 0 else "🟢 Conforme")
            lots_table_data.append([
                Paragraph(escape(str(l["lot"])), table_text),
                Paragraph(f"{l['budget']:,.0f}", table_text),
                Paragraph(f"{l['depenses']:,.0f}", table_text),
                Paragraph(f"{l['pct_conso']}%", table_text),
                Paragraph(f"{l['pct_prevu']}%", table_text),
                Paragraph(f"{l['pct_reel']}%", table_text),
                Paragraph(ecart_str, table_text),
                Paragraph(statut_badge, table_text)
            ])
        lots_t = Table(lots_table_data, colWidths=[3.2*cm, 2.3*cm, 2.3*cm, 1.6*cm, 1.6*cm, 1.6*cm, 1.7*cm, 2.2*cm])
        lots_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3B82F6")),
            ('ALIGN', (1, 1), (-2, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(lots_t)
        elements.append(Spacer(1, 10))

        # 4. Matériaux & Alertes
        elements.append(Paragraph("3. SURVEILLANCE MATÉRIAUX & RATIOS DE CONSOMMATION", h1_style))
        mat_table_data = [
            [
                Paragraph("<b>Matériau</b>", table_header),
                Paragraph("<b>Lot</b>", table_header),
                Paragraph("<b>Prévu</b>", table_header),
                Paragraph("<b>Consommé</b>", table_header),
                Paragraph("<b>Stock</b>", table_header),
                Paragraph("<b>Surconsommation</b>", table_header)
            ]
        ]
        for m in self.kpi.materiaux_alertes[:6]:
            sc_badge = f"<font color='red'><b>+{m['surconsommation_pct']}%</b></font>" if m["surconsommation_pct"] > 5 else f"{m['surconsommation_pct']}%"
            mat_table_data.append([
                Paragraph(escape(str(m["materiau"])), table_text),
                Paragraph(escape(str(m["lot"])), table_text),
                Paragraph(f"{m['quantite_prevue']:,.0f} {escape(str(m['unite']))}", table_text),
                Paragraph(f"{m['quantite_consommee']:,.0f} {escape(str(m['unite']))}", table_text),
                Paragraph(f"{m['stock']:,.0f} {escape(str(m['unite']))}", table_text),
                Paragraph(sc_badge, table_text)
            ])
        mat_t = Table(mat_table_data, colWidths=[3.5*cm, 3.2*cm, 2.8*cm, 2.8*cm, 2.2*cm, 2.8*cm])
        mat_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#475569")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(mat_t)
        elements.append(Spacer(1, 10))

        # 5. Alertes Métiers & Actions Recommandées
        elements.append(Paragraph("4. RADAR DES ALERTES & ACTIONS PRIORITAIRES", h1_style))
        alert_data = [
            [
                Paragraph("<b>Gravité</b>", table_header),
                Paragraph("<b>Type / Lot</b>", table_header),
                Paragraph("<b>Constat / Description</b>", table_header),
                Paragraph("<b>Action Recommandée</b>", table_header)
            ]
        ]
        for a in self.alerts[:8]:
            alert_data.append([
                Paragraph(escape(a.gravite), table_text),
                Paragraph(f"<b>{escape(a.type_alerte)}</b><br/>{escape(a.lot)}", table_text),
                Paragraph(escape(a.description), table_text),
                Paragraph(f"<i>{escape(a.action_recommandee)}</i>", table_text)
            ])
        alt_t = Table(alert_data, colWidths=[2.2*cm, 3.0*cm, 6.0*cm, 5.8*cm])
        alt_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#DC2626")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF7ED")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(alt_t)
        elements.append(Spacer(1, 15))

        # Signatures
        sig_data = [
            [
                Paragraph(f"<b>L'Ingénieur de Contrôle</b><br/><br/>{p_ing}", body_style),
                Paragraph("<b>Le Conducteur de Travaux</b><br/><br/>Pour l'Entreprise Générale", body_style),
                Paragraph(f"<b>Le Maître d'Ouvrage</b><br/><br/>{p_client}", body_style)
            ]
        ]
        sig_t = Table(sig_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
        sig_t.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
            ('TOPPADDING', (0, 0), (-1, -1), 8)
        ]))
        elements.append(sig_t)

        doc.build(elements)
        return output_path
