#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PATH
export PROOT_NO_SECCOMP=1

echo "=== IMPRIMIENDO TICKET FACTURA #1 (desde el POS) ==="
linux-run 'curl -s -X POST http://127.0.0.1:8080/facturas/1/imprimir -o /dev/null -w "imprimir HTTP %{http_code}\n"'
sleep 3
echo "=== LOG DE IMPRESION ==="
linux-run 'tail -3 /opt/pos/data/pos.log'
echo "SCRIPT_PRINT_OK"
