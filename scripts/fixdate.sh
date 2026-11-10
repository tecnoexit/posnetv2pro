#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PATH
export PROOT_NO_SECCOMP=1

echo "########## CORRIGIENDO ticket-demo (bug de la fecha) ##########"

linux-run 'cat > /usr/local/bin/ticket-demo << "XEOF"
#!/bin/bash
# Genera e imprime un ticket ESC/POS de demostracion en la impresora interna.
export PATH=/usr/local/bin:$PATH
F=/tmp/ticket_demo.bin
: > "$F"

emit() { printf "%b" "$1" >> "$F"; }

FECHA=$(date +%d/%m/%Y)
HORA=$(date +%H:%M)

emit "\x1B\x40"              # ESC @  -> inicializar impresora
emit "\x1B\x61\x01"          # ESC a 1 -> centrado
emit "\x1B\x45\x01"          # ESC E 1 -> negrita ON
emit "SUNMI V2 PRO\n"
emit "Debian Linux + RawBT\n"
emit "\x1B\x45\x00"          # ESC E 0 -> negrita OFF
emit "========================\n"
emit "\x1B\x61\x00"          # ESC a 0 -> izquierda
emit "TICKET DE PRUEBA\n"
printf "%s\n" "Fecha: $FECHA  $HORA" >> "$F"
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
echo "########## VERIFICACION ##########"
linux-run 'bash -n /usr/local/bin/ticket-demo && echo "sintaxis OK"'
echo "--- contenido generado de prueba ---"
linux-run 'F=/tmp/chk.bin; : > $F; FECHA=$(date +%d/%m/%Y); HORA=$(date +%H:%M); printf "%s\n" "Fecha: $FECHA  $HORA" >> $F; cat $F'

echo ""
echo "########## Estado de RawBT ##########"
linux-run 'export PATH=/system/bin:$PATH; dumpsys activity activities 2>/dev/null | grep -E "mResumedActivity" | head -2'

echo "SCRIPT_FIXDATE_OK"
