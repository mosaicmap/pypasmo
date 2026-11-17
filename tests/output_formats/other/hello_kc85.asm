; Hello for the Robotron KC 85/2-4 (CAOS):
;   python -m pypasmo --kcc-kc85 hello_kc85.asm hello_kc85.kcc
; In an emulator (JKCEMU): load hello_kc85.kcc; it starts at once (autostart), prints
; the text with the CAOS call OSTR and returns to CAOS.

caos    equ 0F003h              ; CAOS entry point 1: CALL, then DB the call number
ostr    equ 23h                 ; print the string after the call, up to 0

        org 300h
start:  call caos
        db ostr
        db "Hello from pypasmo!", 0Dh, 0Ah
        db "Robotron KC 85", 0Dh, 0Ah, 0
        ret                     ; back to CAOS

        end start
