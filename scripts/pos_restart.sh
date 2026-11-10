#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PATH
export PROOT_NO_SECCOMP=1

cp /data/local/tmp/pos_app.py $PREFIX/var/lib/proot-distro/containers/debian/rootfs/opt/pos/app.py && echo APP_ACTUALIZADA

proot-distro login debian -- /bin/sh -c 'pkill -f "[p]ython3 /opt/pos/[a]pp.py" 2>/dev/null; echo servidor-detenido'
sleep 2

nohup $PREFIX/bin/proot-distro login debian -- /bin/sh -c 'exec python3 /opt/pos/app.py' >> $HOME/pos-server.log 2>&1 &
sleep 4

linux-run 'curl -s -o /dev/null -w "venta HTTP %{http_code}\n" --max-time 5 http://127.0.0.1:8080/venta'
echo SCRIPT_RESTART_OK
