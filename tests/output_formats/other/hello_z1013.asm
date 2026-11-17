; Hello for the Robotron Z 1013:
;   python -m pypasmo --z80-z1013 hello_z1013.asm hello_z1013.z80
; In an emulator (JKCEMU): load hello_z1013.z80, start it with  J 100  in the monitor
; (or the emulator starts it). The code writes into the video RAM and then waits in a
; loop (reset to get back to the monitor).

screen  equ 0EC00h              ; video RAM: 32 rows of 32 characters (ASCII)
row     equ 32

        org 100h
start:  ld hl,hello
        ld de,screen+10*row
        ld bc,hello_end-hello
        ldir
        ld hl,second
        ld de,screen+12*row
        ld bc,second_end-second
        ldir
stop:   jr stop                 ; wait here

hello:  db "Hello from pypasmo!"
hello_end:
second: db "Robotron Z 1013"
second_end:

        end start
