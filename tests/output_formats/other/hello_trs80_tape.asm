; Hello for the TRS-80 Model I / III from a tape (Level II BASIC, no DOS needed):
;   python -m pypasmo --cas-trs --name hello hello_trs80_tape.asm hello_trs80.cas
; In BASIC: SYSTEM, at *? type HELLO (the name on the tape), at *? again type / to run it.
; Model III: answer L (low speed, 500 baud) at Cass?
; The code waits for a key, then returns to BASIC (READY). For a DOS: hello_trs80.asm.

cls     equ 01C9h               ; ROM: clear the screen
dispch  equ 0033h               ; ROM: print the character in A
keyin   equ 0049h               ; ROM: wait for a key, its character in A
basic   equ 1A19h               ; ROM: back to BASIC (READY)

        org 7000h
start:  call cls
        ld hl,text
loop:   ld a,(hl)
        or a
        jr z,key
        call dispch
        inc hl
        jr loop
key:    call keyin              ; wait for a key
        jp basic

text:   db "Hello from pypasmo!", 13
        db "TRS-80, from a tape", 13
        db "Press a key", 13, 0

        end start
