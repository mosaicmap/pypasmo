; Hello for the Jupiter Ace (16K RAM pack: the code at 4000h):
;   python -m pypasmo --tap-ace --name hello hello_ace.asm hello_ace.tap
; In an emulator: type  0 0 BLOAD hello  and play the tape; the loader (the input line)
; then loads the code and calls it. The code writes into the video RAM and returns to
; Forth with JP (IY).

screen  equ 2400h               ; video RAM: 24 rows of 32 characters, ASCII, + 128 = inverse
row     equ 32

        org 4000h
start:  ld hl,title
        ld de,screen+3*row
        ld b,title_end-title
inv:    ld a,(hl)               ; the title inverse: bit 7
        or 80h
        ld (de),a
        inc hl
        inc de
        djnz inv
        ld hl,hello
        ld de,screen+5*row
        ld bc,hello_end-hello
        ldir
        jp (iy)                 ; back to Forth

title:  db " PYPASMO ON THE JUPITER ACE "
title_end:
hello:  db "Hello, World! (Forth: JP (IY))"
hello_end:

        end start
