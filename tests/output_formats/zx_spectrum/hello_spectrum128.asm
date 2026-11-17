; hello_spectrum128.asm - pypasmo demo of BANK for the ZX Spectrum 128K (+2, +3)
;
; Build a tape with the 128K Basic loader, or a 128K snapshot:
;     python -m pypasmo --tap-wloader-128k tests/output_formats/zx_spectrum/hello_spectrum128.asm tests/output_formats/zx_spectrum_results/hello_spectrum128.tap
; The same tape as .tzx or .pzx (IN DEVELOPMENT):
;     python -m pypasmo --tzx-wloader-128k tests/output_formats/zx_spectrum/hello_spectrum128.asm tests/output_formats/zx_spectrum_results/hello_spectrum128.tzx
;     python -m pypasmo --pzx-wloader-128k tests/output_formats/zx_spectrum/hello_spectrum128.asm tests/output_formats/zx_spectrum_results/hello_spectrum128.pzx
;     python -m pypasmo --sna-128k tests/output_formats/zx_spectrum/hello_spectrum128.asm tests/output_formats/zx_spectrum_results/hello_spectrum128.sna
;     python -m pypasmo --z80-128k tests/output_formats/zx_spectrum/hello_spectrum128.asm tests/output_formats/zx_spectrum_results/hello_spectrum128.z80
; In an emulator in 128K mode choose "Tape Loader" (or LOAD "" in 128 BASIC). The loader
; puts each block into its bank, then runs the program: it pages in banks 1 and 3 at
; C000h and prints a text stored in each of them.

CLS     equ 0D6Bh               ; ROM: clear the screen
CHANOPEN equ 1601h              ; ROM: open the channel in A (2 = upper screen)
BANKM   equ 5B5Ch               ; system variable: last value written to port 7FFDh
PAGING  equ 7FFDh               ; bits 0-2: RAM bank at C000h

AT      equ 16h
INK     equ 10h
END_TEXT equ 0FFh

        org 8000h               ; bank 2 (always at 8000h)

start:  call CLS
        ld a,2
        call CHANOPEN
        ld a,1                  ; text from bank 1
        call page
        ld hl,text1
        call print
        ld a,3                  ; text from bank 3
        call page
        ld hl,text3
        call print
        xor a                   ; back to bank 0, as 128 BASIC expects
        call page
        ld hl,text0
        jr print                ; print and return to Basic

page:   ld b,a                  ; page in RAM bank A at C000h
        ld a,(BANKM)
        and 0F8h                ; keep ROM and screen bits
        or b
        di
        ld (BANKM),a
        ld bc,PAGING
        out (c),a
        ei
        ret

print:  ld a,(hl)               ; print text up to END_TEXT
        cp END_TEXT
        ret z
        rst 10h
        inc hl
        jr print

text0:  db AT,14,2, INK,0, "Back in bank 0, done.", END_TEXT

        bank 1
        org 0C000h
text1:  db AT,6,2, INK,2, "Hello from bank 1 (C000h)", END_TEXT

        bank 3
        org 0C000h
text3:  db AT,10,2, INK,1, "Hello from bank 3 (C000h)", END_TEXT

        end start
