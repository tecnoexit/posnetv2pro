# -*- coding: utf-8 -*-
"""Verificacion rapida tras desplegar en un dispositivo."""
import json
import sqlite3
import urllib.request

BASE = "http://127.0.0.1:8080"


def getjson(path):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=10).read().decode())


print("ratios:", getjson("/api/ratios"))
print("categorias:", getjson("/api/categorias"))
print("buscar 7790000000012:", getjson("/api/buscar?q=7790000000012"))

db = sqlite3.connect("/opt/pos/data/pos.db")
db.row_factory = sqlite3.Row
print("productos:")
for r in db.execute("SELECT id,codigo,nombre,costo,precio,categoria,stock FROM productos WHERE activo=1"):
    print("  ", dict(r))
print("facturas:")
for r in db.execute("SELECT id,fecha,total,estado FROM ventas"):
    print("  ", dict(r))
print("VERIFY_OK")
