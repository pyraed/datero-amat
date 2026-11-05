# Importaciones
from flask import Flask, render_template, request, send_file, jsonify
import csv
import io
import pandas as pd
import requests
import base64

from reportlab.platypus import Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# Cargar la grilla
df = pd.read_excel("grilla.xlsx")

# Crear diccionarios
tabla_6 = dict(zip(df["Monto"], df["Cuotas6"]))
tabla_12 = dict(zip(df["Monto"], df["Cuotas12"]))
tabla_18 = dict(zip(df["Monto"], df["Cuotas18"]))
tabla_24 = dict(zip(df["Monto"], df["Cuotas24"]))

# Cargar grilla Decreto 352
df_352 = pd.read_excel("grilla_decreto352.xlsx")
tabla_352_12 = dict(zip(df_352["Monto"], df_352["Cuotas12"]))
tabla_352_18 = dict(zip(df_352["Monto"], df_352["Cuotas18"]))
tabla_352_24 = dict(zip(df_352["Monto"], df_352["Cuotas24"]))
tabla_352_36 = dict(zip(df_352["Monto"], df_352["Cuotas36"]))


# Inicialización Flask
app = Flask(__name__)

API_WAPI_URL = "https://api.wapifirma.com/api/documentSet"
API_KEY_WAPI = "z4LNpZ8EWnA35cptNqaz0DAwPKiUnToW"  # 👈 reemplazar por tu api real

# ---------------- LOGICA ----------------

# Función para formatear números al estilo moneda argentina
def formatear(numero):
    return "{:,.2f}".format(numero).replace(",", "X").replace(".", ",").replace("X", ".")

# Función que calcula cuota social y coseguros según repartición y monto
def calcular_membresia(entidad, reparticion, monto):

    # =========================
    # MUTUAL 2 DE AGOSTO
    # =========================
    if entidad == "dos_agosto":

        # Caso Policía
        if reparticion in ["policia"]:
            cuota_social = 9630
            if monto <= 200000:
                medico, farmacia = 3750, 3950
            elif monto <= 300000:
                medico, farmacia = 6250, 6450
            elif monto <= 400000:
                medico, farmacia = 8250, 8450
            elif monto <= 600000:
                medico, farmacia = 11750, 11950
            else:
                medico, farmacia = 14750, 14950

        # Caso Educación
        elif reparticion == "educacion":
            cuota_social = 9630
            if monto <= 200000:
                medico, farmacia = 3750, 3950
            elif monto <= 300000:
                medico, farmacia = 6250, 6450
            elif monto <= 400000:
                medico, farmacia = 8250, 8450
            else:
                medico, farmacia = 9998, 9998

        # Caso Salud (valores fijos)
        elif reparticion == "salud":
            cuota_social = 9630
            medico = 14850
            if monto <= 350000:
                farmacia = 0
            else:
                farmacia = 14950

        # Caso IPS
        elif reparticion == "ips":
            cuota_social = 9000
            medico = 14850
            farmacia = 14950


        # Caso SPB (SEPARADO)
        elif reparticion == "spb":
            cuota_social = 4300
            if monto <= 200000:
                medico, farmacia = 3750, 3950
            elif monto <= 300000:
                medico, farmacia = 6250, 6450
            elif monto <= 400000:
                medico, farmacia = 8250, 8450
            elif monto <= 600000:
                medico, farmacia = 11750, 11950
            else:
                medico, farmacia = 14750, 14950

        return cuota_social, medico, farmacia


    # =========================
    # AMAT (LO ORIGINAL TUYO)
    # =========================

    # Caso Policía o SPB
    if reparticion == "policia":
        cuota_social = 4601
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

    elif reparticion == "spb":
        cuota_social = 4696
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

    # Caso Educación
    elif reparticion == "educacion":
        cuota_social = 10593
        if monto <= 200000:
            medico, farmacia = 3850, 3950
        elif monto <= 300000:
            medico, farmacia = 6150, 6250
        elif monto <= 400000:
            medico, farmacia = 8150, 8250
        else:
            medico, farmacia = 9998, 9998

    # Caso Salud (valores fijos)
    elif reparticion == "salud":
        cuota_social = 5530
        medico = 5078
        farmacia = 5214

    elif reparticion == "caja_policia":
        cuota_social = 4390
        medico = 0
        farmacia = 0

    elif reparticion == "ips":
        cuota_social = 4600
        medico = 0
        farmacia = 0    

    # Retorna los valores calculados
    return cuota_social, medico, farmacia


