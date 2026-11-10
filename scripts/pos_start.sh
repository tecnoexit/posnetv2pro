#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PATH
export PROOT_NO_SECCOMP=1
mkdir -p "$TMPDIR"

echo "########## 1. DETENER SERVIDOR ANTERIOR (si existe) ##########"
proot-distro login debian -- /bin/sh -c 'pkill -f "[p]ython3 /opt/pos/[a]pp.py" 2>/dev/null; sleep 1; echo listo'
sleep 2

echo ""
echo "########## 2. LANZADORES EN TERMUX (pos / pos-detener) ##########"
printf '#!/data/data/com.termux/files/usr/bin/bash\n# Punto de venta SUNMI: inicia el servidor y abre Chrome\nexport PROOT_NO_SECCOMP=1\nP=/data/data/com.termux/files/usr\nif ! proot-distro login debian -- /bin/sh -c "curl -s -o /dev/null --max-time 2 http://127.0.0.1:8080/" 2>/dev/null; then\n  echo "Iniciando servidor del punto de venta..."\n  nohup $P/bin/proot-distro login debian -- /bin/sh -c "exec python3 /opt/pos/app.py" >> $HOME/pos-server.log 2>&1 &\n  sleep 3\nfi\nam start --user 0 -a android.intent.action.VIEW -d http://127.0.0.1:8080/ >/dev/null 2>&1\necho "Punto de venta en http://127.0.0.1:8080"\n' > $PREFIX/bin/pos
chmod 755 $PREFIX/bin/pos

printf '#!/data/data/com.termux/files/usr/bin/bash\n# Detiene el servidor del punto de venta\nexport PROOT_NO_SECCOMP=1\nP=/data/data/com.termux/files/usr\n$P/bin/proot-distro login debian -- /bin/sh -c "pkill -f \\"[p]ython3 /opt/pos/[a]pp.py\\" 2>/dev/null && echo detenido || echo no estaba corriendo"\npkill -f "[p]root-distro login debian" 2>/dev/null\n' > $PREFIX/bin/pos-detener
chmod 755 $PREFIX/bin/pos-detener
ls -la $PREFIX/bin/pos $PREFIX/bin/pos-detener

echo ""
echo "########## 3. ARRANCAR SERVIDOR (sesion persistente) ##########"
nohup $PREFIX/bin/proot-distro login debian -- /bin/sh -c 'exec python3 /opt/pos/app.py' >> $HOME/pos-server.log 2>&1 &
sleep 5

echo ""
echo "########## 4. COMPROBAR SERVIDOR ##########"
proot-distro login debian -- /bin/sh -c 'curl -s -o /dev/null -w "raiz   HTTP %{http_code}\n" --max-time 5 http://127.0.0.1:8080/; curl -s -o /dev/null -w "venta  HTTP %{http_code}\n" --max-time 5 http://127.0.0.1:8080/venta; curl -s -o /dev/null -w "buscar HTTP %{http_code}\n" --max-time 5 "http://127.0.0.1:8080/api/buscar?q=x"; echo "--- log servidor ---"; tail -6 /opt/pos/data/pos.log 2>/dev/null; tail -6 /data/data/com.termux/files/home/pos-server.log 2>/dev/null'

echo ""
echo "SCRIPT_START_OK"
