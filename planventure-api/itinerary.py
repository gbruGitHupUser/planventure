from datetime import date, timedelta

MAX_DAYS = 366


def generate_default_itinerary(start_date, end_date, destination=None):
    """Build an empty day-by-day itinerary template for a trip.

    One entry is created per day from start_date to end_date (inclusive),
    capped at MAX_DAYS entries. The result is JSON-serializable and fits the
    Trip.itinerary column.

    Raises ValueError if the dates are not `date` objects or end_date is
    before start_date.
    """
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise ValueError("start_date and end_date must be date objects")
    if end_date < start_date:
        raise ValueError("end_date must not be before start_date")

    total_days = min((end_date - start_date).days + 1, MAX_DAYS)
    days = []
    for index in range(total_days):
        current = start_date + timedelta(days=index)
        days.append(
            {
                "day": index + 1,
                "date": current.isoformat(),
                "title": f"Day {index + 1}",
                "activities": [],
                "notes": "",
            }
        )

    return {
        "destination": destination,
        "total_days": total_days,
        "days": days,
    }
