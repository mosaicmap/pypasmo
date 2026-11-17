; Sega Game Gear: the whole screen in changing colours (32 KB ROM; the header with the
; checksum at 7FF0h is written by pypasmo):
;   python -m pypasmo --rom-gg hello_gg.asm hello_gg.gg
; As hello_sms.asm, but a Game Gear colour has 12 bits: two bytes in the CRAM
; (GGGGRRRR, then 0000BBBB).

vdp_data equ 0BEh
vdp_ctrl equ 0BFh

        org 0                   ; the Z80 starts here
        di
        im 1
        ld sp,0DFF0h            ; top of the 8 KB RAM (C000h-DFFFh)
        jp main

        org 38h                 ; interrupt (not enabled here)
        reti

        org 66h                 ; NMI (not used on the Game Gear)
        retn

main:   ld hl,regs              ; VDP registers: value, 80h + number
        ld b,regs_end-regs
        ld c,vdp_ctrl
        otir
        ld hl,0                 ; the colour: 0000BBBB GGGGRRRR
loop:   ld a,20h                ; CRAM address 32: colour 16 (2 bytes per colour)
        out (vdp_ctrl),a
        ld a,0C0h               ; 0C0h = write to CRAM
        out (vdp_ctrl),a
        ld a,l
        out (vdp_data),a        ; GGGGRRRR
        ld a,h
        and 0Fh
        out (vdp_data),a        ; 0000BBBB
        ld de,111h              ; the next colour: + 1 in red, green and blue
        add hl,de
        ld de,0                 ; wait: 65536 times
wait:   dec de
        ld a,d
        or e
        jr nz,wait
        jr loop

regs:   db 04h, 80h             ; register 0: mode 4
        db 80h, 81h             ; register 1: display off (the backdrop colour only)
        db 00h, 87h             ; register 7: the backdrop is colour 16
regs_end:
