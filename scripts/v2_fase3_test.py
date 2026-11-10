# -*- coding: utf-8 -*-
"""Prueba Fase 3: ratios de moneda + categorias CRUD."""
import json
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8080"


def post(path, data=None):
    body = urllib.parse.urlencode(data or {}).encode()
    req = urllib.request.Request(BASE + path, data=body)
    try:
        return urllib.request.urlopen(req, timeout=10).status
    except urllib.error.HTTPError as e:
        return e.code


def getjson(path):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=10).read().decode())


db = sqlite3.connect("/opt/pos/data/pos.db")
db.row_factory = sqlite3.Row

# limpieza de corridas anteriores
db.execute("UPDATE productos SET ratio_id=NULL WHERE ratio_id IN (SELECT id FROM ratios WHERE nombre='Mayorista')")
db.execute("DELETE FROM ratios WHERE nombre='Mayorista'")
db.execute("UPDATE productos SET activo=0 WHERE nombre='Producto Prueba Ratio'")
db.execute("DELETE FROM categorias WHERE nombre='PruebaCat'")
db.commit()

print("1. ratios iniciales (migracion desde % de venta):", getjson("/api/ratios"))

post("/ratios", {"nombre": "Mayorista", "valor": "1,5"})
rats = getjson("/api/ratios")
print("2. tras crear ratio Mayorista:", rats)
rid = [r["id"] for r in rats if r["nombre"] == "Mayorista"][0]

post("/categorias", {"nombre": "PruebaCat"})
print("3. categorias:", getjson("/api/categorias"))

post("/productos/nuevo", {
    "nombre": "Producto Prueba Ratio", "costo": "1000",
    "ratio_id": str(rid), "categoria": "PruebaCat",
    "stock": "0", "stock_min": "0"})

p = db.execute("SELECT * FROM productos WHERE nombre='Producto Prueba Ratio' AND activo=1").fetchone()
print("4. producto nuevo:", dict(p))
assert p is not None and abs(p["precio"] - 1500) < 0.01, "esperaba precio 1500 (1000 x 1,5)"

post("/ratios/%d/editar" % rid, {"nombre": "Mayorista", "valor": "1,6"})
post("/ratios/%d/recalcular" % rid)
p = db.execute("SELECT * FROM productos WHERE id=?", (p["id"],)).fetchone()
print("5. tras editar ratio a 1,6 y recalcular: precio =", p["precio"])
assert abs(p["precio"] - 1600) < 0.01, "esperaba precio 1600"

# limpieza final
post("/productos/%d/eliminar" % p["id"])
post("/ratios/%d/eliminar" % rid)
cat = db.execute("SELECT id FROM categorias WHERE nombre='PruebaCat'").fetchone()
if cat:
    post("/categorias/%d/eliminar" % cat["id"])

print("6. ratios finales:", getjson("/api/ratios"))
print("7. categorias finales:", getjson("/api/categorias"))
prods = db.execute("SELECT nombre,precio FROM productos WHERE activo=1 ORDER BY nombre").fetchall()
print("8. productos intactos:", [(r["nombre"], r["precio"]) for r in prods])
print("TEST_F3_OK")
