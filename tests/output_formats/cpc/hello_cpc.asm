; Hello for the Amstrad CPC 464/664/6128 (the firmware prints the text):
;   python -m pypasmo --amsdos --name hello hello_cpc.asm hello_cpc.bin
;   python -m pypasmo --cdt    --name hello hello_cpc.asm hello_cpc.cdt
;   python -m pypasmo --cdt-wloader --name hello hello_cpc.asm hello_cpc_bas.cdt
;   python -m pypasmo --dsk-cpc --name hello hello_cpc.asm hello_cpc.dsk
;   python -m pypasmo --sna-cpc6128 hello_cpc.asm hello_cpc6128.sna
;   python -m pypasmo --sna-cpc464 hello_cpc.asm hello_cpc464.sna
; .bin (Amsdos header): RUN "hello" from a disk, or drop it into an emulator;
; .cdt: RUN "" (the code starts at once); _bas.cdt: RUN "" (a Basic loader, then CALL);
; .dsk: RUN "hello"; .sna: a CPC 6128 / 464 snapshot, the code runs at once, back to Basic
; after it.
; The code waits for a key, then returns. After LOAD "hello": CALL &4000 the CPC is back
; in Basic (Ready); a program started with RUN (also RUN "" from a tape) has no Basic to
; return to, so the CPC resets then (as on the real machine).

txt_output equ 0BB5Ah           ; firmware: print the character in A (keeps the registers)
km_wait_char equ 0BB06h         ; firmware: wait for a key, its character in A

        org 4000h
start:  ld hl,text
loop:   ld a,(hl)
        or a
        jr z,key
        call txt_output
        inc hl
        jr loop
key:    call km_wait_char       ; wait for a key
        ret                     ; back to Basic (after RUN: reset)

text:   db "Hello from pypasmo!", 13, 10
        db "Amstrad CPC", 13, 10
        db "Press a key", 13, 10, 0

        end start
