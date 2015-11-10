#!/usr/bin/env bash 
# Clean
rm -f *.o *.dylib

# Make
gcc -std=c99 -arch i386 -arch x86_64 -c ./_factlib.c
gcc -std=c99 -arch i386 -arch x86_64 -dynamiclib -flat_namespace -undefined suppress -o _factlib.dylib _factlib.o

echo "Done."