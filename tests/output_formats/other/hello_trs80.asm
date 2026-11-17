; Hello for the TRS-80 Model I / III (the ROM prints the text), a /CMD file:
;   python -m pypasmo --trs hello_trs80.asm hello_trs80.cmd
; Load it from a DOS (TRSDOS, LDOS, NEWDOS: type HELLO), or let the emulator load it.
; The code waits for a key, then jumps to the DOS (402Dh): run it from a DOS; loaded
; without a DOS there is nothing at 402Dh. For a tape (back to BASIC): hello_trs80_tape.asm.

cls     equ 01C9h               ; ROM: clear the screen
dispch  equ 0033h               ; ROM: print the character in A
keyin   equ 0049h               ; ROM: wait for a key, its character in A
dos     equ 402Dh               ; back to the DOS ("DOS Ready")

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
        jp dos

text:   db "Hello from pypasmo!", 13
        db "TRS-80", 13
        db "Press a key", 13, 0

        end start
