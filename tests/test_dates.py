from datetime import date

from mostek_kultura.dates import TZ, infer_year, parse_cz, parse_iso_compact

REF = date(2026, 9, 11)


def test_full_datetime():
    s, e, all_day = parse_cz("12. 9. 2026 13:00")
    assert (s.year, s.month, s.day, s.hour, s.minute) == (2026, 9, 12, 13, 0)
    assert s.tzinfo is TZ and e is None and not all_day


def test_date_only_is_all_day():
    s, e, all_day = parse_cz("12.9.2026")
    assert all_day and e is None and s.hour == 0


def test_od_do():
    s, e, all_day = parse_cz("12.9.2026  od 10:00 do 17:00 hodin")
    assert (s.hour, e.hour, all_day) == (10, 17, False)


def test_range_days():
    s, e, all_day = parse_cz("12.9.2026 až 13.9.2026")
    assert (s.day, e.day, all_day) == (12, 13, True)


def test_antee_spaces_and_short_hour():
    s, _, _ = parse_cz("18. 09. 2026 2:00")
    assert (s.day, s.hour) == (18, 2)


def test_no_year_infers_forward():
    s, _, _ = parse_cz("ne 13. 09. 15:30", ref=REF)
    assert (s.year, s.month, s.day, s.hour) == (2026, 9, 13, 15)
    s, _, _ = parse_cz("po 5. 1. 19:00", ref=REF)
    assert (s.year, s.month) == (2027, 1)


def test_month_words():
    s, _, all_day = parse_cz("sobota: 12. září 2026", ref=REF)
    assert (s.year, s.month, s.day, all_day) == (2026, 9, 12, True)


def test_infer_year_recent_past_stays():
    assert infer_year(1, 9, REF) == 2026
    assert infer_year(1, 7, REF) == 2027


def test_iso_compact():
    d = parse_iso_compact("20260912T130000")
    assert (d.day, d.hour) == (12, 13)
    assert parse_iso_compact("") is None
