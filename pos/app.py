# -*- coding: utf-8 -*-
"""
app.py - Punto de venta LOCAL para SUNMI V2 Pro.
Todo (base de datos, fotos, facturas) se guarda en el propio dispositivo.
Acceso: http://127.0.0.1:8080 desde Chrome.

Precio de venta = costo x ratio_moneda  (ej: costo 100, ratio 1,30 -> 130)
Los ratios y las categorias se administran desde la web (crear/editar/eliminar).
"""

import os
import csv
import io
import sqlite3
import time

from flask import (Flask, g, request, render_template, redirect,
                   url_for, jsonify, flash, send_from_directory)

import ticket as tk

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
FOTOS = os.path.join(DATA, "fotos")
DB = os.path.join(DATA, "pos.db")
os.makedirs(FOTOS, exist_ok=True)

app = Flask(__name__)
app.secret_key = "pos-local-sunmi-v2pro"
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True


# ============================ base de datos ============================

SCHEMA = """
CREATE TABLE IF NOT EXISTS config(
  clave TEXT PRIMARY KEY, valor TEXT);

CREATE TABLE IF NOT EXISTS categorias(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT UNIQUE NOT NULL);

CREATE TABLE IF NOT EXISTS ratios(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  valor REAL NOT NULL DEFAULT 1.3);

CREATE TABLE IF NOT EXISTS productos(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo TEXT UNIQUE,
  nombre TEXT NOT NULL,
  precio REAL NOT NULL DEFAULT 0,
  costo REAL NOT NULL DEFAULT 0,
  categoria TEXT DEFAULT '',
  ratio_id INTEGER REFERENCES ratios(id) ON DELETE SET NULL,
  stock REAL NOT NULL DEFAULT 0,
  stock_min REAL NOT NULL DEFAULT 0,
  foto TEXT,
  activo INTEGER NOT NULL DEFAULT 1);

CREATE TABLE IF NOT EXISTS ventas(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fecha TEXT NOT NULL,
  total REAL NOT NULL DEFAULT 0,
  pago TEXT DEFAULT 'efectivo',
  estado TEXT DEFAULT 'completada',
  notas TEXT DEFAULT '');

CREATE TABLE IF NOT EXISTS venta_items(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  venta_id INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
  producto_id INTEGER REFERENCES productos(id),
  descripcion TEXT NOT NULL,
  cantidad REAL NOT NULL,
  precio REAL NOT NULL,
  subtotal REAL NOT NULL);
"""

