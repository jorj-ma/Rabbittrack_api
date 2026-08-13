from datetime import date, timedelta


def age_label(from_date: date, as_of: date | None = None) -> str:
    as_of = as_of or date.today()
    days = max(0, (as_of - from_date).days)

    months, remainder_days = divmod(days, 30)
    weeks = remainder_days // 7

    if months == 0:
        if days == 0:
            return "Today"
        weeks_only = days // 7
        if weeks_only == 0:
            return f"{days} day{'s' if days != 1 else ''}"
        return f"{weeks_only} week{'s' if weeks_only != 1 else ''}"

    label = f"{months} month{'s' if months != 1 else ''}"
    if weeks:
        label += f", {weeks} week{'s' if weeks != 1 else ''}"
    return label


def age_months(from_date: date, as_of: date | None = None) -> int:
    as_of = as_of or date.today()
    return max(0, (as_of - from_date).days) // 30


NEST_BOX_LEAD_DAYS = 26
GESTATION_DAYS_EARLY = 28
GESTATION_DAYS_LATE = 35


def predict_gestation_dates(mating_date: date) -> dict:
    return {
        "expected_nesting_date": mating_date + timedelta(days=NEST_BOX_LEAD_DAYS),
        "expected_birth_date": mating_date + timedelta(days=GESTATION_DAYS_EARLY),
        "expected_birth_date_latest": mating_date + timedelta(days=GESTATION_DAYS_LATE),
    }


def iso_week_bounds(d: date) -> tuple[date, date]:
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday
