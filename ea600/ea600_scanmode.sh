#!/system/bin/sh
# Pone el escaner Urovo en modo TECLADO (teclea el codigo en el campo enfocado)
# usa la app demo urovoscan: cambia su preferencia y la abre para que aplique el modo
BB=/data/local/tmp/busybox
PREF=/data/data/com.example.urovoscan/shared_prefs/com.example.urovoscan_preferences.xml
set -x
if [ ! -f "$PREF" ]; then echo NO_HAY_PREF; exit 1; fi
$BB sed 's/name="scanner_keyboard_output" value="false"/name="scanner_keyboard_output" value="true"/' $PREF > $PREF.n
$BB mv $PREF.n $PREF
$BB chown 10076:10076 $PREF 2>/dev/null
$BB chmod 660 $PREF 2>/dev/null
am force-stop com.example.urovoscan
am start --user 0 -n com.example.urovoscan/.MainActivity
sleep 4
am force-stop com.example.urovoscan
echo MODO_TECLADO_APLICADO
