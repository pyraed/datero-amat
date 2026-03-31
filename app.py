from flask import Flask, render_template, request, send_file, redirect, session
import csv
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "amat_secreto_123"

# 🔐 USUARIO HARDCODE (después lo mejoramos)
USUARIO = "admin"
PASSWORD = "1234"

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["password"]

        if user == USUARIO and password == PASSWORD:
            session["logueado"] = True
            return redirect("/")
        else:
            return "Usuario o contraseña incorrectos"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


def requiere_login():
    return "logueado" in session

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
    if not requiere_login():
        return redirect("/login")
    return render_template("index.html")


@app.route("/calcular", methods=["POST"])
def calcular():
    if not requiere_login():
        return redirect("/login")

    reparticion = request.form["reparticion"]
    monto = int(request.form["monto"])
    cuotas = int(request.form["cuotas"])

    cuota_social, medico, farmacia = calcular_membresia(reparticion, monto)
    valor_cuota = calcular_cuota(monto, cuotas)

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