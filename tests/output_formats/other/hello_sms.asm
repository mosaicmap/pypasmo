; Sega Master System: the whole screen in changing colours (32 KB ROM; the header with
; the checksum at 7FF0h is written by pypasmo):
;   python -m pypasmo --rom-sms hello_sms.asm hello_sms.sms
; With the display off, the VDP shows the backdrop colour on the whole screen; the
; program changes that colour about twice a second.

vdp_data equ 0BEh
vdp_ctrl equ 0BFh

        org 0                   ; the Z80 starts here
        di
        im 1
        ld sp,0DFF0h            ; top of the 8 KB RAM (C000h-DFFFh)
        jp main

        org 38h                 ; interrupt (not enabled here)
        reti

        org 66h                 ; NMI: the pause button
        retn

main:   ld hl,regs              ; VDP registers: value, 80h + number
        ld b,regs_end-regs
        ld c,vdp_ctrl
        otir
        ld b,0                  ; the colour: 00BBGGRR
loop:   ld a,10h                ; CRAM address 16: colour 0 of the sprite palette
        out (vdp_ctrl),a
        ld a,0C0h               ; 0C0h = write to CRAM
        out (vdp_ctrl),a
        ld a,b
        and 3Fh
        out (vdp_data),a
        inc b
        ld de,0                 ; wait: 65536 times
wait:   dec de
        ld a,d
        or e
        jr nz,wait
        jr loop

regs:   db 04h, 80h             ; register 0: mode 4
        db 80h, 81h             ; register 1: display off (the backdrop colour only)
        db 00h, 87h             ; register 7: the backdrop is colour 16 (CRAM 10h)
regs_end:
