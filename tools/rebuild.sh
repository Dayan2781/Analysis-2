#!/bin/sh
# rebuild chapters NN... : convert + merge AI
cd /tmp/claude-0/pt
for n in "$@"; do
  python3 tex2ptx.py /mnt/project-files/analysis2/Analysis2_16/weeks/week${n}_*.tex conv/ch$n.ptx $(expr $n + 0) 2>&1 | sed 's/^/  /'
  if [ -f ai/ch$n.xml ]; then python3 merge_ai.py conv/ch$n.ptx ai/ch$n.xml book/source/chapters/ch$n.ptx; else cp conv/ch$n.ptx book/source/chapters/ch$n.ptx; fi
  if [ -f sim/gen/sim$n.json ]; then python3 sim/add_similar.py book/source/chapters/ch$n.ptx sim/gen/sim$n.json; fi
done
