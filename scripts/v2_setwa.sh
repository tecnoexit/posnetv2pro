#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export TMPDIR=$PREFIX/tmp
export PATH=$PREFIX/bin:$PATH
export PROOT_NO_SECCOMP=1

ROOTFS=$PREFIX/var/lib/proot-distro/containers/debian/rootfs
cp /data/local/tmp/v2_setwa.py $ROOTFS/tmp/setwa.py

proot-distro login debian -- /bin/sh -c 'python3 /tmp/setwa.py'
