# -*- coding: utf-8 -*-
"""
ticket.py - Generacion de tickets ESC/POS para la impresora termica 58mm
del SUNMI V2 Pro (via RawBT). Todo el dato se genera localmente.
"""

import os
import subprocess
import time
import unicodedata

ANCHO = 32  # caracteres por linea en 58mm (fuente A)


# ---------- codificacion ----------
def _enc(s, codif="ascii"):
    if not isinstance(s, str):
        s = str(s)
    if codif == "utf8":
        return s.encode("utf-8", "replace")
    if codif == "cp850":
        return s.encode("cp850", "replace")
    # ascii: translitera acentos (á -> a)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.encode("ascii", "replace")


# ---------- comandos ESC/POS ----------
def init():            return b"\x1b\x40"
def align(n):          return b"\x1b\x61" + bytes([n])
def bold(n):           return b"\x1b\x45" + bytes([n])
def underline(n):      return b"\x1b\x2d" + bytes([n])
def size(w=1, h=1):    return b"\x1d\x21" + bytes([((w - 1) & 15) | (((h - 1) & 15) << 4)])
def feed(n=1):         return b"\x1b\x64" + bytes([n])
def cut(mode=0):       return b"\x1d\x56" + bytes([mode])
def codepage(n):       return b"\x1b\x74" + bytes([n])


def linea(s, codif="ascii"):
    return _enc(s, codif) + b"\n"


def cols(izq, der, width=ANCHO, codif="ascii"):
    """Dos columnas: texto a la izquierda y a la derecha."""
    izq = str(izq)[:width]
    der = str(der)
    pad = width - len(izq) - len(der)
    if pad < 1:
        pad = 1
    return _enc(izq + " " * pad + der, codif) + b"\n"


def regla(c="=", width=ANCHO, codif="ascii"):
    return linea(c * width, codif)


def centrado(s, codif="ascii"):
    s = str(s)[:ANCHO]
    pad = (ANCHO - len(s)) // 2
    if pad < 0:
        pad = 0
    return linea(" " * pad + s, codif)


def dinero(v, mon="$"):
    s = f"{float(v):.2f}".replace(".", ",")
    return f"{mon} {s}"


# ---------- construccion del ticket ----------
def construir_ticket(venta, items, config):
    """
    venta: dict con id, fecha, total, pago, estado, notas
    items: lista de dict con descripcion, cantidad, precio, subtotal
    config: dict con nombre_negocio, direccion, pie_ticket, moneda, codificacion
    """
    codif = config.get("codificacion", "ascii")
    mon = config.get("moneda", "$")
    out = bytearray()

    out += init()
    # cabecera
    out += align(1)
    out += size(2, 2)
    out += centrado(config.get("nombre_negocio", "MI COMERCIO"), codif)
    out += size(1, 1)
    if config.get("direccion"):
        out += centrado(config["direccion"], codif)
    out += regla("-", codif=codif)

    # datos del ticket
    out += align(0)
    try:
        fecha = time.strftime("%d/%m/%Y %H:%M", time.strptime(venta["fecha"], "%Y-%m-%d %H:%M:%S"))
    except Exception:
        fecha = venta["fecha"]
    out += cols(f"Ticket #{int(venta['id']):06d}", fecha, codif=codif)
    if venta.get("estado") == "anulada":
        out += bold(1)
        out += centrado("*** ANULADA ***", codif)
        out += bold(0)
    out += regla("-", codif=codif)

    # articulos
    for it in items:
        cant = it["cantidad"]
        nombre = it["descripcion"][:20]
        izq = f"{cant:g} x {nombre}"
        der = dinero(it["subtotal"], mon)
        out += cols(izq, der, codif=codif)
    out += regla("-", codif=codif)

    # total
    out += bold(1)
    out += size(1, 2)
    out += cols("TOTAL", dinero(venta["total"], mon), codif=codif)
    out += size(1, 1)
    out += bold(0)
    out += cols(f"Pago: {venta.get('pago', 'efectivo')}", "", codif=codif)
    if venta.get("notas"):
        out += linea(venta["notas"], codif)
    out += regla("=", codif=codif)

    # pie
    out += align(1)
    out += linea(config.get("pie_ticket", "Gracias por su compra"), codif)
    out += feed(2)
    out += cut(0)

    return bytes(out)


def ticket_prueba(config):
    """Ticket de prueba para verificar codificacion y formato."""
    venta = {"id": 0, "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
             "total": 1234.5, "pago": "efectivo", "estado": "completada",
             "notas": ""}
    items = [
        {"descripcion": "Acentos: aeiou n N", "cantidad": 1, "precio": 10, "subtotal": 10},
        {"descripcion": "Cafe con leche", "cantidad": 2, "precio": 1500, "subtotal": 3000},
        {"descripcion": "Pan artesano", "cantidad": 1, "precio": 1234.5, "subtotal": 1234.5},
    ]
    datos = construir_ticket(venta, items, config)
    return datos.replace(b"\x1b\x40", b"\x1b\x40" + b"PRUEBA DE IMPRESION\n")


def enviar_a_imprimir(datos):
    """Escribe el ticket y lo envia al comando imprimir (RawBT)."""
    ruta = f"/tmp/ticket_{int(time.time()*1000)}.bin"
    with open(ruta, "wb") as f:
        f.write(datos)
    env = dict(os.environ)
    env["PATH"] = "/system/bin:/system/xbin:" + env.get("PATH", "")
    try:
        r = subprocess.run(["/usr/local/bin/imprimir", ruta],
                           capture_output=True, text=True, timeout=30, env=env)
        ok = "OK" in (r.stdout or "")
        return ok, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return False, str(e)
