#!/system/bin/sh
# EA600 - arreglo definitivo v2: runner interno del chroot + setsid
BB=/data/local/tmp/busybox
ROOT=/data/local/alpine
date > /data/local/tmp/last_run

# 1) runner DENTRO del chroot (sin nohup: usa setsid + redirecciones)
cat > $ROOT/opt/pos/start.sh <<'EOF'
#!/bin/sh
date >> /opt/pos/start_ran
cd /opt/pos
/bin/busybox setsid /usr/bin/python3 /opt/pos/app.py >> /opt/pos/pos.log 2>&1 < /dev/null &
EOF
$BB chmod 755 $ROOT/opt/pos/start.sh

# 2) pos_boot.sh (lado Android): monta y llama al runner
cat > /data/local/bin/pos_boot.sh <<'EOF'
#!/system/bin/sh
BB=/data/local/tmp/busybox
ROOT=/data/local/alpine
date >> /data/local/tmp/boot_ran
$BB mount --bind /dev $ROOT/dev 2>/dev/null
$BB mount -t proc proc $ROOT/proc 2>/dev/null
if $BB pgrep -f "[p]ython3 /opt/pos/[a]pp.py" >/dev/null 2>&1; then exit 0; fi
$BB chroot $ROOT /bin/sh /opt/pos/start.sh
EOF
$BB chmod 755 /data/local/bin/pos_boot.sh

# 3) hook de arranque en /system
$BB mount -o remount,rw /system
if ! $BB grep -q pos_boot /system/etc/init.qcom.post_boot.sh; then
  echo "sh /data/local/bin/pos_boot.sh" >> /system/etc/init.qcom.post_boot.sh
fi
$BB mount -o remount,ro /system

# 4) estado de archivos
$BB ls -l $ROOT/opt/pos/ $ROOT/opt/pos/templates/ | $BB head -20

# 5) arrancar ahora
sh /data/local/bin/pos_boot.sh
sleep 5

# 6) verificar paginas
for p in /venta /catalogo /productos /config /categorias /ratios /facturas /api/productos; do
  code=`/system/bin/curl -s -m 5 -o /dev/null -w %{http_code} http://127.0.0.1:8080$p`
  echo "PAGE $p -> $code"
done
echo "--- POS.LOG ---"
$BB tail -c 1200 $ROOT/opt/pos/pos.log 2>/dev/null
echo FINAL_OK
