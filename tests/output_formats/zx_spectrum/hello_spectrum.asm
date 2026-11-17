; hello_spectrum.asm - pypasmo demo for the ZX Spectrum (48K, 128K, +2, +3)
;
; Build a tape with a Basic loader or a snapshot:
;     python -m pypasmo --tap-wloader-48k --name hello tests/output_formats/zx_spectrum/hello_spectrum.asm tests/output_formats/zx_spectrum_results/hello_spectrum.tap
;     python -m pypasmo --tzx-wloader-48k --name hello tests/output_formats/zx_spectrum/hello_spectrum.asm tests/output_formats/zx_spectrum_results/hello_spectrum.tzx
;     python -m pypasmo --pzx-wloader-48k --name hello tests/output_formats/zx_spectrum/hello_spectrum.asm tests/output_formats/zx_spectrum_results/hello_spectrum.pzx
;     python -m pypasmo --sna-48k tests/output_formats/zx_spectrum/hello_spectrum.asm tests/output_formats/zx_spectrum_results/hello_spectrum.sna
;     python -m pypasmo --dsk-plus3 --name hello tests/output_formats/zx_spectrum/hello_spectrum.asm tests/output_formats/zx_spectrum_results/hello_spectrum.dsk
; Open the .tap / .tzx / .pzx in an emulator (Fuse, ZEsarUX, Spectaculator...) and LOAD ""
; (it starts by itself), the .sna starts at once; the +3 .dsk: "Loader" in the menu. The program prints a text, flashes the border until a key is pressed and
; returns to Basic.

CLS     equ 0D6Bh               ; ROM: clear the screen
CHANOPEN equ 1601h              ; ROM: open the channel in A (2 = upper screen)
BORDER  equ 0FEh                ; ULA port: bits 0-2 border colour, read = keyboard

AT      equ 16h                 ; print control codes
INK     equ 10h
END_TEXT equ 0FFh               ; end of the text (0 can be a parameter of AT / INK)

        org 8000h

start:  call CLS
        ld a,2
        call CHANOPEN
        ld hl,text
print:  ld a,(hl)               ; RST 10h prints the character in A
        cp END_TEXT
        jr z,release
        rst 10h
        inc hl
        jr print

release: xor a                  ; first wait until no key is pressed
        in a,(BORDER)           ; (ENTER from LOAD "" can still be down)
        cpl
        and 1Fh
        jr nz,release

flash:  ld c,0                  ; border colour
next:   ld a,c
        out (BORDER),a
        halt                    ; wait for the next frame (1/50 s)
        halt
        halt
        xor a                   ; read all keyboard rows
        in a,(BORDER)
        cpl
        and 1Fh                 ; a key is pressed when a bit is 0
        jr nz,done
        ld a,c
        inc a
        and 7
        ld c,a
        jr next

done:   ld a,7                  ; white border, back to Basic
        out (BORDER),a
        ret

text:   db AT,8,6, INK,2, "Hello from pypasmo!"
        db AT,10,2, INK,1, "Z80 assembler based on Pasmo"
        db AT,14,5, INK,0, "Press a key to stop"
        db END_TEXT             ; not 0: INK 0 above contains a zero byte

        end start
