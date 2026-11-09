"""Регрессия HOURS_TEXT: день двумя интервалами, вложенные блоки, иврит/французский/арабский.

Откуда взялось (10.11.2026): сторож выдавал 13 ложных находок HOURS_TEXT, 5 из них
критичными. Живые страницы пишут перерыв внутри дня одной ячейкой
(«Пн-чт 10:00-13:30, 15:00-19:00»), а правило брало последний интервал как часы дня
и теряло перерыв. Плюс в разборе дней не было ивритских שני/שלישי/רביעי/חמישי,
французских mardi/mercredi и арабских الثلاثاء/الأربعاء, а виджет расписания отдавал
контейнер и его же детей — каждый ребёнок проверялся как отдельная строка часов.
"""

from __future__ import annotations

from pathlib import Path

from pcone_sitewatch.canon import load
from pcone_sitewatch.htmlutil import Page
from pcone_sitewatch.rules import hours_text
from pcone_sitewatch.rules.hourslib import _days, read_visible, visible_problem

CANON = load()
BASE = "https://pconelab.co.il"

# Живые строки часов с pconelab.co.il (сняты 10.11.2026) — все верные.
GOOD_LINES = [
    "Часы работы Воскресенье 9:00-19:00 Пн-чт 10:00-13:30, 15:00-19:00 Пятница 9:00-14:00 "
    "Суббота закрыто Перерыв 13:30-15:00, Вс-Чт",
    "Opening hours Sunday 9:00-19:00 Mon-Thu 10:00-13:30, 15:00-19:00 Friday 9:00-14:00 "
    "Saturday Closed Break 13:30-15:00, Sun-Thu",
    "Horaires Dimanche 9:00-19:00 Lun.-jeu. 10:00-13:30, 15:00-19:00 Vendredi 9:00-14:00 "
    "Samedi Fermé Pause 13:30-15:00, dim-jeu",
    "שעות פעילות א׳ (ראשון) 9:00-19:00 ב׳-ה׳ 10:00-13:30, 15:00-19:00 ו׳ (שישי) 9:00-14:00 "
    "שבת סגור הפסקה 13:30-15:00, א׳-ה׳",
    "ساعات العمل الأحد 9:00-19:00 الاثنين-الخميس 10:00-13:30, 15:00-19:00 الجمعة 9:00-14:00 "
    "السبت مغلق استراحة 13:30-15:00 ، الأحد-الخميس",
]

# Виджет расписания: контейнер со всеми днями и те же дни детьми (как на /av/contacts.html).
WIDGET_DAYS = [
    '<p class="p7c-hours">שעות פעילות … ראשון 9:00–13:30, 15:00–19:00 שני 10:00–13:30, 15:00–19:00 '
    "שלישי 10:00–13:30, 15:00–19:00 רביעי 10:00–13:30, 15:00–19:00 חמישי 10:00–13:30, 15:00–19:00 "
    "שישי 9:00–14:00 שבת סגור</p>",
    '<p class="hours-day">ראשון 9:00–13:30, 15:00–19:00</p>',
    '<p class="hours-day">שני 10:00–13:30, 15:00–19:00</p>',
    '<p class="hours-day">שלישי 10:00–13:30, 15:00–19:00</p>',
    '<p class="hours-day">רביעי 10:00–13:30, 15:00–19:00</p>',
    '<p class="hours-day">חמישי 10:00–13:30, 15:00–19:00</p>',
    '<p class="hours-day">שישי 9:00–14:00</p>',
    '<p class="hours-day">שבת סגור</p>',
]


def _page(html: str, tmp_path: Path) -> Page:
    return Page(BASE + "/x.html", "x.html", f"<html><body>{html}</body></html>", tmp_path, tmp_path / "x.html")


def test_two_intervals_in_one_cell_are_a_day_with_break():
    for line in GOOD_LINES:
        problem = visible_problem(read_visible(line, CANON), CANON)
        assert problem is None, f"{line} → {problem}"


def test_two_intervals_give_open_close_and_break():
    read = read_visible(GOOD_LINES[0], CANON)
    assert read["opens"]["mon"] == ("10:00", "19:00")
    assert read["opens"]["sun"] == ("09:00", "19:00")
    assert ("13:30", "15:00") in read["break_ranges"]
    assert {"mon", "tue", "wed", "thu"} <= read["break_days"]


def test_two_intervals_wrong_close_is_still_flagged():
    bad = "Вс 9:00-19:00 · Пн-Чт 10:00-13:30, 15:00-20:00 · Пт 9:00-14:00 · Сб закрыто · перерыв 13:30-15:00 (вс-чт)"
    problem = visible_problem(read_visible(bad, CANON), CANON)
    assert problem and "mon 10:00-20:00" in problem


def test_two_intervals_wrong_gap_is_not_swallowed():
    bad = "Вс 9:00-19:00 · Пн-Чт 10:00-13:30, 16:00-19:00 · Пт 9:00-14:00 · Сб закрыто"
    read = read_visible(bad, CANON)
    assert ("13:30", "16:00") in read["break_ranges"]


def test_hebrew_full_day_names_are_days():
    assert _days("שני 10:00-19:00") == {"mon"}
    assert _days("שלישי 10:00-19:00") == {"tue"}
    assert _days("רביעי 10:00-19:00") == {"wed"}
    assert _days("חמישי 10:00-19:00") == {"thu"}


def test_hebrew_common_word_is_not_a_day():
    # «שני» без времени рядом — это «два/второй», а не понедельник.
    assert _days("שני מחשבים במלאי") == set()
    assert _days("השני בתור") == set()


def test_french_and_arabic_missing_days_are_days():
    assert _days("Mardi 10:00-19:00") == {"tue"}
    assert _days("Mercredi 10:00-19:00") == {"wed"}
    assert _days("الثلاثاء 10:00-19:00") == {"tue"}
    assert _days("الأربعاء 10:00-19:00") == {"wed"}


def test_nested_widget_children_are_not_checked_alone(tmp_path: Path):
    page = _page("".join(WIDGET_DAYS), tmp_path)
    assert len(page.parsed()["hours"]) == 8
    assert hours_text.check(page, CANON) == []


def test_fragment_without_saturday_is_still_flagged(tmp_path: Path):
    # Обратная проверка: правило не должно замолчать. Подвал без субботы — настоящая дыра.
    page = _page(
        '<p class="p7c-hours">Sun 9:00–19:00 Mon–Thu 10:00–19:00 Fri 9:00–14:00</p>',
        tmp_path,
    )
    found = hours_text.check(page, CANON)
    assert found and "saturday not closed" in found[0].evidence


def test_wrong_hours_are_still_flagged(tmp_path: Path):
    page = _page(
        '<p class="p7c-hours">Вс 9:00-19:00 · Пн-Чт 10:00-13:30, 15:00-21:00 · Пт 9:00-14:00 · Сб закрыто</p>',
        tmp_path,
    )
    found = hours_text.check(page, CANON)
    assert found and "mon 10:00-21:00" in found[0].evidence


def test_russian_vyhodnoy_means_closed():
    read = read_visible("Вс 9:00-19:00 · Пн-Чт 10:00-19:00 · Пт 9:00-14:00 · Сб выходной · перерыв 13:30-15:00", CANON)
    assert read["sat_closed"] is True
    assert visible_problem(read, CANON) is None
