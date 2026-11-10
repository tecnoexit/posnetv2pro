# POSNET V2 PRO — Punto de venta local para terminales SUNMI V2 Pro

Convierte un terminal POS **SUNMI V2 Pro** (Android 7.1.2, msm8937) en un equipo Linux usable
con un punto de venta **100% local** (sin nube ni internet) que usa la **impresora térmica interna
de 58 mm** del propio terminal, sin borrar nada del dispositivo: las apps POS originales
("Punto de Pago", MDM SOTI, etc.) y sus datos quedan intactos.

> ⚠️ **Regla de oro: NO flashear, NO desbloquear el bootloader, NO borrar datos.**
> El bootloader está bloqueado y no existen ROMs custom para este modelo. Todo se hace en
> espacio de usuario mediante ADB + Termux + proot.

## Qué incluye

| Componente | Descripción |
|---|---|
| **POS web** (Flask + SQLite + PIL) | Venta con escáner láser, productos con fotos, stock, códigos de barras, facturas imprimibles/editables, importación CSV, categorías administrables, ratios de moneda (precio = costo × ratio), buscador dinámico |
| **Ticket térmico 58 mm** | ESC/POS nativo vía la impresora interna del SUNMI (RawBT + AIDL `woyou.aidlservice.jiuiv5`) |
| **Vidriera digital** (`/catalogo`) | Catálogo público solo lectura para clientes: grilla de tarjetas con foto/categoría/precio, buscador dinámico, chips de categoría y botón flotante de WhatsApp para pedidos (`wa.me/<num>?text=<msg>`) |
| **Servidor persistente** | Flask escuchando en `0.0.0.0:8080`, arrancado desde Termux y sobreviviente a cierres de terminal |

Todo corre **dentro del dispositivo**: un único usuario sin login, pensado para uso en mostrador.

## Arquitectura

```
Android 7.1.2 (intacto, apps originales sin tocar)
 └── Termux 0.118 (app de usuario, sin root)
      └── proot-distro → Debian 13 (trixie) armhf  [PROOT_NO_SECCOMP=1]
           ├── /opt/pos/app.py        → Flask POS en 0.0.0.0:8080
           ├── /opt/pos/ticket.py     → generación ESC/POS
           ├── /opt/pos/data/pos.db   → SQLite (productos, ventas, config, categorías, ratios)
           ├── /opt/pos/data/fotos/   → fotos de productos (PIL)
           └── /usr/local/bin/imprimir → wrapper que envía a la impresora interna
                                          vía intent `rawbt:base64,<b64>` → RawBT
                                           → AIDL woyou.aidlservice.jiuiv5/.WoyouService
```

## Estructura de este repositorio

```
pos/                 Código de la aplicación (se instala en /opt/pos/ dentro de Debian)
  app.py             App Flask completa (POS + catálogo + migraciones de BD)
  ticket.py          Generación y envío de tickets ESC/POS
  templates/         11 plantillas Jinja2 (POS y catálogo público)
scripts/             Instalación, despliegue, arranque y pruebas
  setup_termux.sh    Instalación de Termux + proot-distro + Debian
  install_debian.sh  Paquetes Debian (flask, pillow, etc.)
  fixprint.sh        Cadena de impresión interna (imprimir → RawBT → AIDL woyou)
  fixdate.sh         Corrección de fecha/hora
  pos_install2.sh    Instalación limpia del POS
  pos_start.sh       Arranque persistente desde Termux (nohup)
  pos_restart.sh     Reinicio del servidor
  v2_deploy.sh       Despliegue del código (copia app + plantillas, py_compile, reinicia, verifica 11 páginas)
  v2_verify.*        Verificación de BD y API tras desplegar
  v2_fase2_test.*    Pruebas de CSV / buscador
  v2_fase3_test.*    Pruebas de categorías y ratios (creación, edición, recálculo, borrado)
  v2_setwa.*         Carga directa del WhatsApp de pedidos en SQLite
  ejemplo-productos.csv  Formato CSV de referencia
docs/                Referencia ESC/POS y ejemplo de ticket completo
AGENTS.md            ← Instrucciones para un agente IA que replique la instalación
```

Los APKs (Termux, RawBT, PrintService) **no se incluyen** por tamaño/licencia. Fuentes:

- **Termux 0.118 (armeabi-v7a)**: F-Droid (`https://f-droid.org/en/packages/com.termux/`)
  — usar la versión de F-Droid, NO la de Play Store (deprecada).
- **RawBT** (print service): Play Store o `https://rawbt.ru/` — versión probada: 7.0.3.

## Requisitos

- Terminal **SUNMI V2 Pro** con ADB habilitado (o habilitable desde Ajustes → Opciones de desarrollador).
- PC con `adb` en el PATH.
- WiFi para el terminal (la IP la asigna el router; la web queda en `http://<ip-del-terminal>:8080`).

## Instalación rápida (resumen)

El detalle completo paso a paso (con los trucos de este hardware) está en `AGENTS.md`.
En esencia:

1. Instalar Termux + proot-distro + Debian (`scripts/setup_termux.sh`, `scripts/install_debian.sh`).
2. Instalar RawBT y configurar la impresora interna 58 mm (`scripts/fixprint.sh`).
3. Instalar el POS (`scripts/pos_install2.sh`) y desplegar el código (`scripts/v2_deploy.sh`).
4. Arrancar el servidor persistente (`scripts/pos_start.sh`).
5. Configurar desde la web: nombre del negocio, dirección, pie de ticket, moneda,
   **WhatsApp de pedidos** y mensaje del catálogo (en `http://<ip>:8080/config`).
6. Verificar con `scripts/v2_verify.sh` y las pruebas `scripts/v2_fase3_test.sh`.

## Uso

- **POS**: `http://<ip-del-terminal>:8080` — venta con escáner láser, facturas, productos, stock.
- **Vidriera de clientes**: `http://<ip-del-terminal>:8080/catalogo` — solo lectura + botón WhatsApp.
- **Importar productos**: CSV `codigo;nombre;costo` (+ opcionales `precio;stock;categoria;ratio`),
  separador `;` o `,`, upsert por código.
- **Precios**: `precio = costo × ratio`. Los ratios ("General ×1,30", etc.) se crean, editan,
  eliminan y recalculan masivamente desde `/ratios`. Un precio escrito manualmente se respeta siempre.

## Licencia

Uso interno TecnoExit. Ajustar según necesidad.
