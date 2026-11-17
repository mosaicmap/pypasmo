; hello_msx_rom.asm - pypasmo demo for the MSX cartridge ROM (.rom)
;
;     python -m pypasmo --rom-msx tests/output_formats/msx/hello_msx_rom.asm tests/output_formats/msx_results/hello_msx_rom.rom
;
; In an emulator (e.g. WebMSX): insert hello_msx_rom.rom as a cartridge and reset (or
; start) the MSX. The BIOS finds the header "AB" at 4000h and calls INIT: the program
; prints a text, waits for a key and returns; then the MSX starts BASIC as usual.

CHPUT   equ 00A2h               ; BIOS: print the character in A
CHGET   equ 009Fh               ; BIOS: wait for a key, its code in A

        org 4000h

        db "AB"                 ; ID of a cartridge ROM
        dw init                 ; INIT: called by the BIOS at start-up
        dw 0, 0, 0              ; STATEMENT, DEVICE, TEXT: not used
        ds 6                    ; reserved

init:   ld hl,text
print:  ld a,(hl)
        or a
        jr z,wait
        call CHPUT
        inc hl
        jr print
wait:   ei                      ; the keyboard is read in the interrupt
        call CHGET
        ret                     ; back to the BIOS: it starts BASIC

text:   db 12                   ; clear the screen
        db "Hello from pypasmo!",13,10
        db "MSX .rom test OK",13,10,13,10
        db "Press a key for BASIC",0
