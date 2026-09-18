"""Live web information — weather, search."""
import urllib.request, urllib.parse, json
from .registry import register


def _geocode(city):
    url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
        {"name": city, "count": 1, "language": "en", "format": "json"})
    with urllib.request.urlopen(url, timeout=8) as r:
        d = json.loads(r.read().decode())
    res = d.get("results") or [None]
    r0 = res[0]
    if not r0: return None
    return r0["latitude"], r0["longitude"], r0.get("name", city), r0.get("country", "")


@register("web", "Get live web information such as weather.", {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["weather"]},
        "city": {"type": "string"},
    },
    "required": ["action"],
})
def web(args: dict) -> str:
    a = args.get("action")
    if a == "weather":
        city = (args.get("city") or "London").strip()
        geo = _geocode(city)
        if not geo: return f"Could not find: {city}"
        lat, lon, name, country = geo
        url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "timezone": "auto"})
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read().decode())
        c = data.get("current", {})
        return (f"Weather in {name}, {country}: "
                f"{c.get('temperature_2m','?')}°C, "
                f"humidity {c.get('relative_humidity_2m','?')}%, "
                f"wind {c.get('wind_speed_10m','?')} km/h")
    raise ValueError(f"Unknown web action: {a}")