# Математик Анализ 2 — PreTeXt ном

Analysis2_16 LaTeX номоос хөрвүүлсэн PreTeXt төсөл. Хичээл бүр = нэг `source/chapters/chNN.ptx` файл.

## Build хийх
```
pip install pretext        # PreTeXt CLI (2.55+)
pretext build web          # HTML -> output/web/
pretext view web           # браузерт харах
pretext build print        # PDF (xelatex, кирилл фонт хэрэгтэй)
```

## Бүтэц
- `source/main.ptx` — номын үндсэн файл, бүлгүүдийг xi:include-ээр оруулна.
- `source/docinfo.ptx` — LaTeX макро (`\R`, `\N`, ...) болон монгол нэршил (`<rename>`: Теорем, Жишээ, Заавар, Хариу, Бодолт ...).
- `source/chapters/chNN.ptx` — хичээл бүр: урьдчилсан дасгал (AI) → лекцийн хэсгүүд (хэсэг бүрийн төгсгөлд "Шалгах дасгал (AI)") → Семинар → Гэрийн даалгавар (+ "Нэмэлт бодлого (AI)").
- `publication/publication.ptx` — гаралтын тохиргоо.

## AI-аар үүсгэсэн агуулга
AI-ийн бүх агуулга `component="ai"` атрибуттай. Үүнийг номноос хасах бол `publication/publication.ptx` дотор
`<version include="ai"/>` мөрийг `<version include="none"/>` болго.
Багшийн өөрийн материал (теорем, баталгаа, жишээ, семинар, гэрийн даалгавар) өөрчлөгдөөгүй.

## tools/
- `tex2ptx.py` — LaTeX → PreTeXt хөрвүүлэгч (нэг удаагийн; одоо .ptx файлуудаа шууд засна).
- `merge_ai.py`, `ai/chNN.xml` — AI дасгалуудын эх, хөрвүүлсэн бүлэгт оруулах скрипт.

## Төстэй бодлого (AI)
Дасгал бүрийн бодолтын хэсэгт «Төстэй бодлого (AI)» гэсэн нэмэлт бодолт байна: ижил сэдэв, аргатай шинэ бодлого, заавар, хариу. Нэг удаа үүсгэж номонд суулгасан тул уншихад токен зарцуулахгүй. Тооцооны хариуг sympy-гаар шалгасан, баталгааны бодлогыг багш шалгах шаардлагатай. Бүгд `component="ai"` тул publication.ptx дахь `<version include="ai"/>`-г авбал алга болно.
Эх: `tools/sim/simNN.json` (түлхүүр нь бодлогын текстийн hash). `tools/rebuild.sh` дахин хөрвүүлэхдээ `tools/sim/add_similar.py`-г ажиллуулна.