MIGRACIONES = [
    ("productos", "costo", "ALTER TABLE productos ADD COLUMN costo REAL NOT NULL DEFAULT 0"),
    ("productos", "categoria", "ALTER TABLE productos ADD COLUMN categoria TEXT DEFAULT ''"),
    ("productos", "ratio_id", "ALTER TABLE productos ADD COLUMN ratio_id INTEGER"),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    # migraciones para bases creadas con versiones anteriores
    for tabla, columna, sql in MIGRACIONES:
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({tabla})")]
        if columna not in cols:
            db.execute(sql)
    if db.execute("SELECT 1 FROM config LIMIT 1").fetchone() is None:
        db.executemany("INSERT OR REPLACE INTO config(clave,valor) VALUES(?,?)", [
            ("nombre_negocio", "MI COMERCIO"),
            ("direccion", ""),
            ("pie_ticket", "Gracias por su compra"),
            ("moneda", "$"),
            ("codificacion", "ascii"),
        ])
    # migrar el viejo porcentaje_venta al primer ratio_moneda
    if db.execute("SELECT 1 FROM ratios LIMIT 1").fetchone() is None:
        r = db.execute("SELECT valor FROM config WHERE clave='porcentaje_venta'").fetchone()
        pct = 30.0
        if r and r["valor"]:
            try:
                pct = float(str(r["valor"]).replace(",", "."))
            except ValueError:
                pct = 30.0
        db.execute("INSERT INTO ratios(nombre,valor) VALUES('General',?)",
                   (round(1 + pct / 100.0, 4),))
    # categorias: incorporar las que ya esten escritas en productos
    for r in db.execute("SELECT DISTINCT categoria FROM productos WHERE categoria != ''"):
        db.execute("INSERT OR IGNORE INTO categorias(nombre) VALUES(?)", (r["categoria"],))
    db.commit()
    db.close()


def cfg_todas(db):
    return {r["clave"]: r["valor"] for r in db.execute("SELECT clave,valor FROM config")}


def cfg(db, clave, default=""):
    r = db.execute("SELECT valor FROM config WHERE clave=?", (clave,)).fetchone()
    return r["valor"] if r and r["valor"] is not None else default


def fmt_dinero(v, db=None):
    if db is None:
        try:
            db = get_db()
        except RuntimeError:
            db = None
    mon = cfg(db, "moneda", "$") if db is not None else "$"
    return tk.dinero(v, mon)


app.jinja_env.globals["dinero"] = fmt_dinero


def num(s, default=0.0):
    """Convierte '1.234,56' o '1234.56' en float."""
    if s is None:
        return default
    s = str(s).strip().replace(" ", "")
    if not s:
        return default
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return default


# ---------------------------- ratios moneda ----------------------------

def ratios_todos(db):
    return [dict(r) for r in db.execute("SELECT * FROM ratios ORDER BY nombre")]


def ratio_default(db):
    """Ratio usado cuando el producto no tiene uno propio."""
    rid = cfg(db, "ratio_default", "")
    if rid:
        r = db.execute("SELECT * FROM ratios WHERE id=?", (rid,)).fetchone()
        if r:
            return r
    return db.execute("SELECT * FROM ratios ORDER BY id LIMIT 1").fetchone()


def ratio_valor(db, ratio_id=None):
    """Valor multiplicador del ratio (ej 1.3)."""
    if ratio_id:
        r = db.execute("SELECT valor FROM ratios WHERE id=?", (ratio_id,)).fetchone()
        if r:
            return float(r["valor"])
    r = ratio_default(db)
    return float(r["valor"]) if r else 1.3


def precio_desde_costo(db, costo, ratio_id=None):
    return round(costo * ratio_valor(db, ratio_id), 2)


def categoria_registrar(db, nombre):
    """Alta automatica de una categoria usada por primera vez."""
    nombre = (nombre or "").strip()
    if nombre:
        db.execute("INSERT OR IGNORE INTO categorias(nombre) VALUES(?)", (nombre,))


def guardar_foto(file):
    """Comprime la foto a max 400px JPEG y la guarda. Devuelve el nombre."""
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("jpg", "jpeg", "png", "webp", "bmp"):
        return None
    try:
        from PIL import Image
        img = Image.open(file.stream)
        img = img.convert("RGB")
        img.thumbnail((400, 400))
        nombre = f"{int(time.time() * 1000)}.jpg"
        img.save(os.path.join(FOTOS, nombre), "JPEG", quality=82)
        return nombre
    except Exception:
        return None


def imprimir_venta(venta_id):
    db = get_db()
    v = db.execute("SELECT * FROM ventas WHERE id=?", (venta_id,)).fetchone()
    if not v:
        return False
    items = db.execute("SELECT * FROM venta_items WHERE venta_id=?", (venta_id,)).fetchall()
    datos = tk.construir_ticket(dict(v), [dict(i) for i in items], cfg_todas(db))
    ok, _ = tk.enviar_a_imprimir(datos, cfg_todas(db))
    return ok


# ============================ rutas ============================

@app.route("/")
def home():
    return redirect(url_for("venta"))


@app.route("/venta")
def venta():
    db = get_db()
    bajos = db.execute(
        "SELECT nombre,stock,stock_min FROM productos "
        "WHERE activo=1 AND stock <= stock_min ORDER BY nombre").fetchall()
    return render_template("venta.html", bajos=bajos)


@app.route("/api/buscar")
def api_buscar():
    q = request.args.get("q", "").strip()
    db = get_db()
    rows = []
    if q:
        like = f"%{q}%"
        rows = db.execute(
            "SELECT id,codigo,nombre,precio,costo,categoria,stock,foto FROM productos "
            "WHERE activo=1 AND (codigo = ? OR codigo LIKE ? OR nombre LIKE ? OR categoria LIKE ?) "
            "ORDER BY (codigo = ?) DESC, (codigo LIKE ?) DESC, nombre LIMIT 20",
            (q, q + "%", like, like, q, q + "%")).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/catalogo")
def catalogo():
    """Vidriera para el cliente: solo muestra productos y boton de WhatsApp."""
    db = get_db()
    rows = db.execute(
        "SELECT codigo,nombre,precio,categoria,foto FROM productos "
        "WHERE activo=1 ORDER BY categoria, nombre").fetchall()
    cats = sorted({r["categoria"] for r in rows if r["categoria"]})
    wa_msg = cfg(db, "whatsapp_mensaje", "") or "Hola! Quiero hacer un pedido:"
    return render_template("catalogo.html", productos=rows, cats=cats,
                           negocio=cfg(db, "nombre_negocio", ""),
                           wa=cfg(db, "whatsapp", ""), wa_msg=wa_msg)


@app.route("/api/categorias")
def api_categorias():
    db = get_db()
    rows = db.execute("SELECT nombre FROM categorias ORDER BY nombre").fetchall()
    return jsonify([r["nombre"] for r in rows])


@app.route("/api/ratios")
def api_ratios():
    db = get_db()
    return jsonify([dict(r) for r in ratios_todos(db)])


@app.route("/venta/cobrar", methods=["POST"])
def cobrar():
    data = request.get_json(force=True)
    items = data.get("items", [])
    if not items:
        return jsonify({"ok": False, "error": "El carrito esta vacio"}), 400
    db = get_db()
    pago = data.get("pago", "efectivo")
    imprimir = bool(data.get("imprimir", True))
    ahora = time.strftime("%Y-%m-%d %H:%M:%S")

    cur = db.execute(
        "INSERT INTO ventas(fecha,total,pago,estado) VALUES(?,?,?,?)",
        (ahora, 0, pago, "completada"))
    venta_id = cur.lastrowid

    total = 0.0
    for it in items:
        p = db.execute("SELECT * FROM productos WHERE id=?", (it.get("id"),)).fetchone()
        if not p:
            continue
        cant = float(it.get("cantidad", 1) or 1)
        precio = float(it.get("precio", p["precio"]) or 0)
        sub = round(cant * precio, 2)
        total += sub
        db.execute(
            "INSERT INTO venta_items(venta_id,producto_id,descripcion,cantidad,precio,subtotal) "
            "VALUES(?,?,?,?,?,?)",
            (venta_id, p["id"], p["nombre"], cant, precio, sub))
        db.execute("UPDATE productos SET stock = stock - ? WHERE id=?", (cant, p["id"]))

    db.execute("UPDATE ventas SET total=? WHERE id=?", (round(total, 2), venta_id))
    db.commit()

    impreso = imprimir_venta(venta_id) if imprimir else False
    return jsonify({"ok": True, "venta_id": venta_id, "impreso": impreso, "total": round(total, 2)})


# ---------- categorias ----------

@app.route("/categorias", methods=["GET", "POST"])
def categorias():
    db = get_db()
    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        if not nombre:
            flash("Escriba un nombre de categoria")
        else:
            try:
                db.execute("INSERT INTO categorias(nombre) VALUES(?)", (nombre,))
                db.commit()
                flash(f"Categoria '{nombre}' creada")
            except sqlite3.IntegrityError:
                flash("Esa categoria ya existe")
        return redirect(url_for("categorias"))
    filas = db.execute(
        "SELECT c.id, c.nombre, "
        "(SELECT COUNT(*) FROM productos p WHERE p.categoria = c.nombre AND p.activo=1) AS cuantos "
        "FROM categorias c ORDER BY c.nombre").fetchall()
    return render_template("categorias.html", cats=filas)


@app.route("/categorias/<int:cid>/editar", methods=["POST"])
def categoria_editar(cid):
    db = get_db()
    c = db.execute("SELECT * FROM categorias WHERE id=?", (cid,)).fetchone()
    if not c:
        return "Categoria no encontrada", 404
    nuevo = (request.form.get("nombre") or "").strip()
    if not nuevo:
        flash("El nombre no puede quedar vacio")
        return redirect(url_for("categorias"))
    try:
        db.execute("UPDATE categorias SET nombre=? WHERE id=?", (nuevo, cid))
        db.execute("UPDATE productos SET categoria=? WHERE categoria=?", (nuevo, c["nombre"]))
        db.commit()
        flash("Categoria renombrada")
    except sqlite3.IntegrityError:
        flash("Ya existe otra categoria con ese nombre")
    return redirect(url_for("categorias"))


@app.route("/categorias/<int:cid>/eliminar", methods=["POST"])
def categoria_eliminar(cid):
    db = get_db()
    c = db.execute("SELECT * FROM categorias WHERE id=?", (cid,)).fetchone()
    if not c:
        return "Categoria no encontrada", 404
    db.execute("DELETE FROM categorias WHERE id=?", (cid,))
    # los productos quedan sin categoria
    db.execute("UPDATE productos SET categoria='' WHERE categoria=?", (c["nombre"],))
    db.commit()
    flash(f"Categoria '{c['nombre']}' eliminada (los productos quedaron sin categoria)")
    return redirect(url_for("categorias"))


# ---------- ratios moneda ----------

@app.route("/ratios", methods=["GET", "POST"])
def ratios():
    db = get_db()
    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        valor = num(request.form.get("valor"), -1)
        if not nombre:
            flash("Escriba un nombre para el ratio")
        elif valor <= 0:
            flash("El valor del ratio debe ser mayor que 0 (ej: 1,30)")
        else:
            db.execute("INSERT INTO ratios(nombre,valor) VALUES(?,?)", (nombre, valor))
            db.commit()
            flash(f"Ratio '{nombre}' creado (costo x {valor})")
        return redirect(url_for("ratios"))
    filas = db.execute(
        "SELECT r.*, "
        "(SELECT COUNT(*) FROM productos p WHERE p.ratio_id = r.id AND p.activo=1) AS cuantos "
        "FROM ratios r ORDER BY r.nombre").fetchall()
    defecto = ratio_default(db)
    return render_template("ratios.html", ratios=filas,
                           defecto_id=defecto["id"] if defecto else None)


@app.route("/ratios/<int:rid>/editar", methods=["POST"])
def ratio_editar(rid):
    db = get_db()
    r = db.execute("SELECT * FROM ratios WHERE id=?", (rid,)).fetchone()
    if not r:
        return "Ratio no encontrado", 404
    nombre = (request.form.get("nombre") or "").strip() or r["nombre"]
    valor = num(request.form.get("valor"), -1)
    if valor <= 0:
        flash("El valor del ratio debe ser mayor que 0")
        return redirect(url_for("ratios"))
    db.execute("UPDATE ratios SET nombre=?, valor=? WHERE id=?", (nombre, valor, rid))
    db.commit()
    flash(f"Ratio '{nombre}' actualizado (costo x {valor})")
    return redirect(url_for("ratios"))


@app.route("/ratios/<int:rid>/eliminar", methods=["POST"])
def ratio_eliminar(rid):
    db = get_db()
    r = db.execute("SELECT * FROM ratios WHERE id=?", (rid,)).fetchone()
    if not r:
        return "Ratio no encontrado", 404
    cuantos = db.execute(
        "SELECT COUNT(*) n FROM productos WHERE ratio_id=? AND activo=1", (rid,)).fetchone()["n"]
    db.execute("DELETE FROM ratios WHERE id=?", (rid,))
    db.commit()
    msg = f"Ratio '{r['nombre']}' eliminado"
    if cuantos:
        msg += f" ({cuantos} productos pasan al ratio por defecto)"
    flash(msg)
    return redirect(url_for("ratios"))


@app.route("/ratios/<int:rid>/recalcular", methods=["POST"])
def ratio_recalcular(rid):
    """Recalcula el precio de los productos de este ratio: precio = costo x ratio."""
    db = get_db()
    r = db.execute("SELECT * FROM ratios WHERE id=?", (rid,)).fetchone()
    if not r:
        return "Ratio no encontrado", 404
    cur = db.execute(
        "UPDATE productos SET precio = ROUND(costo * ?, 2) "
        "WHERE ratio_id=? AND activo=1 AND costo > 0", (r["valor"], rid))
    db.commit()
    flash(f"Precios recalculados con ratio '{r['nombre']}' (x{r['valor']}): {cur.rowcount} productos")
    return redirect(url_for("ratios"))


@app.route("/ratios/<int:rid>/defecto", methods=["POST"])
def ratio_defecto(rid):
    db = get_db()
    if not db.execute("SELECT 1 FROM ratios WHERE id=?", (rid,)).fetchone():
        return "Ratio no encontrado", 404
    db.execute("INSERT OR REPLACE INTO config(clave,valor) VALUES('ratio_default',?)", (str(rid),))
    db.commit()
    flash("Ratio por defecto actualizado")
    return redirect(url_for("ratios"))


# ---------- productos ----------

@app.route("/productos")
def productos():
    db = get_db()
    q = request.args.get("q", "").strip()
    cat = request.args.get("cat", "").strip()
    cats = [r["nombre"] for r in db.execute("SELECT nombre FROM categorias ORDER BY nombre")]
    sql = "SELECT * FROM productos WHERE activo=1"
    params = []
    if q:
        sql += " AND (codigo LIKE ? OR nombre LIKE ? OR categoria LIKE ?)"
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if cat:
        sql += " AND categoria = ?"
        params.append(cat)
    sql += " ORDER BY categoria, nombre"
    rows = db.execute(sql, params).fetchall()
    return render_template("productos.html", productos=rows, q=q, cat=cat, cats=cats)


@app.route("/productos/nuevo", methods=["GET", "POST"])
def producto_nuevo():
    db = get_db()
    if request.method == "POST":
        return producto_guardar(db, None)
    return render_template("producto_form.html", producto=None,
                           ratios=ratios_todos(db), cats=cats_lista(db),
                           defecto=ratio_default(db))


@app.route("/productos/<int:pid>", methods=["GET", "POST"])
def producto_editar(pid):
    db = get_db()
    p = db.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
    if not p:
        return "Producto no encontrado", 404
    if request.method == "POST":
        return producto_guardar(db, p)
    return render_template("producto_form.html", producto=p,
                           ratios=ratios_todos(db), cats=cats_lista(db),
                           defecto=ratio_default(db))


def cats_lista(db):
    return [r["nombre"] for r in db.execute("SELECT nombre FROM categorias ORDER BY nombre")]


def producto_guardar(db, p):
    """Guarda alta (p=None) o edicion de producto desde el formulario."""
    codigo = (request.form.get("codigo") or "").strip() or None
    nombre = (request.form.get("nombre") or "").strip()
    categoria = (request.form.get("categoria") or "").strip()
    ratio_id = request.form.get("ratio_id") or None
    ratios = ratios_todos(db)
    cats = cats_lista(db)
    defecto = ratio_default(db)

    if not nombre:
        flash("El nombre es obligatorio")
        return render_template("producto_form.html", producto=p,
                               ratios=ratios, cats=cats, defecto=defecto)

    try:
        ratio_id = int(ratio_id) if ratio_id else None
    except ValueError:
        ratio_id = None

    costo = num(request.form.get("costo"))
    precio = num(request.form.get("precio"), -1)
    if precio < 0:
        precio = precio_desde_costo(db, costo, ratio_id)
    stock = num(request.form.get("stock"))
    stock_min = num(request.form.get("stock_min"))
    foto = guardar_foto(request.files.get("foto"))
    if not foto and p:
        foto = p["foto"]

    categoria_registrar(db, categoria)
    try:
        if p:
            db.execute(
                "UPDATE productos SET codigo=?,nombre=?,precio=?,costo=?,categoria=?,"
                "ratio_id=?,stock=?,stock_min=?,foto=? WHERE id=?",
                (codigo, nombre, precio, costo, categoria, ratio_id,
                 stock, stock_min, foto, p["id"]))
            msg = f"Producto '{nombre}' actualizado"
        else:
            db.execute(
                "INSERT INTO productos(codigo,nombre,precio,costo,categoria,ratio_id,"
                "stock,stock_min,foto) VALUES(?,?,?,?,?,?,?,?,?)",
                (codigo, nombre, precio, costo, categoria, ratio_id,
                 stock, stock_min, foto))
            msg = f"Producto '{nombre}' guardado"
        db.commit()
    except sqlite3.IntegrityError:
        flash("Ese codigo ya existe en otro producto")
        return render_template("producto_form.html", producto=p,
                               ratios=ratios, cats=cats, defecto=defecto)
    flash(msg)
    return redirect(url_for("productos"))


@app.route("/productos/<int:pid>/eliminar", methods=["POST"])
def producto_eliminar(pid):
    db = get_db()
    db.execute("UPDATE productos SET activo=0 WHERE id=?", (pid,))
    db.commit()
    flash("Producto eliminado")
    return redirect(url_for("productos"))


@app.route("/productos/importar", methods=["GET", "POST"])
def productos_importar():
    db = get_db()
    ratios = ratios_todos(db)
    defecto = ratio_default(db)
    if request.method != "POST":
        return render_template("importar.html", ratios=ratios, defecto=defecto)

    file = request.files.get("archivo")
    if not file or not file.filename:
        flash("Seleccione un archivo CSV")
        return redirect(url_for("productos_importar"))
    raw = file.stream.read()
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texto = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        texto = raw.decode("utf-8", "replace")

    lineas = [l for l in texto.splitlines() if l.strip()]
    if not lineas:
        flash("El archivo esta vacio")
        return redirect(url_for("productos_importar"))

    # ratio elegido en el formulario (para filas sin precio ni ratio propio)
    rid_form = request.form.get("ratio_id") or None
    try:
        rid_form = int(rid_form) if rid_form else None
    except ValueError:
        rid_form = None
    valor_form = ratio_valor(db, rid_form)

    # detectar separador (; , tab) por la primera linea
    primera = lineas[0]
    sep = max([";", ",", "\t"], key=lambda s: primera.count(s))
    if primera.count(sep) == 0:
        flash("No se reconoce el formato. Se esperan columnas: codigo;nombre;costo")
        return redirect(url_for("productos_importar"))

    reader = csv.reader(io.StringIO(texto), delimiter=sep)
    filas = list(reader)
    # saltear encabezado si lo tiene
    if filas and any("codigo" in (c or "").lower() or "nombre" in (c or "").lower()
                     for c in filas[0]):
        filas = filas[1:]

    creados, actualizados, errores = 0, 0, []
    for i, fila in enumerate(filas, start=1):
        if not fila or not any(c.strip() for c in fila):
            continue
        # columnas: codigo;nombre;costo[;precio][;stock][;categoria][;ratio]
        codigo = (fila[0] if len(fila) > 0 else "").strip() or None
        nombre = (fila[1] if len(fila) > 1 else "").strip()
        costo = num(fila[2] if len(fila) > 2 else 0)
        precio = num(fila[3], -1) if len(fila) > 3 and str(fila[3]).strip() else -1
        stock = num(fila[4]) if len(fila) > 4 else 0
        categoria = (fila[5] if len(fila) > 5 else "").strip()
        ratio_col = (fila[6] if len(fila) > 6 else "").strip()
        if not nombre:
            errores.append(f"fila {i}: sin nombre")
            continue

        # ratio propio de la fila: por nombre de ratio o por numero
        fila_rid, fila_valor = rid_form, valor_form
        if ratio_col:
            r = db.execute("SELECT * FROM ratios WHERE nombre = ?", (ratio_col,)).fetchone()
            if r:
                fila_rid, fila_valor = r["id"], float(r["valor"])
            else:
                v = num(ratio_col, -1)
                if v > 0:
                    fila_valor = v
        if precio < 0:
            precio = round(costo * fila_valor, 2)

        categoria_registrar(db, categoria)
        ex = db.execute("SELECT id FROM productos WHERE codigo=? AND codigo IS NOT NULL",
                        (codigo,)).fetchone() if codigo else None
        try:
            if ex:
                db.execute(
                    "UPDATE productos SET nombre=?,precio=?,costo=?,categoria=?,ratio_id=?,stock=? "
                    "WHERE id=?",
                    (nombre, precio, costo, categoria, fila_rid, stock, ex["id"]))
                actualizados += 1
            else:
                db.execute(
                    "INSERT INTO productos(codigo,nombre,precio,costo,categoria,ratio_id,stock) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (codigo, nombre, precio, costo, categoria, fila_rid, stock))
                creados += 1
        except sqlite3.IntegrityError:
            errores.append(f"fila {i}: codigo repetido ({codigo})")

    db.commit()
    flash(f"Importacion: {creados} creados, {actualizados} actualizados"
          + (f", {len(errores)} con errores" if errores else ""))
    for e in errores[:10]:
        flash(e)
    return redirect(url_for("productos"))


@app.route("/foto/<path:nombre>")
def foto(nombre):
    return send_from_directory(FOTOS, nombre)


# ---------- facturas ----------

@app.route("/facturas")
def facturas():
    db = get_db()
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    sql = "SELECT * FROM ventas"
    params = []
    conds = []
    if desde:
        conds.append("fecha >= ?")
        params.append(desde + " 00:00:00")
    if hasta:
        conds.append("fecha <= ?")
        params.append(hasta + " 23:59:59")
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY id DESC LIMIT 200"
    rows = db.execute(sql, params).fetchall()
    return render_template("facturas.html", ventas=rows, desde=desde, hasta=hasta)


@app.route("/facturas/<int:vid>")
def factura_detalle(vid):
    db = get_db()
    v = db.execute("SELECT * FROM ventas WHERE id=?", (vid,)).fetchone()
    if not v:
        return "Factura no encontrada", 404
    items = db.execute("SELECT * FROM venta_items WHERE venta_id=?", (vid,)).fetchall()
    return render_template("factura_detalle.html", venta=v, items=items)


@app.route("/facturas/<int:vid>/imprimir", methods=["POST"])
def factura_imprimir(vid):
    ok = imprimir_venta(vid)
    flash("Ticket enviado a la impresora" if ok else "No se pudo imprimir (revise Config: impresora)")
    return redirect(url_for("factura_detalle", vid=vid))


@app.route("/facturas/<int:vid>/editar", methods=["POST"])
def factura_editar(vid):
    db = get_db()
    v = db.execute("SELECT * FROM ventas WHERE id=?", (vid,)).fetchone()
    if not v:
        return "Factura no encontrada", 404
    items = db.execute("SELECT * FROM venta_items WHERE venta_id=?", (vid,)).fetchall()
    cantidades = request.form.getlist("cantidad")
    precios = request.form.getlist("precio")

    total = 0.0
    for i, it in enumerate(items):
        try:
            nueva_cant = num(cantidades[i])
            nuevo_precio = num(precios[i])
        except (ValueError, IndexError):
            nueva_cant = it["cantidad"]
            nuevo_precio = it["precio"]
        if nueva_cant <= 0:
            # quitar linea: devolver stock
            if it["producto_id"]:
                db.execute("UPDATE productos SET stock = stock + ? WHERE id=?",
                           (it["cantidad"], it["producto_id"]))
            db.execute("DELETE FROM venta_items WHERE id=?", (it["id"],))
            continue
        # ajustar stock por diferencia
        if it["producto_id"]:
            delta = it["cantidad"] - nueva_cant
            if delta:
                db.execute("UPDATE productos SET stock = stock + ? WHERE id=?",
                           (delta, it["producto_id"]))
        sub = round(nueva_cant * nuevo_precio, 2)
        total += sub
        db.execute("UPDATE venta_items SET cantidad=?,precio=?,subtotal=? WHERE id=?",
                   (nueva_cant, nuevo_precio, sub, it["id"]))

    notas = (request.form.get("notas") or "").strip()
    db.execute("UPDATE ventas SET total=?, notas=? WHERE id=?", (round(total, 2), notas, vid))
    db.commit()
    flash("Factura actualizada")
    return redirect(url_for("factura_detalle", vid=vid))


@app.route("/facturas/<int:vid>/anular", methods=["POST"])
def factura_anular(vid):
    db = get_db()
    v = db.execute("SELECT * FROM ventas WHERE id=?", (vid,)).fetchone()
    if not v:
        return "Factura no encontrada", 404
    if v["estado"] == "completada":
        items = db.execute("SELECT * FROM venta_items WHERE venta_id=?", (vid,)).fetchall()
        for it in items:
            if it["producto_id"]:
                db.execute("UPDATE productos SET stock = stock + ? WHERE id=?",
                           (it["cantidad"], it["producto_id"]))
        db.execute("UPDATE ventas SET estado='anulada' WHERE id=?", (vid,))
        db.commit()
        flash("Factura anulada y stock devuelto")
    return redirect(url_for("factura_detalle", vid=vid))


# ---------- configuracion ----------

@app.route("/config", methods=["GET", "POST"])
def config():
    db = get_db()
    if request.method == "POST":
        for campo in ("nombre_negocio", "direccion", "pie_ticket", "moneda", "codificacion",
                      "whatsapp", "whatsapp_mensaje", "impresora_red"):
            db.execute("INSERT OR REPLACE INTO config(clave,valor) VALUES(?,?)",
                       (campo, request.form.get(campo, "")))
        db.commit()
        flash("Configuracion guardada")
        return redirect(url_for("config"))
    return render_template("config.html", cfg=cfg_todas(db),
                           defecto=ratio_default(db))


@app.route("/config/test", methods=["POST"])
def config_test():
    db = get_db()
    datos = tk.ticket_prueba(cfg_todas(db))
    ok, msg = tk.enviar_a_imprimir(datos, cfg_todas(db))
    flash("Ticket de prueba enviado" if ok else "Fallo al imprimir: " + msg)
    return redirect(url_for("config"))


# ============================ arranque ============================

if __name__ == "__main__":
    init_db()
    print("Punto de venta en http://127.0.0.1:8080")
    app.run(host="0.0.0.0", port=8080, threaded=True)
