#!/bin/sh
# copy built web output into preview/ for the Artifact, pinning MathJax version
rm -rf /tmp/claude-0/pt/preview && cp -r /tmp/claude-0/pt/book/output/web /tmp/claude-0/pt/preview
cd /tmp/claude-0/pt/preview
rm -rf _static/pretext/js/src; find . -name "*.map" -delete
mv index.html redirect-index.html
sed -i 's|npm/mathjax@4/tex-mml-chtml.js|npm/mathjax@4.0.0/tex-mml-svg.js|g' *.html knowl/*/*.html 2>/dev/null
# artifact CSP blocks webfonts from jsdelivr -> use SVG output (font data loads as scripts)
for f in _static/pretext/js/dist/mathjax_startup.js _static/pretext/js/mathjax_startup.js; do [ -f $f ] && sed -i 's|  "chtml": {|  "svg": {\n    "scale": 0.98,\n    "mtextInheritFont": true,\n    "fontCache": "global"\n  },\n  "chtml": {|' $f; done
mv _static static; grep -rl "_static" . | xargs -r sed -i "s|_static/|static/|g"
# (runtime AI button removed: similar problems are now pre-generated into the book)
cp /tmp/claude-0/pt/landing.html index.html; rm -rf /tmp/claude-0/-home-claude/8e775553-2678-5316-984f-6259b46633b1/scratchpad/book; cp -r /tmp/claude-0/pt/preview /tmp/claude-0/-home-claude/8e775553-2678-5316-984f-6259b46633b1/scratchpad/book
