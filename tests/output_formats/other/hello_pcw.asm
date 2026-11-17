; Amstrad PCW: a disk image with the CP/M program HELLO.COM, which prints two lines:
;   python -m pypasmo --dsk-pcw --name hello hello_pcw.asm hello_pcw.dsk
; The disk does not start by itself: start CP/M Plus in the emulator, put the disk into
; drive B: (or into A: after the start) and type B:HELLO (or HELLO).
; The program works on any CP/M; with --bin it is a HELLO.COM file.

bdos    equ 0005h               ; CP/M: call with the function number in C
print   equ 9                   ; BDOS function: print the text at DE up to "$"

        org 100h                ; CP/M loads a .COM at 100h and starts it there
start:  ld c,print
        ld de,text
        call bdos
        ret                     ; back to CP/M
text:   db "Hello from pypasmo!", 13, 10
        db "Z80 assembler based on Pasmo", 13, 10, "$"
        end start
