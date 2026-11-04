# PCone sitewatch — owner canon and purpose (Roman, 2026-11-04)

## Why this exists
The site keeps breaking after publishes (old header returning, hours wrong, prices in meta, header wider than screen,
stale CSS cache). Goal: no breakage reaches customers unnoticed; mechanical ones are fixed by Ron's server cron,
everything else goes to the owner with proof. Priority order when in doubt: 1) never a false "all clean",
2) zero false positives on a clean copy, 3) speed/cost.

## Seed canon.json (owner-approved facts; rules must read these, never hardcode)
- hours: Sun 09:00-19:00; Mon-Thu 10:00-19:00; Fri 09:00-14:00; Sat closed; lunch break 13:30-15:00 on Sun-Thu
  (NOT Mon-Thu - "пн-чт / ב׳-ה׳" for the break is a defect). Check visible text in all 5 languages AND JSON-LD openingHours.
- phone: 09-8345676; address: Pinhas Lavon 18, Netanya; contact email: ron@pcone.co.il (info@pconelab.co.il on pages = defect).
- meta description / og:description / twitter:description: no prices at all, everywhere (AV product pages included);
  only allowed price: diagnostics 200 ₪.
- approved price facts (body text; flag contradictions, do not invent others): diagnostics 200 ₪; board diagnostics 300 ₪;
  data recovery from 400 ₪; GPU servicing 350-750 ₪; phone water damage from 350 ₪; screen prices only as "from N ₪".
- banned anywhere (all languages): urgent/express diagnostics, "within 4 hours"/"תוך 4 שעות" diagnostics;
  "5,000+ repairs" (use "since 2007"); buying used devices / trade-in ("יד שנייה לקנייה", buy2sell);
  claiming to be an authorized Apple service; the old site header with the blue strip (must not exist; Arena header only).
- Apple warranty canon (ru): «Гарантия на работу и на детали. На детали — до 3 лет в зависимости от типа детали;
  на работу — всегда, по типу ремонта. Восстановление данных не гарантируется.»
- «бесплатно»/"free" claims: report only (owner decision), never auto-fix.

## Seed allowlist (owner decisions)
- gta6/article-regional-versions keeps its old header (owner decision 2026-11-04).
- footer link «Б/у техника» stays (owner decision 2026-10-27) - not a trade-in defect.
- gta-rp pages (5 languages) are never edited: report findings there as info only, never safe_auto.

## Severity guide
critical: wrong hours/phone/email, price in meta, old header, banned claim, page 4xx/5xx, header/menu overflow on 390.
high: broken asset/link, JSON-LD invalid, hreflang mismatch, missing language page, cache-bust missing.
medium/info: everything else.
