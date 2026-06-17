import os
import io
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)

# Database Configuration (Saves locally as clients.db)
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'clients.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Schema/Model representing the PRD Data Points
class ClientRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    inflow = db.Column(db.Float, nullable=False)
    outflow = db.Column(db.Float, nullable=False)
    retirement = db.Column(db.Float, nullable=False)
    non_retirement = db.Column(db.Float, nullable=False)
    trust = db.Column(db.Float, nullable=False)
    liabilities = db.Column(db.Float, nullable=False)
    private_reserve = db.Column(db.Float, nullable=False)
    net_worth = db.Column(db.Float, nullable=False)

# Initialize database tables automatically
with app.app_context():
    db.create_all()

@app.route("/")
def index():
    # Fetch all past calculations to show history on the dashboard
    clients = ClientRecord.query.order_by(ClientRecord.id.desc()).all()
    return render_template("index.html", clients=clients)

@app.route("/calculate", methods=["POST"])
def calculate():
    name = request.form["client_name"]
    inflow = float(request.form["inflow"])
    outflow = float(request.form["outflow"])
    retirement = float(request.form["retirement"])
    non_retirement = float(request.form["non_retirement"])
    trust = float(request.form["trust"])
    liabilities = float(request.form["liabilities"])

    # Core Business Logic Formulas required by PRD
    private_reserve = inflow - outflow
    net_worth = (retirement + non_retirement + trust) - liabilities

    # Save to SQLite
    new_client = ClientRecord(
        name=name, inflow=inflow, outflow=outflow,
        retirement=retirement, non_retirement=non_retirement,
        trust=trust, liabilities=liabilities,
        private_reserve=private_reserve, net_worth=net_worth
    )
    db.session.add(new_client)
    db.session.commit()

    return redirect(url_for('index'))

@app.route("/download_pdf/<int:client_id>")
def download_pdf(client_id):
    client = ClientRecord.query.get_or_404(client_id)
    
    # Generate an in-memory PDF file
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#1e3a8a'), spaceAfter=15)
    normal_style = styles['Normal']

    # PDF Building blocks
    story.append(Paragraph("AW Financial Report Portal", title_style))
    story.append(Paragraph(f"<b>Client Profile Statement</b>", styles['Heading3']))
    story.append(Paragraph(f"<b>Client Name:</b> {client.name}", normal_style))
    story.append(Spacer(1, 15))

    # Construct the structural data table for SACS/TCC metrics
    data = [
        [Paragraph('<b>Metric Description</b>', normal_style), Paragraph('<b>Value ($)</b>', normal_style)],
        ['Monthly Inflow', f"{client.inflow:,.2f}"],
        ['Monthly Outflow', f"{client.outflow:,.2f}"],
        ['Calculated Private Reserve', f"{client.private_reserve:,.2f}"],
        ['', ''], 
        ['Retirement Assets', f"{client.retirement:,.2f}"],
        ['Non-Retirement Assets', f"{client.non_retirement:,.2f}"],
        ['Trust Values', f"{client.trust:,.2f}"],
        ['Total Liabilities', f"{client.liabilities:,.2f}"],
        ['Grand Total Net Worth', f"{client.net_worth:,.2f}"]
    ]

    t = Table(data, colWidths=[240, 160])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0,0), (1,0), colors.HexColor('#1e3a8a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#1e3a8a')),
        ('LINEBELOW', (0,-1), (1,-1), 1.5, colors.HexColor('#1e3a8a')),
        ('FONTNAME', (0,-1), (1,-1), 'Helvetica-Bold')
    ]))
    
    story.append(t)
    doc.build(story)
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{client.name.replace(' ', '_')}_Report.pdf", mimetype='application/pdf')

if __name__ == "__main__":
    app.run(debug=True)