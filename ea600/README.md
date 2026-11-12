# Soporte UROVO EA600 (Android 4.3) — mismo POS, distinta base

Este directorio contiene los scripts usados para instalar el POS en un terminal
**UROVO EA600** (Android 4.3, SoC msm8610) que no tiene impresora térmica interna.
El POS es **el mismo código** de `pos/` con adaptaciones de compatibilidad
(ES5 + CSS sin flex/grid moderno) que además funcionan en los SUNMI V2 Pro.

## Diferencias clave con los SUNMI V2 Pro

| Aspecto | SUNMI V2 Pro | UROVO EA600 |
|---|---|---|
| Base Linux | Termux + proot-distro Debian (PROOT_NO_SECCOMP=1) | **chroot Alpine** (root ADB nativo, sin proot) |
| Python | Debian (python3-flask, python3-pil) | Alpine `apk add python3 py3-flask py3-pillow` (~50 MB) |
| Impresora | Interna 58 mm (RawBT + AIDL woyou) | Ninguna. `ticket.py` soporta **impresora de red** (`impresora_red` = `IP:9100` en Config) |
| Escáner | Láser HID (teclea como teclado) | Motor Urovo `android.device.ScanManager` — se pone en **modo teclado** (`ea600_scanmode.sh`) |
| Arranque | Termux + nohup | `init.qcom.post_boot.sh` → `/data/local/bin/pos_boot.sh` → `setsid python3` en el chroot |
| Navegador | Chrome moderno | WebKit de Android 4.3 → el HTML/JS está en **ES5** (sin fetch/async/let/flex/grid) |

## Pipeline de instalación (resumen)

1. **ADB root**: el build `eng` da shell como `uid=0`. No flashear nada.
2. **busybox estático armv7l** en `/data/local/tmp/busybox` (da chroot, tar, setsid, pgrep).
3. `ea600_poc.sh` — prueba de concepto: extrae `alpine-minirootfs-3.22.x-armv7.tar.gz`
   en `/data/local/alpine`, monta /dev y /proc, `apk add python3 py3-flask py3-pillow`,
   verifica `import flask, PIL, sqlite3`.
4. `ea600_final2.sh` — instalación definitiva:
   - crea `/opt/pos/start.sh` (runner interno del chroot: `setsid python3 app.py </dev/null`)
   - crea `/data/local/bin/pos_boot.sh` (monta /dev y /proc, llama al runner)
   - engancha `pos_boot.sh` a `/system/etc/init.qcom.post_boot.sh` (arranque automático)
   - verifica las páginas con curl local
5. `ea600_scanmode.sh` — pone el escáner Urovo en **modo teclado**:
   cambia `scanner_keyboard_output` a `true` en las preferencias de la app demo
   `com.example.urovoscan` (uid 10076) y la abre para que `switchOutputMode` lo aplique.
   Desde entonces el escáner teclea el código en el campo enfocado (igual que un HID).

## Trucos de este hardware (¡importantes!)

- **ADB serializa las sesiones de shell**: un proceso que hereda el stdin del shell
  (p.ej. `python3` sin `</dev/null`, o `screencap` colgado) **bloquea todos los
  shells siguientes** hasta reiniciar el dispositivo (`adb reboot` sí funciona).
  → Siempre lanzar procesos largos con `... </dev/null >log 2>&1 &` y leer el log después.
- **`tr -d "\r"` con comillas dobles borra las letras "r"** en este shell viejo
  (interpreta `\r` como el carácter r). → Usar comillas simples `tr -d '\r'` o,
  mejor, escribir los archivos con finales LF desde el PC (no hace falta tr).
- **`nohup` no existe en el chroot Alpine minirootfs** → usar `busybox setsid`.
- **La pantalla queda en Keyguard** y `screencap` captura negro: `input keyevent 26`
  (POWER) despierta; el desbloqueo por swipe puede no descartar el Keyguard.
  Para verificar la UI basta con abrirla desde la PC en `http://<ip>:8080`.
- **La IP cambia con la red WiFi** (en la red de prueba fue `192.168.0.60`).
  El POS escucha en `0.0.0.0:8080`, accesible desde cualquier cliente de la LAN.
- `wc`, `head`, `tail`, `uname`, `date` **no existen** en el toolbox de Android 4.3;
  usar los applets de busybox (`/data/local/tmp/busybox tail ...`).

## Estado verificado (12/11/2026)

- Python 3.12 + Flask 3.0.3 + Pillow 11.2.1 corriendo en chroot Alpine (~50 MB).
- 12 páginas en HTTP 200: venta, productos, productos/nuevo, productos/importar,
  facturas, config, categorias, ratios, catalogo, api/buscar, api/categorias, api/ratios.
- Alta de productos con precio automático (costo × ratio) funcionando.
- Arranque automático confirmado tras `adb reboot` (el servidor levanta solo).
- Escáner en modo teclado (`scanner_keyboard_output=true`).

## Pendientes para producción

- Probar físicamente un escaneo en el campo de búsqueda de `/venta`.
- Cargar nombre del negocio y WhatsApp reales en `/config`.
- Configurar la impresora de red cuando la haya (`impresora_red` = `IP:9100`).
