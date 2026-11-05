"""How a brand's sister locations read in a check_availability result."""

from app.schemas.dto.brands.sister_locations import SisterLocationOption


def render_sister_locations(
    options: list[SisterLocationOption],
) -> list[dict[str, object]]:
    """Each sister location's name, how to reach it and its free times."""

    rendered: list[dict[str, object]] = []
    for option in options:
        entry: dict[str, object] = {
            "name": str(option.name),
            "date": str(option.date),
            "timezone": str(option.timezone),
        }
        optional: dict[str, object | None] = {
            "city": option.city,
            "address": option.address,
            "maps_url": option.maps_url,
            "phone": option.phone_number,
            "chat_link": option.chat_url,
        }
        entry.update({key: str(value) for key, value in optional.items() if value})
        if option.free_times:
            entry["free_times"] = [str(time) for time in option.free_times]

        if option.has_free_stay:
            entry["stay_free"] = True

        rendered.append(entry)

    return rendered