# Función que calcula el valor de la cuota del préstamo
def calcular_cuota(monto, cuotas):

    monto = float(monto)

    if cuotas == 6:
        return tabla_6.get(monto, 0)
    if cuotas == 12:
        return tabla_12.get(monto, 0)
    elif cuotas == 18:
        return tabla_18.get(monto, 0)
    elif cuotas == 24:
        return tabla_24.get(monto, 0)
    else:
        return 0

def calcular_cuota_352(monto, cuotas):

    monto = float(monto)

    if cuotas == 12:
        return tabla_352_12.get(monto, 0)
    elif cuotas == 18:
        return tabla_352_18.get(monto, 0)
    elif cuotas == 24:
        return tabla_352_24.get(monto, 0)
    elif cuotas == 36:
        return tabla_352_36.get(monto, 0)
    else:
        return 0
    
def enviar_a_firma(pdf_bytes, nombre, dni, telefono):

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    payload = {
        "document": pdf_base64,
        "document_name": "Datero AMAT",
        "firma_en_todas_las_hojas": True,
        "wpp": True,
        "datos_firmantes": [
            {
                "name": nombre,
                "dni": dni,
                "phone": telefono,
                "position_x": 200,
                "position_y": 40,
                "page": 1
            }
        ]
    }

    headers = {
        "x-api-key": API_KEY_WAPI,
        "Content-Type": "application/json"
    }

    response = requests.post(API_WAPI_URL, json=payload, headers=headers)

    data = response.json()

    print("RESPUESTA WAPI:", data)

    if "urls" not in data:
        raise Exception(f"Error WAPI: {data}")

    link = data["urls"][0]["link"]

    return link 






# ---------------- RUTAS ----------------

# Ruta principal (pantalla inicial)
@app.route("/")
def inicio():
    return render_template("index.html", montos=tabla_12.keys())


@app.route("/calcular", methods=["POST"])
def calcular():

    # Obtiene datos del formulario
    linea = request.form["linea"]
    reparticion = request.form["reparticion"]
    entidad = request.form["entidad"]
    monto = float(request.form["monto"])
    cuotas = int(request.form["cuotas"])

    print("LINEA:", linea)

    # Calcula valores según línea
    if linea == "haberes":

        cuota_social, medico, farmacia = calcular_membresia(entidad, reparticion, monto)
        valor_cuota = calcular_cuota(monto, cuotas)
        cuota_total = valor_cuota + cuota_social + medico + farmacia

    elif linea == "ayuda":

        # 🔥 Evita error si algo no coincide
        valor_cuota = 0
        cuota_social = 0
        medico = 0
        farmacia = 0

        # 🔥 Membresía VISUAL (no suma)
        if entidad == "amat":

            if reparticion == "educacion":
                cuota_social = 10593
                medico = 9998
                farmacia = 9998

            elif reparticion == "salud":
                cuota_social = 5530
                medico = 5078
                farmacia = 5214

        elif entidad == "dos_agosto":

            if reparticion == "educacion":
                cuota_social = 9630
                medico = 9998
                farmacia = 9998

            elif reparticion == "salud":
                cuota_social = 9630
                medico = 14850
                farmacia = 0

        # 🔥 Valores de ayuda
        if entidad == "amat":

            if reparticion == "educacion":
                monto = 200000
                cuotas = 24
                valor_cuota = 30589

            elif reparticion == "salud":
                monto = 100000
                cuotas = 24
                valor_cuota = 15822

        elif entidad == "dos_agosto":

            if reparticion == "educacion":
                monto = 200000
                cuotas = 24
                valor_cuota = 29626

            elif reparticion == "salud":
                monto = 100000
                cuotas = 24
                valor_cuota = 24480

        else:
            return "Entidad no válida"

        # 🔥 NO suma membresía (solo visual)
        cuota_total = valor_cuota

    elif linea == "bapro":

        # 🔥 Solo AMAT
        if entidad != "amat":
            return "Línea BAPRO no disponible para esta entidad"

        medico = 0
        farmacia = 0

        cuota_social, _, _ = calcular_membresia(entidad, reparticion, monto)

        cuotas = 12

        tabla_bapro = {
            100000: 20465.69,
            150000: 30698.53,
            200000: 40931.37,
            250000: 51164.21,
            300000: 61397.06
        }

        valor_cuota = tabla_bapro.get(monto, 0)

        cuota_total = valor_cuota + cuota_social

    elif linea == "decreto_352":

        if entidad != "amat":
            return "Línea Decreto 352 no disponible para esta entidad"

        cuota_social = 7000
        medico = 0
        farmacia = 0

        valor_cuota = calcular_cuota_352(monto, cuotas)
        cuota_total = valor_cuota + cuota_social

    # Genera link para enviar al cliente
    link = f"https://datero-amat.onrender.com/cliente?ent={entidad}&rep={reparticion}&monto={monto}&cuotas={cuotas}&linea={linea}"

    # Renderiza pantalla de resultados
    return render_template(
        "resultado.html",
        entidad=entidad,
        reparticion=reparticion,
        monto=formatear(monto),
        cuotas=cuotas,
        valor_cuota=formatear(valor_cuota),
        cuota_social=formatear(cuota_social),
        medico=formatear(medico),
        farmacia=formatear(farmacia),
        cuota_total=cuota_total,
        link=link,
        linea=linea
        
    )


# Ruta que abre el cliente (datero)
@app.route("/cliente")
def cliente():

    # Obtiene parámetros de la URL
    reparticion = request.args.get("rep")
    entidad = request.args.get("ent")
    linea = request.args.get("linea") or "haberes"  # 👈 fallback seguro
    print("ENTIDAD QUE LLEGA:", entidad)

    monto = float(request.args.get("monto"))
    monto = int(monto)
    cuotas = int(request.args.get("cuotas"))

    # 🔥 LOGICA SEGÚN LINEA

    if linea == "haberes":

        cuota_social, medico, farmacia = calcular_membresia(entidad, reparticion, monto)
        valor_cuota = calcular_cuota(monto, cuotas)

    elif linea == "ayuda":

         # 🔥 Membresía VISUAL (no suma)
         if entidad == "amat":

            if reparticion == "educacion":
               cuota_social = 10593
               medico = 9998
               farmacia = 9998

            elif reparticion == "salud":
               cuota_social = 5530
               medico = 5078
               farmacia = 5214

         elif entidad == "dos_agosto":

           if reparticion == "educacion":
              cuota_social = 9630
              medico = 9998
              farmacia = 9998

           else:
              cuota_social = 0
              medico = 0
              farmacia = 0


         if entidad == "amat":

            if reparticion == "educacion":
                monto = 200000
                cuotas = 24
                valor_cuota = 30589

            elif reparticion == "salud":
                monto = 100000
                cuotas = 24
                valor_cuota = 15822

         elif entidad == "dos_agosto":

            if reparticion == "educacion":
                monto = 200000
                cuotas = 24
                valor_cuota = 29626

            elif reparticion == "salud":
                monto = 100000
                cuotas = 24
                valor_cuota = 24480

    elif linea == "bapro":

        if entidad != "amat":
            return "Línea BAPRO no disponible para esta entidad"

        medico = 0
        farmacia = 0

        cuota_social, _, _ = calcular_membresia(entidad, reparticion, monto)

        cuotas = 12

        tabla_bapro = {
            100000: 20465.69,
            150000: 30698.53,
            200000: 40931.37,
            250000: 51164.21,
            300000: 61397.06
        }

        valor_cuota = tabla_bapro.get(monto, 0)

    elif linea == "decreto_352":

        if entidad != "amat":
            return "Línea Decreto 352 no disponible para esta entidad"

        cuota_social = 7000
        medico = 0
        farmacia = 0

        valor_cuota = calcular_cuota_352(monto, cuotas)

    # Renderiza formulario del cliente
    return render_template(
        "cliente.html",
        entidad=entidad,
        reparticion=reparticion,
        monto=formatear(monto),
        cuotas=cuotas,
        valor_cuota=formatear(valor_cuota),
        cuota_social=formatear(cuota_social),
        medico=formatear(medico),
        farmacia=formatear(farmacia)
    )


from datetime import datetime

def formatear_fecha(fecha):
    try:
        return datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        return fecha

def fmt_moneda(valor):
    if not valor:
        return ""
    s = str(valor).strip()
    if "," in s:
        if s.endswith(",00"):
            return s[:-3]
        return s
    try:
        n = float(s)
        if n == int(n):
            return "{:,.0f}".format(n).replace(",", ".")
        else:
            return "{:,.2f}".format(n).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return s


# Ruta que guarda datos y genera el PDF
@app.route("/guardar", methods=["POST"])
def guardar():

    # Obtiene todos los datos enviados desde el formulario
    datos = request.form

    # Guarda los datos en un archivo CSV
    with open("datos_clientes.csv", "a", newline="", encoding="utf-8") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(datos.values())

    # Crea un buffer en memoria para generar el PDF
    buffer = io.BytesIO()
    PAGE_W, PAGE_H = letter
    MARGIN_LR = 40
    MARGIN_TB = 18
    content_w = PAGE_W - 2 * MARGIN_LR

    doc = SimpleDocTemplate(buffer, pagesize=letter,
        topMargin=MARGIN_TB, bottomMargin=MARGIN_TB,
        leftMargin=MARGIN_LR, rightMargin=MARGIN_LR)

    elementos = []
    styles = getSampleStyleSheet()

    es_dos_agosto = datos.get("entidad") == "dos_agosto"
    color_marca = HexColor("#2C2C2C") if es_dos_agosto else HexColor("#FFD600")
    nombre_entidad = "MUTUAL 2 DE AGOSTO" if es_dos_agosto else "AMAT - MUTUAL AMARILLA"
    nombre_mutual = "Dos de Agosto" if es_dos_agosto else "AMAT"
    logo_path = "static/logo_dos_agosto.png" if es_dos_agosto else "static/logo_amat.jpg"

    color_borde = HexColor("#D1D5DB")
    color_texto = HexColor("#111827")
    color_label = HexColor("#6B7280")

    # ── HEADER ──
    header_title_style = ParagraphStyle("h_title", parent=styles["Normal"],
        fontSize=14, textColor=color_texto, fontName="Helvetica-Bold", leading=17, alignment=TA_LEFT)
    header_sub_style = ParagraphStyle("h_sub", parent=styles["Normal"],
        fontSize=8, textColor=color_label, leading=10, alignment=TA_LEFT)

    logo = Image(logo_path, width=45, height=45)
    header_text_cell = [
        Paragraph(nombre_entidad, header_title_style),
        Paragraph("DATERO - SOLICITUD DE AYUDA ECONÓMICA", header_sub_style)
    ]
    header_table = Table([[logo, header_text_cell]], colWidths=[58, content_w - 58])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elementos.append(header_table)

    line_table = Table([[""]], colWidths=[content_w], rowHeights=[2])
    line_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_marca),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elementos.append(Spacer(1, 4))
    elementos.append(line_table)
    elementos.append(Spacer(1, 6))

    # ── ESTILOS TABLAS ──
    label_style = ParagraphStyle("label", parent=styles["Normal"],
        fontSize=7.5, textColor=color_label, leading=9)
    value_style = ParagraphStyle("value", parent=styles["Normal"],
        fontSize=7.5, textColor=color_texto, fontName="Helvetica-Bold", leading=9)
    color_texto_section = color_texto if not es_dos_agosto else colors.white
    section_style = ParagraphStyle("section", parent=styles["Normal"],
        fontSize=8, textColor=color_texto_section, fontName="Helvetica-Bold", leading=10)

    col_label = 155
    col_value = content_w - col_label

    def tabla(titulo, filas):
        header_row = [[Paragraph(titulo, section_style), ""]]
        data_rows = [[Paragraph(f[0], label_style), Paragraph(str(f[1]), value_style)] for f in filas]
        data = header_row + data_rows
        t = Table(data, colWidths=[col_label, col_value])
        style_cmds = [
            ("SPAN", (0, 0), (1, 0)),
            ("BACKGROUND", (0, 0), (-1, 0), color_marca),
            ("TOPPADDING", (0, 0), (-1, 0), 3),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 2.5),
            ("GRID", (0, 0), (-1, -1), 0.4, color_borde),
            ("BOX", (0, 0), (-1, -1), 0.6, color_borde),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        for i in range(1, len(data)):
            if i % 2 == 0:
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), HexColor("#F9FAFB")))
        t.setStyle(TableStyle(style_cmds))
        return t

    SP = 4

    elementos.append(tabla("DATOS PERSONALES", [
        ["Apellido y Nombre", datos.get("nombre", "").upper()],
        ["DNI", datos.get("dni", "").upper()],
        ["Nacionalidad", datos.get("nacionalidad", "").upper()],
        ["Fecha de Nacimiento", formatear_fecha(datos.get("fecha_nacimiento", ""))],
        ["Domicilio", datos.get("domicilio", "").upper()],
        ["Localidad", datos.get("localidad", "").upper()],
        ["CP", datos.get("cp", "").upper()],
        ["CUIT", datos.get("cuit", "").upper()],
        ["Provincia", datos.get("provincia", "").upper()],
        ["Teléfono", datos.get("celular", "").upper()],
        ["Email", datos.get("email", "").upper()],
        ["CBU", datos.get("cbu", "").upper()],
        ["Repartición", datos.get("reparticion", "").upper()]
    ]))
    elementos.append(Spacer(1, SP))

    elementos.append(tabla("MEMBRESÍA", [
        ["Cuota Social", "$ " + fmt_moneda(datos.get("cuota_social", ""))],
        ["Coseguro Médico", "$ " + fmt_moneda(datos.get("medico", ""))],
        ["Coseguro Farmacia", "$ " + fmt_moneda(datos.get("farmacia", ""))]
    ]))
    elementos.append(Spacer(1, SP))

    elementos.append(tabla("REFERENCIA 1", [
        ["Parentesco", datos.get("ref1_parentesco", "").upper()],
        ["Nombre", datos.get("ref1_nombre", "").upper()],
        ["Teléfono", datos.get("ref1_tel", "")]
    ]))
    elementos.append(Spacer(1, SP))

    elementos.append(tabla("REFERENCIA 2", [
        ["Parentesco", datos.get("ref2_parentesco", "").upper()],
        ["Nombre", datos.get("ref2_nombre", "").upper()],
        ["Teléfono", datos.get("ref2_tel", "")]
    ]))
    elementos.append(Spacer(1, SP))

    elementos.append(tabla("DATOS DE LA AYUDA ECONÓMICA", [
        ["Monto", "$ " + fmt_moneda(datos.get("monto", ""))],
        ["Cuotas", datos.get("cuotas", "")],
        ["Valor Cuota", "$ " + fmt_moneda(datos.get("valor_cuota", ""))]
    ]))
    elementos.append(Spacer(1, SP))

    # ── LEYENDA ──
    leyenda_style = ParagraphStyle("leyenda", parent=styles["Normal"],
        fontSize=6.5, textColor=color_label, leading=8, alignment=TA_LEFT)
    leyenda_text = f"Declaro conocer los derechos y obligaciones de los socios de {nombre_mutual}, las condiciones generales de la prestación recibida, la autorización para retención de cuota y descuento de haberes y CBU Resolución 1481 - INAES - ANEXO. Ley Nº 25.246 y ANEXOS correspondientes al organismo donde desempeño mi relación laboral. Importe a transferir sujeto a grilla del fondeador (en base al Decreto 988/21). El crédito puede ser pasible del cobro del impuesto al sello (1,2%), según línea crediticia. Registro de firma para legajo y aceptación de plan aprobado."

    leyenda = Table([[Paragraph(leyenda_text, leyenda_style)]], colWidths=[content_w])
    leyenda.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, color_borde),
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F9FAFB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos.append(leyenda)
    elementos.append(Spacer(1, 6))

    # ── FIRMA ──
    firma_label_style = ParagraphStyle("firma_label", parent=styles["Normal"],
        fontSize=8, textColor=color_texto, fontName="Helvetica-Bold", alignment=TA_CENTER)
    firma_body_h = 150
    pad_h = (firma_body_h - 14) / 2
    firma = Table(
        [[""], [Paragraph("Firma", firma_label_style)], [""]],
        colWidths=[content_w], rowHeights=[pad_h, 14, pad_h]
    )
    firma.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elementos.append(firma)

    # Construye el PDF
    doc.build(elementos)
    buffer.seek(0)

    buffer.seek(0)
    pdf_bytes = buffer.getvalue()

    nombre = datos.get("nombre")
    dni = datos.get("dni")
    telefono = datos.get("celular")
    # limpiar todo lo que no sea número
    telefono = ''.join(filter(str.isdigit, telefono))

    # sacar 0 inicial si existe
    if telefono.startswith("0"):
        telefono = telefono[1:]

    # agregar 549 si no lo tiene
    if not telefono.startswith("549"):
        telefono = "549" + telefono

    link_firma = enviar_a_firma(pdf_bytes, nombre, dni, telefono)

    return jsonify({
        "link_firma": link_firma
})


