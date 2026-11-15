# Источники

Все документы лежат в репозитории, контрольные суммы — в `SHA256SUMS` рядом с файлами.
Ссылки на страницы указаны по печатной нумерации документа, если не сказано иное.

## Документы (`docs/datasheets/`)

| Файл | Источник | Что использовано |
|---|---|---|
| `advantech-pcm-3864-3860-users-manual-ed1-1996.pdf` | [Advantech](https://advdownload.advantech.com/productfile/Downloadfile1/1-60I7T/PCM3864%20ed1..pdf), ed.1, август 1996 | с. 2, 5 — PCM-3864 = вариант с C&T 65545; с. 6 и 10 — размещение CN1/CN2 (схематично); с. 8 — CN1/CN2 = PC/104; с. 58–59 — гнёзда female, переходник «male-male», рисунок модуля; с. 67 — таблица CN1/CN2 |
| `pc104-specification-v2.6-2008.pdf` | [PC/104 Consortium](https://pc104.org/wp-content/uploads/2015/02/PC104_Spec_v2_6.pdf), 13.10.2008 | рис. 1 (с. 3) — стек и стойки 0.600 in; разд. 2.3 — ключи; рис. 3 (с. A-3) — габарит, отверстия, положение J1/J2; рис. 4 (с. A-4) — корпус разъёма, 0.800/0.400 in, хвост; табл. 2 (с. B-2) — назначение выводов; рис. 7 (с. D-2) — стойка |
| `pc104-specification-v2.5-2003.pdf` | [зеркало rogerarrick.com](https://www.rogerarrick.com/pc104faq/PC104SpecV2_5.pdf) | сверка рис. 3 с v2.6 (совпадает); история переименований сигналов |
| `samtec-esw-esq-elevated-sockets-f226-rev16jun26.pdf` | [Samtec](https://suddendocs.samtec.com/catalog_english/esq_th.pdf), F-226 Rev 16JUN26 | таблица PC/104: J1/P1 stackthrough ESQ-132-14/-39-G-D, J2/P2 ESQ-120-14/-39-G-D; стиль -39: A = .480 in, B = .435 in; штырь .025 in квадрат; глубина ввода 3.68–6.35 мм |
| `samtec-esw-esq-catalog-2011.pdf` | [Farnell](https://www.farnell.com/datasheets/1304221.pdf), Samtec 2011 | та же таблица PC/104 в более раннем каталоге |
| `samtec-esq-recommended-pcb-layout-esq-sdt.pdf` | [Samtec ESQ-SDT](https://suddendocs.samtec.com/prints/esq-sdt.pdf) | отверстие **Ø .040 in (1.02 мм)**, шаг 2.54 мм |
| `samtec-esq-strip-asm-drawing.pdf` | [Samtec](https://suddendocs.samtec.com/prints/esq-1xx-xx-x-x-xxx-xx-x-xx-mkt.pdf) | чертёж серии ESQ: ширина .195 in, длина .100 × N + .020 in |

Страница продукта Samtec ESQ-132-39-G-D (2026-11-15): деталь в продаже, но отмечена как доступная
только существующим клиентам. 3D-модели Samtec выдаются после ввода e-mail, поэтому не скачивались
(см. [models.md](models.md)).

### Лицензионные пометки

Руководство Advantech запрещает воспроизведение без разрешения (Copyright notice, 2-я страница PDF). На чертеже Samtec
`samtec-esq-strip-asm-drawing.pdf` стоит пометка о конфиденциальности. Оба файла свободно скачиваются
с сайтов производителей. В репозиторий они положены по правилу проекта «все документы в репо».
**Перед публикацией репозитория владелец решает**, оставлять ли их в открытом доступе или заменить
ссылками.

## Фотографии (`docs/references/photos/`)

| Файл | Источник | Что видно |
|---|---|---|
| `pcm-3860-64-revA1-01-3-top-ebay.jpg` | фото продавца eBay, [i.ebayimg.com …xpoAAOSw8qNiXxRv](https://i.ebayimg.com/images/g/xpoAAOSw8qNiXxRv/s-l1600.jpg) | CN2 — внутренний длинный разъём; «A32» у COM1; CHIPS F65545 |
| `pcm-3860-64-revA1-01-3-bottom-ebay.jpg` | фото продавца eBay, [i.ebayimg.com …H4IAAOSwauZiXxRe](https://i.ebayimg.com/images/g/H4IAAOSwauZiXxRe/s-l1600.jpg) | маркировка «PCM-3860/64 Rev.A1 01-3», контур разъёмов, отступы J2 0.8/0.4 in |

Фото чужие и используются только для сверки ориентации. Выводы — в [mechanics.md](mechanics.md).

## Производство

[Возможности JLCPCB](https://jlcpcb.com/capabilities/pcb-capabilities) — по правилам проекта retro535
(дорожка ≥ 0.18 мм, зазор 0.20 мм, медь до края ≥ 0.30 мм, текст ≥ 1.0 мм / 0.15 мм). Для этой платы
важны только отверстия 1.02 и 3.18 мм, поясок 0.34 мм и шелкография. Страница JLCPCB в этой сессии
заново не открывалась; перед заказом сверить её с [manufacturing.md](manufacturing.md).
