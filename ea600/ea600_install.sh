#!/system/bin/sh
# Instalacion POS en EA600 (Urovo) - chroot Alpine
# Se ejecuta como root via: adb shell sh /data/local/tmp/ea600_install.sh
BB=/data/local/tmp/busybox
ROOT=/data/local/alpine
POS_SRC=/data/local/tmp/posfiles
set -x

# 1) Copiar la app al chroot
$BB mkdir -p $ROOT/opt/pos/templates $ROOT/opt/pos/data/fotos
$BB cp $POS_SRC/app.py $ROOT/opt/pos/app.py
$BB cp $POS_SRC/ticket.py $ROOT/opt/pos/ticket.py
$BB cp $POS_SRC/tpl_* $ROOT/opt/pos/templates/ 2>/dev/null
for f in $ROOT/opt/pos/templates/tpl_*; do
  base=`$BB basename $f | $BB sed 's/^tpl_//'`
  $BB mv $f $ROOT/opt/pos/templates/$base
done

# 2) Verificar sintaxis
$BB chroot $ROOT /usr/bin/python3 -m py_compile /opt/pos/app.py /opt/pos/ticket.py || { echo FALLO_COMPILE; exit 1; }

# 3) Script de arranque (lado Android)
$BB mkdir -p /data/local/bin
cat > /data/local/bin/pos_boot.sh <<'EOF'
#!/system/bin/sh
BB=/data/local/tmp/busybox
ROOT=/data/local/alpine
$BB mount --bind /dev $ROOT/dev 2>/dev/null
$BB mount -t proc proc $ROOT/proc 2>/dev/null
if $BB pgrep -f "[p]ython3 /opt/pos/[a]pp.py" >/dev/null 2>&1; then
  exit 0
fi
$BB chroot $ROOT /bin/sh -c 'cd /opt/pos && nohup /usr/bin/python3 /opt/pos/app.py >>/opt/pos/pos.log 2>&1 &'
EOF
$BB chmod 755 /data/local/bin/pos_boot.sh

# 4) Persistencia: enganchar a init.qcom.post_boot.sh (se ejecuta en cada arranque)
if ! $BB grep -q "pos_boot.sh" /system/etc/init.qcom.post_boot.sh; then
  $BB mount -o remount,rw /system 2>/dev/null
  echo "sh /data/local/bin/pos_boot.sh" >> /system/etc/init.qcom.post_boot.sh
  $BB mount -o remount,ro /system 2>/dev/null
fi

# 5) Arrancar ahora
sh /data/local/bin/pos_boot.sh
sleep 3

# 6) Verificar paginas
for p in / /venta /productos /producto/nuevo /facturas /config /importar /categorias /ratios /catalogo /api/productos; do
  code=`/system/bin/curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080$p`
  echo "PAGE $p -> $code"
done
echo INSTALACION_OK
