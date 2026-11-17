; Hello for the ZX81 (16K RAM), the text in the ZX81 character set:
;   python -m pypasmo --p-zx81 hello_zx81.asm hello_zx81.p
; In an emulator: load hello_zx81.p, it runs at once (line 2 RAND USR VAL "16514").
; The code writes straight into the display file (no ROM calls), then returns to Basic.

d_file  equ 400Ch               ; system variable: address of the display file
row     equ 33                  ; a row of the display file: 32 characters + NEWLINE

        org 16514               ; the code is in the REM line 1 (--p-zx81)
start:  ld hl,(d_file)
        inc hl                  ; row 0, column 0: after the first NEWLINE
        ld de,title
        call print
        ld hl,(d_file)
        ld bc,1+2*row           ; row 2
        add hl,bc
        ld de,hello
        call print
        ld hl,(d_file)
        ld bc,1+4*row           ; row 4
        add hl,bc
        ld de,blocks
        call print
        ld hl,(d_file)
        ld bc,1+6*row           ; row 6
        add hl,bc
        ld de,last
        call printc
        ret                     ; back to Basic: report 0/2

; print: copy the characters at DE to HL up to 0FFh (not a character on the ZX81)
print:  ld a,(de)
        cp 0FFh
        ret z
        ld (hl),a
        inc de
        inc hl
        jr print

; printc: copy a DC_ZX81 string: bit 7 (inverse) marks its last character
printc: ld a,(de)
        inc de
        ld b,a
        and 7Fh                 ; the last character normal again
        ld (hl),a
        inc hl
        bit 7,b
        jr z,printc
        ret

title:  d_zx81i " PYPASMO ON THE ZX81 ", 0FFh       ; all inverse
hello:  d_zx81 "HELLO, WORLD. ", "inverse", 0FFh   ; lower case = inverse
blocks: d_zx81 "GRAPHICS ", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0FFh
last:   dc_zx81 "BIT 7 ENDS THIS TEXT."

        end start
