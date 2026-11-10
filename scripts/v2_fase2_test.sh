#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PATH
export PROOT_NO_SECCOMP=1

ROOTFS=$PREFIX/var/lib/proot-distro/containers/debian/rootfs

# meter el CSV y el verificador dentro del rootfs de Debian
cp /data/local/tmp/ejemplo-productos.csv $ROOTFS/tmp/ejemplo.csv
cp /data/local/tmp/v2_check.py $ROOTFS/tmp/chk.py

echo "########## 1. IMPORTAR CSV DE EJEMPLO ##########"
proot-distro login debian -- /bin/sh -c 'curl -s -X POST http://127.0.0.1:8080/productos/importar -F "archivo=@/tmp/ejemplo.csv" -o /dev/null -w "importar HTTP %{http_code}\n"'

echo ""
echo "########## 2. PRODUCTOS EN LA BASE ##########"
proot-distro login debian -- /bin/sh -c 'python3 /tmp/chk.py'

echo ""
echo "########## 3. CATEGORIAS ##########"
proot-distro login debian -- /bin/sh -c 'curl -s http://127.0.0.1:8080/api/categorias; echo'

echo ""
echo "########## 4. BUSCADOR DINAMICO ##########"
proot-distro login debian -- /bin/sh -c 'curl -s "http://127.0.0.1:8080/api/buscar?q=coca"; echo; curl -s "http://127.0.0.1:8080/api/buscar?q=Bebidas"'

echo ""
echo "SCRIPT_TESTF2_OK"
