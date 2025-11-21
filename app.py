import os
from io import BytesIO
from datetime import datetime

from flask import Flask, request, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

import smtplib
from email.message import EmailMessage

# --------------------
# CONFIG FROM ENV VARS
# --------------------
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

SEND_TO_EMAIL = os.environ.get("SEND_TO_EMAIL", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_USER or "no-reply@example.com")

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/submit-estimate", methods=["POST"])
def submit_estimate():
    # Grab form fields (names must match your HTML form)
    name = request.form.get("name", "")
    phone = request.form.get("phone", "")
    email = request.form.get("email", "")
    contact_method = request.form.get("contact_method", "")
    address = request.form.get("address", "")
    city = request.form.get("city", "")
    zip_code = request.form.get("zip", "")
    space_type = request.form.get("space_type", "")
    sqft = request.form.get("square_footage", "")
    finish = request.form.get("finish", "")
    condition = request.form.get("condition", "")
    vision = request.form.get("vision", "")
    timeline = request.form.get("timeline", "")
    budget = request.form.get("budget", "")
    referral = request.form.get("referral", "")

    # 1) Generate the branded PDF in memory
    pdf_bytes = generate_branded_pdf(
        name=name,
        phone=phone,
        email=email,
        contact_method=contact_method,
        address=address,
        city=city,
        zip_code=zip_code,
        space_type=space_type,
        sqft=sqft,
        finish=finish,
        condition=condition,
        vision=vision,
        timeline=timeline,
        budget=budget,
        referral=referral,
    )

    # 2) Email it to you
    try:
        send_estimate_email(
            pdf_bytes=pdf_bytes,
            filename=f"Edgemore_Estimate_{sanitize_filename(name)}.pdf",
            name=name,
            phone=phone,
            email=email,
            space_type=space_type,
            sqft=sqft,
        )
        status = "ok"
        msg = "Estimate submitted successfully."
    except Exception as e:
        status = "error"
        msg = f"Error sending email: {e}"

    # 3) Respond JSON (you can swap this for a redirect if you want)
    return jsonify({"status": status, "message": msg})


def generate_branded_pdf(**data):
    """
    Creates a luxury black + gold style PDF in memory using ReportLab.
    Returns raw PDF bytes.
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleGold",
        parent=styles["Title"],
        alignment=1,
        textColor=colors.gold,
        fontSize=20,
        leading=24,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "SubtitleGold",
        parent=styles["Normal"],
        alignment=1,
        textColor=colors.whitesmoke,
        fontSize=10,
        leading=12,
        spaceAfter=18,
    )

    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading3"],
        textColor=colors.gold,
        fontSize=12,
        leading=14,
        spaceBefore=10,
        spaceAfter=4,
    )

    field_label = ParagraphStyle(
        "FieldLabel",
        parent=styles["Normal"],
        textColor=colors.gold,
        fontSize=9,
        leading=11,
    )

    field_value = ParagraphStyle(
        "FieldValue",
        parent=styles["Normal"],
        textColor=colors.whitesmoke,
        fontSize=10,
        leading=13,
    )

    footer_style = ParagraphStyle(
        "FooterGold",
        parent=styles["Normal"],
        textColor=colors.gold,
        fontSize=8,
        leading=10,
        alignment=1,
        spaceBefore=20,
    )

    elements = []

    # Header
    elements.append(Paragraph("EDGEMORE EPOXY AND PAINTING", title_style))
    elements.append(Paragraph("Luxury Epoxy & Fine Finishes • Tampa Bay", subtitle_style))

    def field_row(label, value):
        return [
            Paragraph(label, field_label),
            Paragraph(value if value else "-", field_value),
        ]

    # CLIENT INFO
    elements.append(Paragraph("CLIENT INFORMATION", section_style))
    client_table_data = [
        field_row("Full Name", data.get("name", "")),
        field_row("Phone Number", data.get("phone", "")),
        field_row("Email Address", data.get("email", "")),
        field_row("Preferred Contact", data.get("contact_method", "")),
        field_row("Service Address", data.get("address", "")),
        field_row("City", data.get("city", "")),
        field_row("ZIP Code", data.get("zip_code", "")),
    ]

    client_table = Table(client_table_data, colWidths=[160, 360])
    client_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(client_table)
    elements.append(Spacer(1, 10))

    # PROJECT DETAILS
    elements.append(Paragraph("PROJECT DETAILS", section_style))
    project_table_data = [
        field_row("Type of Space", data.get("space_type", "")),
        field_row("Approx. Square Footage", data.get("sqft", "")),
        field_row("Desired Finish", data.get("finish", "")),
        field_row("Surface Condition", data.get("condition", "")),
        field_row("Timeline", data.get("timeline", "")),
        field_row("Budget", data.get("budget", "")),
        field_row("Referral Source", data.get("referral", "")),
    ]

    project_table = Table(project_table_data, colWidths=[160, 360])
    project_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(project_table)
    elements.append(Spacer(1, 10))

    # VISION / DESCRIPTION
    elements.append(Paragraph("PROJECT DESCRIPTION / VISION", section_style))
    vision_text = data.get("vision", "").strip() or "No description provided."
    elements.append(Paragraph(vision_text.replace("\n", "<br/>"), field_value))

    # Footer
    elements.append(Spacer(1, 18))
    footer_text = (
        "Edgemore Epoxy and Painting • Leggari-Certified Installer<br/>"
        "Premium Metallic Epoxy • Garage Floors • Driveways • Countertops • Commercial Floors<br/>"
        "Phone: 727-421-4564 • Generated on "
        + datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    elements.append(Paragraph(footer_text, footer_style))

    # Black + gold border background
    def draw_background(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.black)
        canvas.rect(0, 0, letter[0], letter[1], fill=1, stroke=0)
        margin = 24
        canvas.setStrokeColor(colors.gold)
        canvas.setLineWidth(1.2)
        canvas.rect(
            margin, margin, letter[0] - 2 * margin, letter[1] - 2 * margin, fill=0, stroke=1
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_background, onLaterPages=draw_background)

    buffer.seek(0)
    return buffer.read()


def send_estimate_email(pdf_bytes, filename, name, phone, email, space_type, sqft):
    """
    Sends an email with the PDF attached.
    """
    subject = f"New Edgemore Estimate Request from {name or 'Unknown'}"
    body = (
        f"A new estimate request has been submitted.\n\n"
        f"Name: {name}\n"
        f"Phone: {phone}\n"
        f"Email: {email}\n"
        f"Type of Space: {space_type}\n"
        f"Approx. Sq Ft: {sqft}\n\n"
        f"The full details are in the attached PDF."
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = SEND_TO_EMAIL
    msg.set_content(body)

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=filename,
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def sanitize_filename(s):
    if not s:
        return "client"
    return "".join(c for c in s if c.isalnum() or c in ("-", "_")).strip("_") or "client"


if __name__ == "__main__":
    # Local dev only – on Render we'll use gunicorn
    app.run(host="0.0.0.0", port=5000, debug=True)
