#!/bin/bash
# =====================================================================
#  referencia-escpos - Imprime una tarjeta de referencia ESC/POS
#  Uso:  referencia-escpos
# =====================================================================
source /usr/local/lib/escpos.sh

escpos_reset_file
escpos_init

escpos_align 1
escpos_size 2 1
escpos_text "REFERENCIA ESC/POS"
escpos_size 1 1
escpos_text "SUNMI V2 Pro - 58mm"
escpos_rule2

escpos_align 0
escpos_bold 1; escpos_text "COMANDOS BASICOS"; escpos_bold 0
escpos_rule
escpos_text 'ESC @ ............ init'
escpos_text 'ESC a n .......... alineacion'
escpos_text '                  0=izq 1=centro 2=der'
escpos_text 'ESC E n .......... negrita'
escpos_text 'ESC - n .......... subrayado'
escpos_text 'ESC M n .......... fuente A/B/C'
escpos_text 'ESC d n .......... avance lineas'
escpos_text 'GS  ! n .......... tamano (nibbles)'
escpos_text 'GS  B n .......... invertir'
escpos_text 'GS  V n .......... corte (0=total)'
escpos_text 'ESC p n t d ...... abrir caja'
escpos_text ""

escpos_bold 1; escpos_text "TAMANO DE LETRA"; escpos_bold 0
escpos_rule
escpos_text "GS ! n : alto nibble = alto"
escpos_text "         bajo nibble = ancho"
escpos_text "         n = 0x00 a 0x77"
escpos_text ""
escpos_size 1 1; escpos_text "1x1 normal"
escpos_size 2 1; escpos_text "2x1 doble ancho"
escpos_size 1 2; escpos_text "1x2 doble alto"
escpos_size 2 2; escpos_text "2x2 doble ambos"
escpos_size 1 1
escpos_text ""

escpos_bold 1; escpos_text "CODIGOS DE BARRAS"; escpos_bold 0
escpos_rule
escpos_text "GS h n  alto (1-255)"
escpos_text "GS w n  ancho (2-6)"
escpos_text "GS H n  HRI 0-3"
escpos_text "GS k m n d1..dn"
escpos_text ""
escpos_text "  65 UPC-A    69 CODE39"
escpos_text "  66 UPC-E    70 ITF"
escpos_text "  67 EAN13    71 CODABAR"
escpos_text "  68 EAN8     72 CODE93"
escpos_text "              73 CODE128"
escpos_text ""

escpos_bold 1; escpos_text "QR (GS ( k)"; escpos_bold 0
escpos_rule
escpos_text "31 41 n n ... modelo 2"
escpos_text "31 43 n .... tamano 1-16"
escpos_text "31 45 n .... correccion"
escpos_text "             48=L 49=M"
escpos_text "             50=Q 51=H"
escpos_text "31 50 30 .. almacenar dato"
escpos_text "31 51 30 .. imprimir"
escpos_text ""

escpos_bold 1; escpos_text "COMANDOS EN LINUX"; escpos_bold 0
escpos_rule
escpos_text "source /usr/local/lib/escpos.sh"
escpos_text "escpos_init"
escpos_text 'escpos_align 1'
escpos_text 'escpos_bold 1'
escpos_text 'escpos_text "Hola"'
escpos_text "escpos_flush"
escpos_text ""
escpos_text "imprimir f.bin      ESC/POS crudo"
escpos_text 'imprimir --texto .. texto rapido'
escpos_text "ticket-completo     demo completo"
escpos_text ""

escpos_feed 1
escpos_align 1
escpos_text "fin de la referencia"
escpos_feed 2
escpos_cut 0

escpos_flush
