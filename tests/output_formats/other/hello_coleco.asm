; ColecoVision: the whole screen in changing colours (cartridge ROM from 8000h; the
; header is written here, pypasmo pads the ROM to 8 KB):
;   python -m pypasmo --rom-coleco hello_coleco.asm hello_coleco.col
; The emulator needs the ColecoVision BIOS (coleco.rom). With the display off, the VDP
; shows the backdrop colour on the whole screen; the program changes that colour about
; twice a second.

vdp_ctrl equ 0BFh               ; write a value, then 80h + the register number

        org 8000h
        db 0AAh, 55h            ; AAh 55h: the title screen of the BIOS first
        dw 0, 0, 0, 0           ; BIOS tables (sprites, buffer, controllers): not used
        dw start                ; 800Ah: the start of the program
        jp no_rst               ; 800Ch: RST 08h
        jp no_rst               ; RST 10h
        jp no_rst               ; RST 18h
        jp no_rst               ; RST 20h
        jp no_rst               ; RST 28h
        jp no_rst               ; RST 30h
        jp no_int               ; 801Eh: RST 38h / the maskable interrupt (not used)
        jp nmi                  ; 8021h: NMI = the VDP frame interrupt (off here)
        db "HELLO/PYPASMO/2026" ; 8024h: the text of the title screen: line/line/year

no_rst: ret
no_int: ei
        reti
nmi:    retn

start:  di
        ld sp,7400h             ; the top of the 1 KB RAM (7000h-73FFh)
        ld a,80h                ; VDP register 1 = 80h: 16 KB VRAM, display off
        out (vdp_ctrl),a
        ld a,81h
        out (vdp_ctrl),a
        ld b,1
loop:   ld a,b
        and 0Fh
        out (vdp_ctrl),a        ; VDP register 7: the backdrop colour (low 4 bits)
        ld a,87h
        out (vdp_ctrl),a
        ld de,0                 ; wait: 65536 x 26 T = about 0.5 s at 3.58 MHz
wait:   dec de
        ld a,d
        or e
        jr nz,wait
        inc b
        jr loop
