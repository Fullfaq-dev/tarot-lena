from datetime import date


def _reduce(n: int, *, keep_master: bool = True) -> int:
    while n > 9:
        if keep_master and n in (11, 22, 33):
            return n
        n = sum(int(d) for d in str(n))
    return n


def life_path_number(birth: date) -> int:
    digits = f"{birth.day:02d}{birth.month:02d}{birth.year}"
    total = sum(int(d) for d in digits)
    return _reduce(total)


def personal_year_number(birth: date, year: int | None = None) -> int:
    y = year or date.today().year
    total = birth.day + birth.month + y
    return _reduce(total, keep_master=False)


def day_number(for_day: date | None = None) -> int:
    d = for_day or date.today()
    total = d.day + d.month + d.year
    return _reduce(total, keep_master=False)
