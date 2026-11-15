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
| `ess-es1868-datasheet.pdf` | [theretroweb](https://theretroweb.com/chip/documentation/es1868-ess-65a2c4acefa2b084162955.pdf), ESS 1995–1996 | этап 2: ISA 8 бит, IRQA–F/DRQA–D, PnP и «bypass key», EEPROM 93LC66 (рис. 15), кварц 14.318 МГц (t14), пример заголовка EEPROM |
| `ess-es1868-product-brief.pdf` | [theretroweb](https://theretroweb.com/chip/documentation/es1868-65982d221ed99238102939.pdf) | этап 2: краткие характеристики ES1868 |
| `st-tea2025-2012.pdf` | [theretroweb](https://theretroweb.com/chip/documentation/tea2025-6774092b5a20f409874196.pdf), ST 2012 | этап 2: усилитель донорской карты (CM2025B — его аналог) |
| `btc-1853l-1857l-quick-install-guide-1997.pdf` | [theretroweb](https://theretroweb.com/expansioncard/documentation/1853l-1857l-quick-install-guide-6822872e7c19d307377926.pdf), 20.01.1997 | этап 2: инструкция донорской карты (скан) |
| `cui-sj1-352xn.pdf` | [CUI/Same Sky](https://www.cuidevices.com/product/resource/pdf/sj1-352xn.pdf), 09/12/2024 | этап 2: гнёзда 3.5 мм SJ1-3523N — выводы 1 sleeve / 2 tip / 3 ring, высота ~6 мм, рекомендованная разводка с. 2 (пазы 1.5 × 0.8 мм, отверстия Ø1.2 мм) |
| `ti-sn74hct138.pdf` | [Texas Instruments](https://www.ti.com/lit/ds/symlink/sn74hct138.pdf), Rev. F | этап 2: U2, дешифратор A15–A12 + AEN, как U2 74LS138 на рис. 28 ESS |
| `microchip-93aa66-93lc66-93c66.pdf` | [Microchip DS21795E](https://ww1.microchip.com/downloads/en/DeviceDoc/21795E.pdf) | этап 2: U3 93C66, распиновка DIP-8, вывод ORG (на GND — организация 512 × 8) |
| `national-an-1130-game-midi-ports-1999.pdf` | [bitsavers](https://bitsavers.mirrorservice.org/components/national/_appNotes/AN-1130.pdf), National Semiconductor 1999 | этап 2: раскладка штыревого разъёма game/MIDI 2 × 8 (с. 1): 1, 2, 15 = +5 В; 7, 9 = GND; 8 = MIDI out; 14 = MIDI in |
| `samtec-esq-strip-asm-drawing.pdf` | [Samtec](https://suddendocs.samtec.com/prints/esq-1xx-xx-x-x-xxx-xx-x-xx-mkt.pdf) | чертёж серии ESQ: ширина .195 in, длина .100 × N + .020 in |

Страница продукта Samtec ESQ-132-39-G-D (2026-11-15): деталь в продаже, но отмечена как доступная
только существующим клиентам. 3D-модели Samtec выдаются после ввода e-mail, поэтому не скачивались
(см. [models.md](models.md)).

### Лицензионные пометки

Запрет воспроизведения без разрешения стоит в руководстве Advantech (Copyright notice, 2-я страница PDF)
и в даташите ESS ES1868 (с. 3). На чертеже Samtec `samtec-esq-strip-asm-drawing.pdf` — пометка
о конфиденциальности. Все три файла свободно скачиваются из сети и лежат в репозитории по правилу
проекта «все документы в репо». Репозиторий на GitHub уже опубликован: если он публичный, владелец
решает, оставлять ли эти файлы или заменить их ссылками.

## Фотографии (`docs/references/photos/`)

| Файл | Источник | Что видно |
|---|---|---|
| `pcm-3860-64-revA1-01-3-top-ebay.jpg` | фото продавца eBay, [i.ebayimg.com …xpoAAOSw8qNiXxRv](https://i.ebayimg.com/images/g/xpoAAOSw8qNiXxRv/s-l1600.jpg) | CN2 — внутренний длинный разъём; «A32» у COM1; CHIPS F65545 |
| `pcm-3860-64-revA1-01-3-bottom-ebay.jpg` | фото продавца eBay, [i.ebayimg.com …H4IAAOSwauZiXxRe](https://i.ebayimg.com/images/g/H4IAAOSwauZiXxRe/s-l1600.jpg) | маркировка «PCM-3860/64 Rev.A1 01-3», контур разъёмов, отступы J2 0.8/0.4 in |
| `btc-1853l-front-theretroweb-oerg866.jpg` | [theretroweb, фото Eric Voirin (oerg866)](https://theretroweb.com/expansioncards/s/behavior-tech-btc-1853l) | донор этапа 2: ES1868F, кварц 14.31818 МГц, 93C66, CM2025B, 74LS138 |
| `btc-1853l-back-theretroweb-oerg866.jpg` | там же | обратная сторона донора |

Фото чужие и используются только для сверки. Фото с theretroweb уменьшены до 3200 px, метаданные
EXIF (в том числе GPS) удалены. Выводы — в [mechanics.md](mechanics.md) и [audio-options.md](audio-options.md).

## Открытые проекты (только факты, без копирования)

- [hkzlab/ES1868_ISA8](https://github.com/hkzlab/ES1868_ISA8) — 8-битная ISA-карта на ES1868F,
  лицензия CC BY-NC-SA 4.0. Схема и плата оттуда **не копировались**. Использованы два факта:
  заголовок дампа EEPROM 93C66 типовой карты `A5 59 A7 CB 10 53 00 0C` совпадает с примером ESS
  (прил. A даташита), то есть такие карты разводят IRQ/DMA по эталону ESS; конфигурация в DOS
  делается утилитой ESSCFG или UNISOUND.
- [PicoGUS](https://github.com/polpo/picogus) — рассмотрен как вариант C (железо CERN-OHL-P v2,
  прошивка GPL v2), см. [audio-options.md](audio-options.md).

## Производство

[Возможности JLCPCB](https://jlcpcb.com/capabilities/pcb-capabilities) — по правилам проекта retro535
(дорожка ≥ 0.18 мм, зазор 0.20 мм, медь до края ≥ 0.30 мм, текст ≥ 1.0 мм / 0.15 мм). Для этой платы
важны только отверстия 1.02 и 3.18 мм, поясок 0.34 мм и шелкография. Страница JLCPCB в этой сессии
заново не открывалась; перед заказом сверить её с [manufacturing.md](manufacturing.md).
