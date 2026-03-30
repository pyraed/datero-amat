from flask import Flask, render_template, request, send_file
import csv
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

app = Flask(__name__)

# ---------------- LOGICA ----------------

def formatear(numero):
    return f"$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calcular_membresia(reparticion, monto):
    if reparticion in ["policia", "spb"]:
        cuota_social = 4300
        if monto <= 200000:
            medico, farmacia = 3850, 3950
        elif monto <= 300000:
            medico, farmacia = 6150, 6250
        elif monto <= 400000:
            medico, farmacia = 8150, 8250
        elif monto <= 600000:
            medico, farmacia = 11850, 11950
        else:
            medico, farmacia = 14850, 14950

    elif reparticion == "educacion":
        cuota_social = 9900
        if monto <= 200000:
            medico, farmacia = 3850, 3950
        elif monto <= 300000:
            medico, farmacia = 6150, 6250
        elif monto <= 400000:
            medico, farmacia = 8150, 8250
        else:
            medico, farmacia = 9998, 9998

    elif reparticion == "salud":
        cuota_social = 4950
        medico = 5078
        farmacia = 5214

    return cuota_social, medico, farmacia


def calcular_cuota(monto, cuotas):
    tabla_12 = {
        100000: 12180.02, 200000: 24360.04, 300000: 36540.06,
        400000: 48720.08, 500000: 60900.10, 600000: 73080.12,
        700000: 85260.14, 800000: 97440.16, 900000: 109620.18,
        1000000: 121800.20, 1200000: 146160.24, 1500000: 182700.30,
        2000000: 243600.40
    }

    tabla_24 = {
        100000: 8094.27, 200000: 16188.54, 300000: 24282.82,
        400000: 32377.09, 500000: 40471.36, 600000: 48565.63,
        700000: 56559.91, 800000: 64754.18, 900000: 72848.45,
        1000000: 80942.72, 1200000: 97131.27, 1500000: 121414.09,
        2000000: 161885.45
    }

    return tabla_12.get(monto, 0) if cuotas == 12 else tabla_24.get(monto, 0)

# ---------------- RUTAS ----------------

@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/calcular", methods=["POST"])
def calcular():
    reparticion = request.form["reparticion"]
    monto = int(request.form["monto"])
    cuotas = int(request.form["cuotas"])

    cuota_social, medico, farmacia = calcular_membresia(reparticion, monto)
    valor_cuota = calcular_cuota(monto, cuotas)

    # 🔥 LINK CORRECTO ONLINE
    link = f"https://datero-amat.onrender.com/cliente?rep={reparticion}&monto={monto}&cuotas={cuotas}"

    return render_template(
        "resultado.html",
        reparticion=reparticion,
        monto=formatear(monto),
        cuotas=cuotas,
        valor_cuota=formatear(valor_cuota),
        cuota_social=formatear(cuota_social),
        medico=formatear(medico),
        farmacia=formatear(farmacia),
        link=link
    )


@app.route("/cliente")
def cliente():
    reparticion = request.args.get("rep")
    monto = int(request.args.get("monto"))
    cuotas = int(request.args.get("cuotas"))

    cuota_social, medico, farmacia = calcular_membresia(reparticion, monto)
    valor_cuota = calcular_cuota(monto, cuotas)

    return render_template(
        "cliente.html",
        reparticion=reparticion,
        monto=formatear(monto),
        cuotas=cuotas,
        valor_cuota=formatear(valor_cuota),
        cuota_social=formatear(cuota_social),
        medico=formatear(medico),
        farmacia=formatear(farmacia)
    )


@app.route("/guardar", methods=["POST"])
def guardar():
    datos = request.form

    with open("datos_clientes.csv", "a", newline="", encoding="utf-8") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(datos.values())

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=20, bottomMargin=20)

    elementos = []

    def tabla(titulo, filas):
        data = [[titulo, ""]] + filas
        t = Table(data, colWidths=[200, 250])
        t.setStyle(TableStyle([
            ("SPAN", (0,0), (1,0)),
            ("BACKGROUND", (0,0), (-1,0), colors.grey),
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("FONTSIZE", (0,0), (-1,-1), 8)
        ]))
        return t

    elementos.append(tabla("DATOS PERSONALES", [
        ["Apellido y Nombre", datos.get("nombre")],
        ["DNI", datos.get("dni")],
        ["Nacionalidad", datos.get("nacionalidad")],
        ["Domicilio", datos.get("domicilio")],
        ["Localidad", datos.get("localidad")],
        ["CP", datos.get("cp")],
        ["CUIT", datos.get("cuit")],
        ["Provincia", datos.get("provincia")],
        ["Teléfono", datos.get("celular")],
        ["Email", datos.get("email")]
    ]))

    elementos.append(tabla("DATOS BANCARIOS", [["CBU", datos.get("cbu")]]))

    elementos.append(tabla("DATOS LABORALES", [
        ["Repartición", datos.get("reparticion")],
        ["Localidad", datos.get("loc_laboral")]
    ]))

    elementos.append(tabla("MEMBRESÍA", [
        ["Cuota Social", datos.get("cuota_social")],
        ["Coseguro Médico", datos.get("medico")],
        ["Coseguro Farmacia", datos.get("farmacia")]
    ]))

    elementos.append(tabla("REFERENCIA 1", [
        ["Parentesco", datos.get("ref1_parentesco")],
        ["Nombre", datos.get("ref1_nombre")],
        ["Teléfono", datos.get("ref1_tel")]
    ]))

    elementos.append(tabla("REFERENCIA 2", [
        ["Parentesco", datos.get("ref2_parentesco")],
        ["Nombre", datos.get("ref2_nombre")],
        ["Teléfono", datos.get("ref2_tel")]
    ]))

    elementos.append(tabla("DATOS DE LA AYUDA ECONÓMICA", [
        ["Monto", datos.get("monto")],
        ["Cuotas", datos.get("cuotas")],
        ["Valor Cuota", datos.get("valor_cuota")]
    ]))

    # 🔥 LEYENDA CORREGIDA (no se desborda)
    leyenda = Table([
    ["Declaro conocer los derechos y obligaciones de los socios de AMAT, las condiciones generales de la prestación recibida la autorización para retención de cuota"],
    ["y descuento de haberes y CBU Resolución 1481 - INAES - ANEXO. Ley Nº 25.246 y ANEXOS correspondientes al organismo donde desempeño mi relación laboral."],   
    ["Importe a transferir sujeto a grilla del fondeador (en base al Decreto 988/21)."],
    ["El crédito puede ser pasible del cobro del impuesto al sello (1,2%), según línea crediticia."],
    ["Registro de firma para legajo y aceptación de plan aprobado"]
    ], colWidths=[460])

    leyenda.setStyle(TableStyle([
    ("FONTSIZE", (0,0), (-1,-1), 7),
    ("LEFTPADDING", (0,0), (-1,-1), 2),
    ("RIGHTPADDING", (0,0), (-1,-1), 2),
    ("TOPPADDING", (0,0), (-1,-1), 1),
    ("BOTTOMPADDING", (0,0), (-1,-1), 1),
    ]))

    elementos.append(leyenda)

    firma = Table([["Firma"],[""]], colWidths=[450], rowHeights=[15,60])
    firma.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black)]))
    elementos.append(firma)

    doc.build(elementos)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="datero.pdf", mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)