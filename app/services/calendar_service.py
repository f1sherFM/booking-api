from datetime import UTC, datetime


def _format_ics_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _escape_ics_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\r\n", r"\n")
        .replace("\n", r"\n")
    )


def _to_ics_status(status: str) -> str:
    normalized = status.upper()
    if normalized in {"CONFIRMED", "CANCELLED"}:
        return normalized
    return "CONFIRMED"


def build_booking_calendar_ics(
    booking_id: int,
    slot_start_at: datetime,
    slot_end_at: datetime,
    specialist_display_name: str,
    client_email: str,
    booking_status: str,
) -> str:
    summary = _escape_ics_text(f"Booking with {specialist_display_name}")
    description = _escape_ics_text(
        f"Booking #{booking_id}\\nSpecialist: {specialist_display_name}\\nClient: {client_email}"
    )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Booking API//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:booking-{booking_id}@booking-api.local",
        f"DTSTAMP:{_format_ics_datetime(datetime.now(UTC))}",
        f"DTSTART:{_format_ics_datetime(slot_start_at)}",
        f"DTEND:{_format_ics_datetime(slot_end_at)}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"STATUS:{_to_ics_status(booking_status)}",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    return "\r\n".join(lines)
