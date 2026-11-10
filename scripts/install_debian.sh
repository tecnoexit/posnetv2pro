#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PATH
export PROOT_NO_SECCOMP=1
export DEBIAN_FRONTEND=noninteractive

echo "########## FASE 4: liberar espacio (toolchain de compilacion) ##########"
pkg remove -y clang llvm lld libllvm libcompiler-rt ndk-sysroot 2>&1 | tail -6
apt clean 2>/dev/null
rm -rf $PREFIX/tmp/* 2>/dev/null
echo "--- espacio tras limpieza ---"
df -h /data

echo ""
echo "########## FASE 5: instalar Debian (proot-distro) ##########"
echo "Inicio: $(date)"
proot-distro install debian 2>&1
echo "EXIT_install=$?"
echo "Fin: $(date)"

echo ""
echo "########## FASE 6: verificar Debian ##########"
proot-distro list 2>&1 | head -8

echo ""
echo "--- arrancando Debian ---"
proot-distro login debian -- /bin/sh -c 'echo "=== DEBIAN FUNCIONANDO ==="; cat /etc/os-release; echo "--- kernel ---"; uname -a; echo "--- arquitectura ---"; dpkg --print-architecture; echo "--- apt ---"; apt-get --version 2>/dev/null | head -1; echo "--- espacio ---"; df -h / 2>/dev/null; echo "--- red ---"; cat /etc/resolv.conf 2>/dev/null | head -3' 2>&1

echo ""
echo "########## ESPACIO FINAL ##########"
df -h /data
du -sh $PREFIX/var/lib/proot-distro 2>/dev/null

echo "SCRIPT_DEBIAN_OK"
