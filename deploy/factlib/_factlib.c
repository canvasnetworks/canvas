#include <stdio.h>

char
decode_hex(char input) {
    static char hex[] = "0123456789ABCDEF";
    int i; // I hate you, C before C99.
    for (i = 0; i < 16; ++i) {
        if (input == hex[i]) {
            return i;
        }
    }
    return 0;
}

void
nginx_unescape(char* inp)
{
    char* outp = inp;
    while (*inp) {
        if (*inp == '\\' && *(inp+1) == 'x') {
            *outp++ = (decode_hex(*(inp+2)) << 4) + decode_hex(*(inp+3));
            inp += 4;
        } else {
            *outp++ = *inp++;
        }
    }
    *outp = 0;
}