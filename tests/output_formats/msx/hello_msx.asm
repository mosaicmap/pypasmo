; hello_msx.asm - pypasmo demo for the MSX tape image (.cas) and disk image (.dsk)
;
;     python -m pypasmo --cas-msx --name hello tests/output_formats/msx/hello_msx.asm tests/output_formats/msx_results/hello_msx.cas
;     python -m pypasmo --dsk-msx --name hello tests/output_formats/msx/hello_msx.asm tests/output_formats/msx_results/hello_msx.dsk
;
; In an emulator (e.g. WebMSX): insert hello_msx.cas as a cassette, then in MSX-BASIC
;     BLOAD "CAS:",R
; or insert hello_msx.dsk as a disk and reset: AUTOEXEC.BAS runs HELLO.BIN.
; The program clears the screen, prints a text with the BIOS and returns to BASIC (Ok).

CHPUT   equ 00A2h               ; BIOS: print the character in A

        org 9000h

start:  ld hl,text
print:  ld a,(hl)
        or a
        ret z                   ; end of the text: back to BASIC
        call CHPUT
        inc hl
        jr print

text:   db 12                   ; clear the screen
        db "Hello from pypasmo!",13,10
        db "MSX test OK",13,10,0

        end start