# ================= API PARA MAKE =================

API_KEY = "123456"

@app.route("/api/calcular_oferta", methods=["POST"])
def api_calcular_oferta():

    data = request.json

    print("DATA API:", data)  # 👈 para debug

    # 🔐 Seguridad
    if data.get("api_key") != API_KEY:
        return jsonify({"error": "No autorizado"}), 401

    try:
        linea = data.get("linea")
        reparticion = data.get("reparticion")
        entidad = data.get("entidad")
        monto = float(data.get("monto"))
        cuotas = int(data.get("cuotas"))

        # ================= LOGICA =================

        if linea == "haberes":
            cuota_social, medico, farmacia = calcular_membresia(entidad, reparticion, monto)
            valor_cuota = calcular_cuota(monto, cuotas)
            cuota_total = valor_cuota + cuota_social + medico + farmacia

        elif linea == "ayuda":

            valor_cuota = 0
            cuota_social = 0
            medico = 0
            farmacia = 0

            if entidad == "amat":

                if reparticion == "educacion":
                    monto = 200000
                    cuotas = 24
                    valor_cuota = 30589

                elif reparticion == "salud":
                    monto = 100000
                    cuotas = 24
                    valor_cuota = 15822

            elif entidad == "dos_agosto":

                if reparticion == "educacion":
                    monto = 200000
                    cuotas = 24
                    valor_cuota = 29626

                elif reparticion == "salud":
                    monto = 0
                    cuotas = 0
                    valor_cuota = 0

            cuota_total = valor_cuota

        elif linea == "bapro":

            if entidad != "amat":
                return jsonify({"error": "Línea BAPRO no disponible"}), 400

            medico = 0
            farmacia = 0

            cuota_social, _, _ = calcular_membresia(entidad, reparticion, monto)

            cuotas = 12

            tabla_bapro = {
                100000: 20465.69,
                150000: 30698.53,
                200000: 40931.37,
                250000: 51164.21,
                300000: 61397.06
            }

            valor_cuota = tabla_bapro.get(monto, 0)
            cuota_total = valor_cuota + cuota_social

        elif linea == "decreto_352":

            if entidad != "amat":
                return jsonify({"error": "Línea Decreto 352 no disponible"}), 400

            cuota_social = 7000
            medico = 0
            farmacia = 0

            valor_cuota = calcular_cuota_352(monto, cuotas)
            cuota_total = valor_cuota + cuota_social

        else:
            return jsonify({"error": "Linea no valida"}), 400

        # 🔗 Generar link
        link = f"https://datero-amat.onrender.com/cliente?ent={entidad}&rep={reparticion}&monto={monto}&cuotas={cuotas}&linea={linea}"

        # 📦 RESPUESTA PARA MAKE
        return jsonify({
            "entidad": entidad,
            "reparticion": reparticion,
            "monto": monto,
            "cuotas": cuotas,
            "valor_cuota": valor_cuota,
            "cuota_social": cuota_social,
            "medico": medico,
            "farmacia": farmacia,
            "cuota_total": cuota_total,
            "link_firma": link
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Ejecuta la app en modo debug
if __name__ == "__main__":
    app.run(debug=True)