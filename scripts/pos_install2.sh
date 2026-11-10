#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PATH
export PROOT_NO_SECCOMP=1
mkdir -p "$TMPDIR"

ROOTFS=$PREFIX/var/lib/proot-distro/containers/debian/rootfs
POS=$ROOTFS/opt/pos

echo "########## 1. INSTALANDO PYTHON + FLASK + PIL EN DEBIAN ##########"
proot-distro login debian -- /bin/sh -c 'export DEBIAN_FRONTEND=noninteractive; apt-get update -qq 2>&1 | tail -2; apt-get install -y --no-install-recommends python3 python3-flask python3-pil 2>&1 | tail -5'

echo ""
echo "########## 2. COPIANDO LA APLICACION ##########"
mkdir -p $POS/templates $POS/data/fotos
cp /data/local/tmp/pos_app.py                 $POS/app.py
cp /data/local/tmp/pos_ticket.py              $POS/ticket.py
cp /data/local/tmp/pos_t_base.html            $POS/templates/base.html
cp /data/local/tmp/pos_t_venta.html           $POS/templates/venta.html
cp /data/local/tmp/pos_t_productos.html       $POS/templates/productos.html
cp /data/local/tmp/pos_t_producto_form.html   $POS/templates/producto_form.html
cp /data/local/tmp/pos_t_facturas.html        $POS/templates/facturas.html
cp /data/local/tmp/pos_t_factura_detalle.html $POS/templates/factura_detalle.html
cp /data/local/tmp/pos_t_config.html          $POS/templates/config.html
chmod 644 $POS/app.py $POS/ticket.py $POS/templates/*.html
ls -la $POS
ls -la $POS/templates

echo ""
echo "########## 3. VERIFICACION DE CODIGO ##########"
proot-distro login debian -- /bin/sh -c 'python3 -m py_compile /opt/pos/app.py /opt/pos/ticket.py && echo "python: sintaxis OK"; python3 -c "import flask, PIL; print(\"flask\", flask.__version__, \"| PIL OK\")"'

echo ""
echo "SCRIPT_POS_INSTALL_OK"
