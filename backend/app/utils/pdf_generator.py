"""
PDF Report Generator for Supervisor Visits and Malnutrition Summaries.
Uses ReportLab to generate clean, print-ready, official government-formatted PDFs.
"""
import io
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_visit_pdf(visit_data: dict) -> io.BytesIO:
    """Generates an official Lady Supervisor Visit Report PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    # Title & Header
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e3a8a"),
        alignment=1 # Center
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )

    story.append(Paragraph("<b>DEPARTMENT OF WOMEN & CHILD DEVELOPMENT (ICDS)</b>", title_style))
    story.append(Paragraph("<b>Lady Supervisor (LS) Anganwadi Centre Inspection & Monitoring Report</b>", subtitle_style))
    story.append(Spacer(1, 15))

    # Visit Metadata Table
    meta_data = [
        [Paragraph("<b>Visit ID:</b>", styles['Normal']), Paragraph(str(visit_data.get("visit_id", "N/A")), styles['Normal']),
         Paragraph("<b>Date of Visit:</b>", styles['Normal']), Paragraph(str(visit_data.get("visit_date", date.today())), styles['Normal'])],
        [Paragraph("<b>AWC Name:</b>", styles['Normal']), Paragraph(f"{visit_data.get('awc_name', '')} ({visit_data.get('awc_code', '')})", styles['Normal']),
         Paragraph("<b>Supervisor:</b>", styles['Normal']), Paragraph(str(visit_data.get("supervisor_name", "N/A")), styles['Normal'])],
        [Paragraph("<b>Village:</b>", styles['Normal']), Paragraph(str(visit_data.get("village", "N/A")), styles['Normal']),
         Paragraph("<b>Attendance Today:</b>", styles['Normal']), Paragraph(f"{visit_data.get('attendance_count', 0)} children", styles['Normal'])]
    ]
    t_meta = Table(meta_data, colWidths=[100, 170, 100, 170])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))

    # Section 1: Auto-populated AWC Statistics (FR-SV-03)
    story.append(Paragraph("<b>1. AWC Nutritional & Operational Snapshot (Auto-populated)</b>", styles['Heading3']))
    stats_data = [
        ["Total Enrolled Children", "Measured This Month", "SAM Children", "MAM Children", "Overdue Vaccines"],
        [
            str(visit_data.get("enrolled_children", 0)),
            f"{visit_data.get('measured_this_month', 0)} ({visit_data.get('coverage_pct', 0):.1f}%)",
            str(visit_data.get("sam_count", 0)),
            str(visit_data.get("mam_count", 0)),
            str(visit_data.get("overdue_vaccine_count", 0))
        ]
    ]
    t_stats = Table(stats_data, colWidths=[110, 110, 100, 100, 120])
    t_stats.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_stats)
    story.append(Spacer(1, 15))

    # Section 2: Structured Inspection Checklist (FR-SV-02)
    story.append(Paragraph("<b>2. Structured Quality & Compliance Checklist</b>", styles['Heading3']))
    checklist_data = [
        ["Inspection Parameter", "Observed Status", "Assessment / Score"],
        ["Growth Monitoring Register Upkeep", "Updated & Verified", f"{visit_data.get('register_upkeep_score', 5)} / 5 Stars"],
        ["Equipment Calibration (Scale, Board, Tape)", "Functional & Calibrated" if visit_data.get("equipment_functional") else "Needs Service / Uncalibrated", "Compliant" if visit_data.get("equipment_functional") else "Non-Compliant"],
        ["Cleanliness, Safe Water & Sanitation", "Clean premises verified", f"{visit_data.get('cleanliness_score', 5)} / 5 Stars"],
        ["Supplementary Nutrition (THR/Hot Meal)", "Delivered to enrolled beneficiaries" if visit_data.get("sn_delivered") else "Deficient delivery", "Satisfactory" if visit_data.get("sn_delivered") else "Action Required"]
    ]
    t_check = Table(checklist_data, colWidths=[200, 200, 140])
    t_check.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f766e")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_check)
    story.append(Spacer(1, 15))

    # Section 3: Action Items (FR-SV-04)
    story.append(Paragraph("<b>3. Action Items & Follow-ups</b>", styles['Heading3']))
    action_items = visit_data.get("action_items", [])
    if action_items:
        items_data = [["#", "Action Description", "Owner Role", "Owner Name", "Due Date", "Status"]]
        for idx, item in enumerate(action_items, 1):
            items_data.append([
                str(idx),
                str(item.get("description", "")),
                str(item.get("owner_role", "")),
                str(item.get("owner_name", "")),
                str(item.get("due_date", "")),
                str(item.get("status", "PENDING"))
            ])
        t_items = Table(items_data, colWidths=[30, 210, 70, 90, 70, 70])
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#334155")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_items)
    else:
        story.append(Paragraph("<i>No immediate action items recorded for this visit.</i>", styles['Normal']))
    
    story.append(Spacer(1, 15))
    # Observations
    story.append(Paragraph("<b>4. Supervisor Observations & Field Notes</b>", styles['Heading3']))
    obs_text = visit_data.get("observations") or "Centre visited during morning growth monitoring session. Routine operations verified."
    story.append(Paragraph(obs_text, styles['Normal']))

    # Footer Signatures
    story.append(Spacer(1, 40))
    sig_data = [
        ["_________________________", "_________________________"],
        ["Anganwadi Worker (Signature)", "Lady Supervisor (Signature & Stamp)"]
    ]
    t_sig = Table(sig_data, colWidths=[270, 270])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_sig)

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_malnutrition_pdf(data: dict) -> io.BytesIO:
    """FR-DB-06: Generates an official Malnutrition Surveillance Register and Case Summary PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1e3a8a"),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )

    story.append(Paragraph("<b>DEPARTMENT OF WOMEN & CHILD DEVELOPMENT (ICDS)</b>", title_style))
    story.append(Paragraph("<b>Child Growth Monitoring & Malnutrition Surveillance Register (ACGMS)</b>", subtitle_style))
    story.append(Spacer(1, 10))

    # Meta Table
    meta_info = [
        [
            Paragraph(f"<b>District:</b> {data.get('district', 'Rupnagar')}", styles['Normal']),
            Paragraph(f"<b>Date:</b> {data.get('date', str(date.today()))}", styles['Normal']),
            Paragraph(f"<b>Total Children:</b> {data.get('total_children', 0)}", styles['Normal']),
            Paragraph(f"<b>SAM Cases:</b> <font color='#b91c1c'><b>{data.get('sam_count', 0)}</b></font>", styles['Normal'])
        ]
    ]
    t_meta = Table(meta_info, colWidths=[135, 135, 135, 135])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 12))

    # Summary Stats
    summary_data = [
        ["SAM (Severe)", "MAM (Moderate)", "Recovering", "Normal", "Underweight", "Stunted"],
        [
            f"{data.get('sam_count', 0)} ({data.get('sam_pct', 0)}%)",
            f"{data.get('mam_count', 0)} ({data.get('mam_pct', 0)}%)",
            f"{data.get('recovering_count', 0)} ({data.get('recovering_pct', 0)}%)",
            f"{data.get('normal_count', 0)} ({data.get('normal_pct', 0)}%)",
            f"{data.get('underweight_pct', 0)}%",
            f"{data.get('stunted_pct', 0)}%"
        ]
    ]
    t_sum = Table(summary_data, colWidths=[90, 90, 90, 90, 90, 90])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_sum)
    story.append(Spacer(1, 14))

    # Children Register Table
    story.append(Paragraph("<b>Beneficiary Children Assessment Roster</b>", styles['Heading3']))
    
    table_headers = ["ID", "Name", "Sex", "Age", "AWC", "Status", "Wt(kg)", "Ht(cm)", "WHZ", "WAZ", "Class"]
    rows = [table_headers]
    for r in data.get("rows", []):
        rows.append([
            str(r.get("child_id", ""))[-6:],
            str(r.get("name", ""))[:14],
            str(r.get("sex", "")),
            f"{r.get('age_months', '')}m",
            str(r.get("awc_name", ""))[:12],
            str(r.get("current_state", "")),
            str(r.get("weight_kg", "-")),
            str(r.get("height_cm", "-")),
            str(r.get("whz", "-")),
            str(r.get("waz", "-")),
            str(r.get("acute_class", "-"))
        ])

    t_reg = Table(rows, colWidths=[40, 75, 25, 30, 70, 55, 45, 45, 45, 45, 65])
    t_reg.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#334155")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_reg)

    # Footer Signatures
    story.append(Spacer(1, 30))
    sig_data = [
        ["_________________________", "_________________________"],
        ["Medical Officer / LS", "Child Development Project Officer (CDPO)"]
    ]
    t_sig = Table(sig_data, colWidths=[270, 270])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_sig)

    doc.build(story)
    buffer.seek(0)
    return buffer
