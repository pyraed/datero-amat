# Importaciones
from flask import Flask, render_template, request, send_file, jsonify
import csv
import io
import pandas as pd
import requests
import base64

from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors


# Cargar la grilla
df = pd.read_excel("grilla.xlsx")

# Crear diccionarios
tabla_6 = dict(zip(df["Monto"], df["Cuotas6"]))
tabla_12 = dict(zip(df["Monto"], df["Cuotas12"]))
tabla_18 = dict(zip(df["Monto"], df["Cuotas18"]))
tabla_24 = dict(zip(df["Monto"], df["Cuotas24"]))


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
            cuota_social = 9000
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
            cuota_social = 9900
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
            cuota_social = 0
            medico = 0
            farmacia = 0


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

    # Caso Educación
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

    # Caso Salud (valores fijos)
    elif reparticion == "salud":
        cuota_social = 5172
        medico = 5078
        farmacia = 5214

    elif reparticion == "caja_policia":
        cuota_social = 4390  # 👈 o el valor que corresponda
        medico = 0
        farmacia = 0

    elif reparticion == "ips":
        cuota_social = 4390  # 👈 o el valor que corresponda
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
                "position": 1
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
                cuota_social = 9000
                medico = 9998
                farmacia = 9998

            elif reparticion == "salud":
                cuota_social = 5172
                medico = 5078
                farmacia = 5214

        elif entidad == "dos_agosto":

            if reparticion == "educacion":
                cuota_social = 9900
                medico = 9998
                farmacia = 9998

            else:
                cuota_social = 0
                medico = 0
                farmacia = 0

        # 🔥 Valores de ayuda
        if entidad == "amat":

            if reparticion == "educacion":
                monto = 200000
                cuotas = 24
                valor_cuota = 28996

            elif reparticion == "salud":
                monto = 100000
                cuotas = 24
                valor_cuota = 15464

        elif entidad == "dos_agosto":

            if reparticion == "educacion":
                monto = 200000
                cuotas = 24
                valor_cuota = 29896

            elif reparticion == "salud":
                monto = 0
                cuotas = 0
                valor_cuota = 0

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
               cuota_social = 9000
               medico = 9998
               farmacia = 9998

            elif reparticion == "salud":
               cuota_social = 5172
               medico = 5078
               farmacia = 5214

         elif entidad == "dos_agosto":

           if reparticion == "educacion":
              cuota_social = 9900
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
                valor_cuota = 28996

            elif reparticion == "salud":
                monto = 100000
                cuotas = 24
                valor_cuota = 15464

         elif entidad == "dos_agosto":

            if reparticion == "educacion":
                monto = 200000
                cuotas = 24
                valor_cuota = 29896

            elif reparticion == "salud":
                monto = 0
                cuotas = 0
                valor_cuota = 0

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
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=20, bottomMargin=20)
    
    elementos = []

    styles = getSampleStyleSheet()

    # TITULO
    if datos.get("entidad") == "dos_agosto":
       titulo = Paragraph("<b>DATERO - MUTUAL 2 DE AGOSTO</b>", styles["Title"])
    else:
       titulo = Paragraph("<b>DATERO - AMAT</b>", styles["Title"])

    elementos.append(titulo)
    elementos.append(Spacer(1, 5))


    # Función interna para crear tablas en el PDF
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

    # Sección datos personales
    elementos.append(tabla("DATOS PERSONALES", [
        ["Apellido y Nombre", datos.get("nombre").upper()],
        ["DNI", datos.get("dni").upper()],
        ["Nacionalidad", datos.get("nacionalidad").upper()],
        ["Fecha de Nacimiento", formatear_fecha(datos.get("fecha_nacimiento"))],
        ["Domicilio", datos.get("domicilio").upper()],
        ["Localidad", datos.get("localidad").upper()],
        ["CP", datos.get("cp").upper()],
        ["CUIT", datos.get("cuit").upper()],
        ["Provincia", datos.get("provincia").upper()],
        ["Teléfono", datos.get("celular").upper()],
        ["Email", datos.get("email").upper()],
        ["CBU", datos.get("cbu").upper()],
        ["Repartición", datos.get("reparticion").upper()]
    ]))

    
    # Sección membresía
    elementos.append(tabla("MEMBRESÍA", [
        ["Cuota Social", datos.get("cuota_social")],
        ["Coseguro Médico", datos.get("medico")],
        ["Coseguro Farmacia", datos.get("farmacia")]
    ]))

    # Referencia 1
    elementos.append(tabla("REFERENCIA 1", [
        ["Parentesco", datos.get("ref1_parentesco").upper()],
        ["Nombre", datos.get("ref1_nombre").upper()],
        ["Teléfono", datos.get("ref1_tel")]
    ]))

    # Referencia 2
    elementos.append(tabla("REFERENCIA 2", [
        ["Parentesco", datos.get("ref2_parentesco").upper()],
        ["Nombre", datos.get("ref2_nombre").upper()],
        ["Teléfono", datos.get("ref2_tel")]
    ]))

    # Datos del crédito
    elementos.append(tabla("DATOS DE LA AYUDA ECONÓMICA", [
        ["Monto", datos.get("monto")],
        ["Cuotas", datos.get("cuotas")],
        ["Valor Cuota", datos.get("valor_cuota")]
    ]))


    # 🔥 Nombre de mutual dinámico
    if datos.get("entidad") == "dos_agosto":
       nombre_mutual = "Dos de Agosto"
    else:
       nombre_mutual = "AMAT"

    # Texto legal (leyenda)
    leyenda = Table([
    [f"Declaro conocer los derechos y obligaciones de los socios de {nombre_mutual}, las condiciones generales de la prestación recibida la autorización para retención de cuota"],
    ["y descuento de haberes y CBU Resolución 1481 - INAES - ANEXO. Ley Nº 25.246 y ANEXOS correspondientes al organismo donde desempeño mi relación laboral."],   
    ["Importe a transferir sujeto a grilla del fondeador (en base al Decreto 988/21)." "El crédito puede ser pasible del cobro del impuesto al sello (1,2%), según línea crediticia."],
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

    # Espacio de firma
    firma = Table([["Firma"],[""]], colWidths=[450], rowHeights=[20,90])
    firma.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black)]))
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
                    valor_cuota = 28996

                elif reparticion == "salud":
                    monto = 100000
                    cuotas = 24
                    valor_cuota = 15464

            elif entidad == "dos_agosto":

                if reparticion == "educacion":
                    monto = 200000
                    cuotas = 24
                    valor_cuota = 29896

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