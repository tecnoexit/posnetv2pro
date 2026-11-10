#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PREFIX/bin/applets:$PATH
export LANG=en_US.UTF-8
export SHELL=$PREFIX/bin/bash

echo "=========================================="
echo " SUNMI V2 Pro - Entorno Termux"
echo "=========================================="
echo "PREFIX = $PREFIX"
echo "HOME   = $HOME"
echo "id     = $(id)"
echo "date   = $(date)"
echo "=========================================="

mkdir -p "$TMPDIR" "$HOME"
cd "$HOME" || exit 1

echo ""
echo "[1/3] Actualizando repositorios de Termux..."
pkg update -y
echo "EXIT_pkg_update=$?"

echo ""
echo "[2/3] Instalando proot-distro..."
pkg install -y proot-distro
echo "EXIT_proot_install=$?"

echo ""
echo "[3/3] Verificando instalacion..."
which proot-distro
proot-distro --version 2>/dev/null || proot-distro help 2>&1 | head -5

echo ""
echo "=== DISTROS DISPONIBLES ==="
proot-distro list 2>&1

echo ""
echo "=== ALMACENAMIENTO ==="
df -h /data 2>/dev/null || df -h "$HOME"

echo ""
echo "SCRIPT_SETUP_OK"
