#!/system/bin/sh
# Prueba de concepto EA600: chroot Alpine + Python + Flask + Pillow
BB=/data/local/tmp/busybox
ROOT=/data/local/alpine
set -x
mkdir -p $ROOT
$BB tar -xzf /data/local/tmp/alpine.tar.gz -C $ROOT || { echo FALLO_TAR; exit 1; }
echo "nameserver 192.168.0.1" > $ROOT/etc/resolv.conf
$BB mount --bind /dev $ROOT/dev 2>/dev/null
$BB mount -t proc proc $ROOT/proc 2>/dev/null
$BB chroot $ROOT /bin/sh -c "apk update && apk add --no-cache python3 py3-flask py3-pillow"
echo "--- TEST PYTHON ---"
$BB chroot $ROOT /usr/bin/python3 -c "import flask, PIL, sqlite3, json, base64; print('POC_OK flask=' + flask.__version__ + ' pillow=' + PIL.__version__)"
echo "--- ESPACIO ---"
$BB df -h /data
