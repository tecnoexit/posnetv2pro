# AGENTS.md — Guía para replicar la instalación en otro SUNMI V2 Pro

Estás viendo esto porque un agente te pidió replicar el sistema **POSNET V2 PRO** en otro
terminal SUNMI V2 Pro idéntico. Sigue estas instrucciones al pie de la letra. El código del
repositorio es la fuente de verdad; no reescribas la app salvo que el usuario lo pida.

## Objetivo

Convertir un SUNMI V2 Pro en equipo Linux con POS local (Flask + SQLite + PIL) usando su
impresora térmica interna de 58 mm, **sin borrar nada** del dispositivo (apps POS originales,
MDM SOTI y datos intactos) y con vidriera digital pública en `/catalogo`.

## Reglas inquebrantables

1. **NO flashear, NO desbloquear bootloader, NO factory reset, NO borrar datos.**
2. **NO tocar las apps originales** ("Punto de Pago", MDM SOTI, PrintService del fabricante).
3. Todo se hace en espacio de usuario: ADB + Termux + proot. No se necesita root.
4. La impresora es **la interna del SUNMI** (58 mm), nunca una impresora externa del PC.
5. Todo local: sin nube, sin internet obligatorio en el terminal (solo WiFi de la LAN).

## Entorno conocido

- Hardware: SUNMI V2 Pro (SoC msm8937), **Android 7.1.2**, pantalla táctil, escáner láser
  integrado (emite teclas + Enter, funciona como teclado HID para el navegador).
- Identificación por ADB: el número de serie empieza con `V283...` (ej: `V283213S21789`).
- Solo **un dispositivo ADB conectado a la vez**; usa `adb devices -l` para confirmar cuál es.
- Impresora: SUNMI inner printer de 58 mm, servicio AIDL `woyou.aidlservice.jiuiv5/.WoyouService`.

## Pipeline de instalación (orden obligatorio)

### Fase 0 — Conectividad y ADB

- `adb devices -l` → confirmar el serial del terminal.
- Habilitar depuración USB si hace falta (Ajustes → Opciones de desarrollador).
- La pantalla se duerme: antes de capturas o interacción, `input keyevent KEYCODE_WAKEUP` + swipe.

### Fase 1 — Linux usable (Termux + Debian)

1. Instalar APK de **Termux 0.118 (armeabi-v7a) de F-Droid** (NO Play Store):
   `adb install termux-armeabi-v7a.apk`.
2. `scripts/setup_termux.sh`: actualiza paquetes Termux, instala `proot-distro`, crea el
   contenedor **Debian 13 (trixie) armhf** y fija `PROOT_NO_SECCOMP=1` (obligatorio en este
   kernel viejo; sin eso proot falla).
3. `scripts/install_debian.sh`: `python3-flask`, `python3-pil`, `python3-smbus`/utilidades,
   `net-tools`, `procps`, `sqlite3`, etc.
4. **Impresión interna**: `scripts/fixprint.sh` crea `/usr/local/bin/imprimir` dentro de Debian.
   Cadena de impresión (NO cambiar):
   - Debian genera el ticket ESC/POS → `/usr/bin/base64 -w0` (**nunca** `/system/bin/base64`,
     que es incompatible) → `am start --user 0 -a android.intent.action.VIEW -d "rawbt:base64,<b64>"`
     → app **RawBT** → AIDL `woyou.aidlservice.jiuiv5/.WoyouService` → impresora interna.
   - Instalar RawBT (APK aparte) y en su configuración elegir la impresora interna / SUNMI.
5. `scripts/fixdate.sh`: la hora del terminal suele estar mal; fija fecha/hora desde el PC
   (`date +%d/%m/%Y`, `date +%H:%M`) o vía NTP cuando haya WiFi.
6. Probar impresión con `scripts/pos_print.sh` / ticket de prueba antes de seguir.

### Fase 2 — POS

1. `scripts/pos_install2.sh` instala el POS en `/opt/pos/` (app + plantillas + `data/`).
2. `scripts/v2_deploy.sh` es el despliegue estándar: copia `pos/app.py` y las **11 plantillas**
   al rootfs, corre `py_compile`, reinicia el servidor y verifica que las 11 páginas respondan
   HTTP 200 (`/`, `/venta`, `/productos`, `/producto/nuevo`, `/facturas`, `/config`, `/importar`,
   `/categorias`, `/ratios`, `/catalogo`, `/api/productos`).
3. `scripts/pos_start.sh` arranca el servidor **persistente desde Termux**:
   `nohup proot-distro login debian -- /bin/sh -c 'exec python3 /opt/pos/app.py'`
   — debe lanzarse desde Termux (no desde el PC vía adb directo) para que sobreviva.
   Log: `/data/data/com.termux/files/home/pos-server.log`.
   Escucha en `0.0.0.0:8080` (accesible desde la LAN y desde el propio terminal en `127.0.0.1:8080`).
4. Pruebas: `scripts/v2_fase2_test.sh` (CSV/buscador) y `scripts/v2_fase3_test.sh` (ratios y
   categorías: creación, edición, recálculo masivo, eliminación con limpieza posterior).

