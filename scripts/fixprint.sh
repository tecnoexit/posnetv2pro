#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PATH
export PROOT_NO_SECCOMP=1

echo "########## REINSTALANDO COMANDOS DE IMPRESION (corregidos) ##########"

linux-run 'cat > /usr/local/bin/imprimir << "XEOF"
#!/bin/bash
# Imprime datos ESC/POS crudos en la impresora termica interna del SUNMI.
# Requiere la app RawBT (ya instalada) configurada con la impresora interna.
#
# Uso:
#   imprimir archivo.bin          imprime un fichero de bytes ESC/POS
#   cat datos.bin | imprimir -    imprime desde stdin
#   imprimir --texto "hola"       imprime texto simple
#   imprimir --demo               imprime un ticket de ejemplo

GB64=/usr/bin/base64

if [ "$1" = "--texto" ]; then
  shift
  printf "%s\n" "$*" > /tmp/.imp_txt
  B64=$($GB64 -w0 /tmp/.imp_txt)
elif [ "$1" = "--demo" ]; then
  ticket-demo
  exit $?
elif [ "$1" = "-" ] || [ -z "$1" ]; then
  B64=$($GB64 -w0)
else
  [ -f "$1" ] || { echo "No existe: $1" >&2; exit 1; }
  B64=$($GB64 -w0 "$1")
fi

[ -n "$B64" ] || { echo "No hay datos que imprimir" >&2; exit 1; }

OUT=$(/system/bin/am start --user 0 -a android.intent.action.VIEW -d "rawbt:base64,${B64}" 2>&1)
if echo "$OUT" | grep -qi "unable to resolve\|Exception\|Error"; then
  echo "ERROR: no se pudo enviar a RawBT." >&2
  echo "$OUT" >&2
  exit 1
fi
echo "OK: enviado a la impresora interna."
XEOF
chmod 755 /usr/local/bin/imprimir'

linux-run 'cat > /usr/local/bin/ticket-demo << "XEOF"
#!/bin/bash
# Genera e imprime un ticket ESC/POS de demostracion en la impresora interna.
export PATH=/usr/local/bin:$PATH
F=/tmp/ticket_demo.bin
: > "$F"

emit() { printf "%b" "$1" >> "$F"; }

emit "\x1B\x40"              # ESC @  -> inicializar impresora
emit "\x1B\x61\x01"          # ESC a 1 -> centrado
emit "\x1B\x45\x01"          # ESC E 1 -> negrita ON
emit "SUNMI V2 PRO\n"
emit "Debian Linux + RawBT\n"
emit "\x1B\x45\x00"          # ESC E 0 -> negrita OFF
emit "========================\n"
emit "\x1B\x61\x00"          # ESC a 0 -> izquierda
emit "TICKET DE PRUEBA\n"
printf "%s\n" "Fecha: $(date '+%d/%m/%Y %H:%M')" >> "$F"
emit "------------------------\n"
emit "Articulo 1        10.00\n"
emit "Articulo 2        25.50\n"
emit "------------------------\n"
emit "\x1B\x45\x01TOTAL       35.50\x1B\x45\x00\n"
emit "========================\n"
emit "\x1B\x61\x01Gracias por su compra\n\n\n"
emit "\x1D\x56\x00"          # GS V 0 -> corte de papel

imprimir "$F"
XEOF
chmod 755 /usr/local/bin/ticket-demo'

echo ""
echo "########## COMPROBACION DE SINTAXIS ##########"
linux-run 'bash -n /usr/local/bin/imprimir && echo "imprimir: sintaxis OK"; bash -n /usr/local/bin/ticket-demo && echo "ticket-demo: sintaxis OK"'

echo ""
echo "########## TEST: imprimir texto simple ##########"
linux-run 'export PATH=/usr/local/bin:$PATH; imprimir --texto "Hola desde Debian en el SUNMI V2 Pro" 2>&1'

sleep 4

echo ""
echo "########## TEST: ticket-demo ##########"
linux-run 'export PATH=/usr/local/bin:$PATH; ticket-demo 2>&1'

sleep 5

echo ""
echo "########## ¿Que actividad quedo en primer plano? ##########"
linux-run 'export PATH=/system/bin:$PATH; dumpsys activity activities 2>/dev/null | grep -E "mResumedActivity|mFocusedActivity" | head -3'

echo "SCRIPT_FIX_OK"
