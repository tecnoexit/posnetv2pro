#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PATH
export PROOT_NO_SECCOMP=1

ROOTFS=$PREFIX/var/lib/proot-distro/containers/debian/rootfs
POS=$ROOTFS/opt/pos

echo "########## 1. COPIANDO APP + PLANTILLAS ##########"
cp /data/local/tmp/pos_app.py                 $POS/app.py
cp /data/local/tmp/pos_t_base.html            $POS/templates/base.html
cp /data/local/tmp/pos_t_venta.html           $POS/templates/venta.html
cp /data/local/tmp/pos_t_productos.html       $POS/templates/productos.html
cp /data/local/tmp/pos_t_producto_form.html   $POS/templates/producto_form.html
cp /data/local/tmp/pos_t_facturas.html        $POS/templates/facturas.html
cp /data/local/tmp/pos_t_factura_detalle.html $POS/templates/factura_detalle.html
cp /data/local/tmp/pos_t_config.html          $POS/templates/config.html
cp /data/local/tmp/pos_t_importar.html        $POS/templates/importar.html
cp /data/local/tmp/pos_t_categorias.html      $POS/templates/categorias.html
cp /data/local/tmp/pos_t_ratios.html          $POS/templates/ratios.html
cp /data/local/tmp/pos_t_catalogo.html        $POS/templates/catalogo.html
chmod 644 $POS/app.py $POS/templates/*.html
echo "copiados"

echo ""
echo "########## 2. SINTAXIS ##########"
proot-distro login debian -- /bin/sh -c 'python3 -m py_compile /opt/pos/app.py && echo "python OK"'

echo ""
echo "########## 3. REINICIAR SERVIDOR ##########"
proot-distro login debian -- /bin/sh -c 'pkill -f "[p]ython3 /opt/pos/[a]pp.py" 2>/dev/null; echo detenido'
sleep 2
nohup $PREFIX/bin/proot-distro login debian -- /bin/sh -c 'exec python3 /opt/pos/app.py' >> $HOME/pos-server.log 2>&1 &
sleep 4

echo ""
echo "########## 4. VERIFICAR PAGINAS ##########"
proot-distro login debian -- /bin/sh -c 'for p in /venta /productos /productos/nuevo /productos/importar /facturas /config /categorias /ratios /catalogo "/api/buscar?q=a" /api/categorias /api/ratios; do curl -s -o /dev/null -w "$p  HTTP %{http_code}\n" --max-time 5 "http://127.0.0.1:8080$p"; done'

echo ""
echo "SCRIPT_DEPLOY_OK"
