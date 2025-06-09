INCLUDE Irvine32.inc

.data
str0 BYTE "Enter number of rows:",0
r dd ?
str1 BYTE "Enter number of columns:",0
c12 dd ?
str2 BYTE "Drawing rectangle:",0Dh,0Ah,0
col dd ?
str3 BYTE "*",0
str4 BYTE 0Dh,0Ah,0
str5 BYTE "Finished!",0
.code
main PROC
    lea   edx, str0
    call  WriteString
    call ReadInt
    mov [r], eax
    lea   edx, str1
    call  WriteString
    call ReadInt
    mov [c12], eax
    lea   edx, str2
    call  WriteString
Loop0:
    push DWORD PTR [r]
    push 0
    pop ebx
    pop eax
    cmp eax, ebx
jle EndLoop0
    push DWORD PTR [c12]
    pop eax
    mov [col], eax

Loop1:
    push DWORD PTR [col]
    push 0
    pop ebx
    pop eax
    cmp eax, ebx
jle EndLoop1
    lea   edx, str3
    call  WriteString
    push DWORD PTR [col]
    push 1
    pop ebx
    pop eax
    sub eax, ebx
    push eax
    pop eax
    mov [col], eax

    jmp   Loop1
EndLoop1:
    lea   edx, str4
    call  WriteString
    push DWORD PTR [r]
    push 1
    pop ebx
    pop eax
    sub eax, ebx
    push eax
    pop eax
    mov [r], eax

    jmp   Loop0
EndLoop0:
    lea   edx, str5
    call  WriteString
exit	 
main ENDP
END main
