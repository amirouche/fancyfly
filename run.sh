#!/bin/sh
./cpython/python fancyfly.py in.py > out.js
prettier -w out.js
cat prelude.js out.js > program.js
cat program.js | node -p | cat