### Fase 3 — Vidriera pública

- `/catalogo` es una plantilla standalone (sin menú POS): grilla de tarjetas con foto,
  categoría y precio; buscador dinámico con debounce 120 ms; chips de categoría; filtrado
  100% client-side; **botón flotante de WhatsApp** con latido que abre
  `wa.me/<num>?text=<msg>` (configurables en Config: `whatsapp`, `whatsapp_mensaje`).
- `scripts/v2_setwa.sh` + `v2_setwa.py` cargan un WhatsApp de prueba directo en SQLite.
  **Siempre dejar pendiente al usuario reemplazarlo por el número real en Config.**

## Base de datos

- Ruta: `/opt/pos/data/pos.db` (SQLite). Fotos: `/opt/pos/data/fotos/` (PIL).
- Tablas: `config`, `categorias(id, nombre UNIQUE)`, `ratios(id, nombre, valor REAL)`,
  `productos` (columnas `costo`, `categoria`, `ratio_id` agregadas por migración),
  `ventas`, `venta_items`.
- Migraciones al arrancar: `PRAGMA table_info` + `ALTER TABLE` (nunca recrear tablas:
  preserva datos de instalaciones previas).
- Config keys: `nombre_negocio`, `direccion`, `pie_ticket`, `moneda`, `codificacion`,
  `whatsapp`, `whatsapp_mensaje` (legacy `porcentaje_venta` se migra automáticamente a un
  ratio "General ×1,30" sin tocar precios existentes).
- Modelo de precios: `precio = costo × ratio_moneda`. El ratio por defecto (★) aplica a
  productos sin ratio propio. Precio manual escrito a mano **se respeta siempre**.
- CSV: `codigo;nombre;costo` (+ opcionales `precio;stock;categoria;ratio`), separador `;`
  o `,`, upsert por código; el ratio puede venir por nombre o por número.

## Trucos y bugs conocidos (¡leer antes de operar!)

- **Archivos en `/data/local/tmp` NO son visibles dentro de proot.** Copiarlos antes al rootfs
  (vía `run-as com.termux` o `cat`) o empujar directo con `adb push` a la ruta del rootfs.
- **Scripts `.sh`/`.py`**: empujarlos con `adb push` y normalizar fin de línea:
  `adb shell "tr -d '\r' < archivo > archivo.n && mv archivo.n archivo"`. Nunca escribir
  scripts largos inline desde PowerShell: las comillas anidadas PowerShell→sh fallan.
- Invocar `proot-distro` directamente desde PowerShell falla; usar wrapper sh con
  `export PATH=$PREFIX/bin:$PATH` + `PROOT_NO_SECCOMP=1`, o `run-as com.termux sh script.sh`.
- **`pkill -f` con patrón literal se mata a sí mismo.** Usar patrón con clases de caracteres:
  `[p]ython3 /opt/pos/[a]pp.py`.
- El rootfs Debian vive en
  `/data/data/com.termux/files/usr/var/lib/proot-distro/containers/debian/rootfs`
  (copiar ficheros vía `run-as com.termux`).
- Jinja cachea plantillas: la app corre con `TEMPLATES_AUTO_RELOAD=True`; si cambias plantillas,
  reinicia el servidor con `scripts/pos_restart.sh`.
- Chrome cachea páginas: al verificar visualmente, recargar con `?v=N`.
- La pantalla se duerme: `input keyevent KEYCODE_WAKEUP` + `input swipe 360 1000 360 300 300`
  antes de capturar (`screencap -p`).
- Fecha del ticket: `FECHA=$(date +%d/%m/%Y); HORA=$(date +%H:%M)` (formato argentino).

## Post-instalación (dejar listo para el usuario)

1. En `http://<ip>:8080/config`: nombre del negocio, dirección, pie de ticket, moneda,
   **WhatsApp real** y mensaje del catálogo. (El equipo de prueba quedó con `5491122334455`
   de ejemplo — avisar que hay que cambiarlo.)
2. Confirmar con el usuario si borra o no los productos de prueba.
3. Ver final: las 11 páginas en HTTP 200, una impresión de prueba real por la impresora
   interna, y captura de pantalla del catálogo.

## Verificación rápida (checklist)

```text
[ ] adb devices muestra el terminal correcto
[ ] Termux + Debian arrancan con PROOT_NO_SECCOMP=1
[ ] /usr/local/bin/imprimir imprime ticket de prueba por la impresora interna
[ ] Servidor vivo: curl http://127.0.0.1:8080 responde (y desde la LAN :8080)
[ ] Las 11 páginas responden 200 (usa scripts/v2_verify.py)
[ ] scripts/v2_fase3_test.sh pasa (ratios + categorías)
[ ] Escáner láser carga productos en /venta (prueba manual en pantalla)
[ ] /catalogo muestra tarjetas, buscador y botón de WhatsApp funcional
[ ] Config: nombre de negocio y WhatsApp reales cargados
```
