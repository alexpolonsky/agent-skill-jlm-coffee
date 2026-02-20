#!/usr/bin/env python3
"""Jerusalem specialty coffee shop finder - queries the public Firestore database."""

import argparse
import json
import os
import random
import re
import sys
import tempfile
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

PROJECT = "specialy-coffee-finder"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"
SITE_URL = "https://coffee.amsterdamski.com"

CACHE_TTL = 3600  # 1 hour
CACHE_DIR = os.path.join(tempfile.gettempdir(), "jlm-coffee")
CACHE_FILE = os.path.join(CACHE_DIR, "shops.json")
KEY_CACHE_FILE = os.path.join(CACHE_DIR, "api_key")

_api_key = None

AMENITY_LABELS = {
    "wifi": "WiFi",
    "dogs": "Dog-friendly",
    "laptop": "Laptop-friendly",
    "outdoor": "Outdoor seating",
    "accessible": "Wheelchair accessible",
    "vegan": "Vegan options",
    "kids": "Kid-friendly",
    "quiet": "Quiet atmosphere",
    "smoking": "Smoking area",
    "local-roasting": "Local roasting",
    "sell-beans": "Sells beans",
    "filter-coffee": "Filter coffee",
    "kosher": "Kosher",
    "open-saturday": "Open Saturday",
    "power": "Power outlets",
    "parking": "Parking",
}

DAY_NAMES_HE = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
DAY_NAMES_EN = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# --- Color support ---

_use_color = False


def _init_color(no_color_flag):
    global _use_color
    if no_color_flag or os.environ.get("NO_COLOR"):
        _use_color = False
    elif not sys.stdout.isatty():
        _use_color = False
    else:
        _use_color = True


def c(text, code):
    if not _use_color:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(text):
    return c(text, "32")


def red(text):
    return c(text, "31")


def yellow(text):
    return c(text, "33")


def bold(text):
    return c(text, "1")


def dim(text):
    return c(text, "2")


def brown(text):
    return c(text, "38;5;130")


# --- API key discovery ---


def _get_api_key():
    """Get Firebase API key, from cache or by reading the site's JS bundle."""
    global _api_key
    if _api_key:
        return _api_key

    # Check cached key (same TTL as shop data)
    try:
        if os.path.exists(KEY_CACHE_FILE):
            age = time.time() - os.path.getmtime(KEY_CACHE_FILE)
            if age < CACHE_TTL:
                with open(KEY_CACHE_FILE, "r") as f:
                    key = f.read().strip()
                    if key:
                        _api_key = key
                        return _api_key
    except OSError:
        pass

    # Fetch from site
    try:
        html = urllib.request.urlopen(SITE_URL, timeout=10).read().decode()
        scripts = re.findall(r'src="([^"]+\.js[^"]*)"', html)
        for src in scripts:
            url = src if src.startswith("http") else SITE_URL + src
            js = urllib.request.urlopen(url, timeout=10).read().decode()
            match = re.search(r"AIza[A-Za-z0-9_-]{35}", js)
            if match:
                _api_key = match.group(0)
                try:
                    os.makedirs(CACHE_DIR, exist_ok=True)
                    with open(KEY_CACHE_FILE, "w") as f:
                        f.write(_api_key)
                except OSError:
                    pass
                return _api_key
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"Error: Could not fetch API key from {SITE_URL} - {e}", file=sys.stderr)
        sys.exit(1)

    print("Error: Could not find Firebase API key in site source", file=sys.stderr)
    sys.exit(1)


# --- Cache ---

_force_fresh = False


def _read_cache():
    """Return cached shops list or None if stale/missing."""
    if _force_fresh:
        return None
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        age = time.time() - os.path.getmtime(CACHE_FILE)
        if age > CACHE_TTL:
            return None
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(shops):
    """Write shops list to cache file."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(shops, f, ensure_ascii=False)
    except OSError:
        pass  # cache is best-effort


def get_all_shops():
    """Get all approved shops, from cache if fresh, otherwise from API."""
    cached = _read_cache()
    if cached is not None:
        return cached
    shops = query_shops()
    _write_cache(shops)
    return shops


# --- Firestore API ---


def firestore_request(path, method="GET", body=None):
    api_key = _get_api_key()
    url = f"{BASE_URL}{path}"
    sep = "&" if "?" in url else "?"
    url += f"{sep}key={api_key}"

    req = urllib.request.Request(url)
    req.add_header("Content-Type", "application/json")

    data = json.dumps(body).encode() if body else None
    if method == "POST":
        req.method = "POST"

    try:
        with urllib.request.urlopen(req, data=data, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            err = json.loads(error_body)
            print(f"Error: {err.get('error', {}).get('message', error_body)}", file=sys.stderr)
        except json.JSONDecodeError:
            print(f"Error: HTTP {e.code} - {error_body[:200]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not connect - {e.reason}", file=sys.stderr)
        sys.exit(1)


def extract_value(field):
    if "stringValue" in field:
        return field["stringValue"]
    if "integerValue" in field:
        return int(field["integerValue"])
    if "doubleValue" in field:
        return field["doubleValue"]
    if "booleanValue" in field:
        return field["booleanValue"]
    if "nullValue" in field:
        return None
    if "arrayValue" in field:
        return [extract_value(v) for v in field.get("arrayValue", {}).get("values", [])]
    if "mapValue" in field:
        return {k: extract_value(v) for k, v in field.get("mapValue", {}).get("fields", {}).items()}
    if "timestampValue" in field:
        return field["timestampValue"]
    return None


def parse_doc(doc):
    fields = doc.get("fields", {})
    doc_id = doc.get("name", "").split("/")[-1]
    parsed = {"id": doc_id}
    for key, val in fields.items():
        parsed[key] = extract_value(val)
    return parsed


def query_shops(where=None, select_fields=None):
    query = {
        "structuredQuery": {
            "from": [{"collectionId": "coffeeShops"}],
            "where": {
                "fieldFilter": {
                    "field": {"fieldPath": "status"},
                    "op": "EQUAL",
                    "value": {"stringValue": "approved"},
                }
            },
        }
    }

    if where:
        query["structuredQuery"]["where"] = {
            "compositeFilter": {
                "op": "AND",
                "filters": [
                    {
                        "fieldFilter": {
                            "field": {"fieldPath": "status"},
                            "op": "EQUAL",
                            "value": {"stringValue": "approved"},
                        }
                    },
                    where,
                ],
            }
        }

    if select_fields:
        query["structuredQuery"]["select"] = {
            "fields": [{"fieldPath": f} for f in select_fields]
        }

    result = firestore_request(":runQuery", method="POST", body=query)
    shops = []
    for item in result:
        doc = item.get("document")
        if doc:
            shops.append(parse_doc(doc))
    return shops


def get_shop(shop_id):
    result = firestore_request(f"/coffeeShops/{shop_id}")
    return parse_doc(result)


def find_shop_by_name(name):
    shops = get_all_shops()
    name_lower = name.lower()
    matches = [s for s in shops if name_lower in s.get("name", "").lower()]
    return matches


# --- Formatting ---


def format_hours(shop):
    hours = shop.get("openingHours")
    if not hours or not isinstance(hours, dict):
        return "Hours not available"

    periods = hours.get("periods", [])
    if not periods:
        return "Hours not available"

    lines = []
    for period in periods:
        if not isinstance(period, dict):
            continue
        open_info = period.get("open", {})
        close_info = period.get("close", {})
        day = open_info.get("day", 0)
        open_h = open_info.get("hour", 0)
        open_m = open_info.get("minute", 0)
        close_h = close_info.get("hour", 0)
        close_m = close_info.get("minute", 0)
        day_name = DAY_NAMES_EN[day] if day < len(DAY_NAMES_EN) else f"Day {day}"
        lines.append(f"  {day_name}: {open_h:02d}:{open_m:02d} - {close_h:02d}:{close_m:02d}")
    return "\n".join(lines) if lines else "Hours not available"


def is_open_now(shop):
    hours = shop.get("openingHours")
    if not hours or not isinstance(hours, dict):
        return None

    periods = hours.get("periods", [])
    if not periods:
        return None

    now = datetime.now()
    current_day = (now.weekday() + 1) % 7  # Python: Mon=0, Firestore: Sun=0
    current_minutes = now.hour * 60 + now.minute

    for period in periods:
        if not isinstance(period, dict):
            continue
        open_info = period.get("open", {})
        close_info = period.get("close", {})
        day = open_info.get("day", -1)
        if day != current_day:
            continue
        open_minutes = open_info.get("hour", 0) * 60 + open_info.get("minute", 0)
        close_minutes = close_info.get("hour", 0) * 60 + close_info.get("minute", 0)
        if open_minutes <= current_minutes <= close_minutes:
            return True
        return False
    return False


def format_stars(rating):
    if not rating:
        return dim("No rating")
    filled = int(rating)
    half = rating - filled >= 0.5
    stars = yellow("★") * filled
    if half:
        stars += yellow("½")
    return f"{stars} {rating}"


def format_shop_brief(shop):
    name = shop.get("name", "?")
    rating = shop.get("avgRating", 0)
    reviews = shop.get("totalReviews", 0)
    amenities = shop.get("amenities", [])
    if amenities and isinstance(amenities, list):
        tags = ", ".join(AMENITY_LABELS.get(a, a) for a in amenities[:5])
        if len(amenities) > 5:
            tags += f" +{len(amenities) - 5} more"
    else:
        tags = "-"

    stars = format_stars(rating)
    shop_id = shop["id"]
    return f"{bold(name)}  {stars} {dim(f'({reviews} reviews)')}  {dim(f'[{tags}]')}  {dim(f'id:{shop_id}')}"


def format_shop_detail(shop):
    lines = []
    name = shop.get("name", "?")
    lines.append(f"{brown('===')} {bold(name)} {brown('===')}")
    lines.append(f"  {dim('ID:')} {shop['id']}")

    rating = shop.get("avgRating", 0)
    reviews = shop.get("totalReviews", 0)
    lines.append(f"  {dim('Rating:')} {format_stars(rating)} ({reviews} reviews)")

    desc = shop.get("description", "")
    if desc:
        lines.append(f"  {dim('Description:')} {desc}")

    amenities = shop.get("amenities", [])
    if amenities and isinstance(amenities, list):
        tags = ", ".join(AMENITY_LABELS.get(a, a) for a in amenities)
        lines.append(f"  {dim('Amenities:')} {tags}")

    loc = shop.get("location")
    if loc and isinstance(loc, dict):
        lat = loc.get("lat", "?")
        lng = loc.get("lng", "?")
        lines.append(f"  {dim('Location:')} {lat}, {lng}")
        lines.append(f"  {dim('Google Maps:')} https://www.google.com/maps?q={lat},{lng}")

    place_id = shop.get("googlePlaceId")
    if place_id:
        lines.append(f"  {dim('Google Place ID:')} {place_id}")

    hours_str = format_hours(shop)
    if hours_str != "Hours not available":
        open_status = is_open_now(shop)
        status_str = ""
        if open_status is True:
            status_str = " " + green("OPEN NOW")
        elif open_status is False:
            status_str = " " + red("CLOSED")
        lines.append(f"  {dim('Hours')}{status_str}{dim(':')}")
        lines.append(hours_str)

    images = shop.get("imageUrls", [])
    if images and isinstance(images, list):
        lines.append(f"  {dim('Photos:')} {len(images)} available")

    lines.append(f"  {dim('Web:')} https://coffee.amsterdamski.com/shop/{shop['id']}")
    return "\n".join(lines)


def format_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


# --- Commands ---


def cmd_list(args):
    shops = get_all_shops()
    shops.sort(key=lambda s: s.get("name", ""))
    total = len(shops)

    if args.limit:
        shops = shops[:args.limit]

    if args.json:
        print(format_json({"ok": True, "command": "list", "total": total, "showing": len(shops), "shops": shops}))
        return

    showing = f" (showing {len(shops)})" if args.limit and args.limit < total else ""
    print(f"{bold('Jerusalem Specialty Coffee')} - {total} shops{showing}\n")
    for shop in shops:
        print(f"  {format_shop_brief(shop)}")


def cmd_search(args):
    matches = find_shop_by_name(args.query)

    if args.json:
        print(format_json({"ok": True, "command": "search", "query": args.query, "count": len(matches), "shops": matches}))
        return

    if not matches:
        print(f"No shops found matching '{args.query}'")
        return

    print(f"Found {len(matches)} match(es) for '{args.query}':\n")
    for shop in matches:
        print(format_shop_detail(shop))
        print()


def cmd_get(args):
    identifier = args.id

    # Try as document ID first (check cache before hitting API)
    if len(identifier) > 15 and identifier.isalnum():
        cached = _read_cache()
        if cached:
            match = [s for s in cached if s.get("id") == identifier]
            if match:
                shop = match[0]
                if args.json:
                    print(format_json({"ok": True, "command": "get", "shop": shop}))
                else:
                    print(format_shop_detail(shop))
                return
        try:
            shop = get_shop(identifier)
            if args.json:
                print(format_json({"ok": True, "command": "get", "shop": shop}))
            else:
                print(format_shop_detail(shop))
            return
        except SystemExit:
            pass

    # Fall back to name search
    matches = find_shop_by_name(identifier)
    if not matches:
        print(f"No shop found matching '{identifier}'")
        sys.exit(1)

    if args.json:
        print(format_json({"ok": True, "command": "get", "shop": matches[0]}))
        return

    print(format_shop_detail(matches[0]))
    if len(matches) > 1:
        print(f"\n({len(matches) - 1} more match(es) - use 'search' to see all)")


def cmd_filter(args):
    amenity = args.amenity.lower()
    # Map common aliases
    aliases = {
        "wifi": "wifi",
        "dogs": "dogs",
        "dog": "dogs",
        "dog-friendly": "dogs",
        "laptop": "laptop",
        "laptops": "laptop",
        "outdoor": "outdoor",
        "outside": "outdoor",
        "terrace": "outdoor",
        "accessible": "accessible",
        "wheelchair": "accessible",
        "vegan": "vegan",
        "kids": "kids",
        "children": "kids",
        "kid-friendly": "kids",
        "quiet": "quiet",
        "smoking": "smoking",
        "roasting": "local-roasting",
        "local-roasting": "local-roasting",
        "beans": "sell-beans",
        "sell-beans": "sell-beans",
        "filter": "filter-coffee",
        "filter-coffee": "filter-coffee",
        "kosher": "kosher",
        "saturday": "open-saturday",
        "shabbat": "open-saturday",
        "open-saturday": "open-saturday",
        "power": "power",
        "outlets": "power",
        "parking": "parking",
    }

    resolved = aliases.get(amenity, amenity)
    if resolved not in AMENITY_LABELS:
        print(f"Unknown amenity: '{amenity}'")
        print(f"Available: {', '.join(sorted(AMENITY_LABELS.keys()))}")
        sys.exit(1)

    all_shops = get_all_shops()
    shops = [s for s in all_shops if resolved in (s.get("amenities") or [])]
    shops.sort(key=lambda s: s.get("name", ""))

    if args.json:
        print(format_json({
            "ok": True, "command": "filter", "amenity": resolved,
            "label": AMENITY_LABELS[resolved], "count": len(shops), "shops": shops,
        }))
        return

    print(f"{bold(AMENITY_LABELS[resolved])} - {len(shops)} shops\n")
    for shop in shops:
        print(f"  {format_shop_brief(shop)}")


def cmd_open_now(args):
    shops = get_all_shops()
    open_shops = []
    for shop in shops:
        status = is_open_now(shop)
        if status is True:
            open_shops.append(shop)

    open_shops.sort(key=lambda s: s.get("name", ""))

    if args.json:
        print(format_json({"ok": True, "command": "open-now", "count": len(open_shops), "shops": open_shops}))
        return

    if not open_shops:
        print("No shops appear to be open right now (hours data may be incomplete)")
        return

    print(f"{green('Open now')} - {len(open_shops)} shops\n")
    for shop in open_shops:
        print(f"  {format_shop_brief(shop)}")


def cmd_amenities(args):
    if args.json:
        items = [{"key": k, "label": v} for k, v in sorted(AMENITY_LABELS.items())]
        print(format_json({"ok": True, "command": "amenities", "amenities": items}))
        return

    print(f"{bold('Available amenity filters:')}\n")
    for key in sorted(AMENITY_LABELS.keys()):
        print(f"  {brown(f'{key:20s}')} {AMENITY_LABELS[key]}")


def cmd_surprise(args):
    shops = get_all_shops()

    open_shops = [s for s in shops if is_open_now(s) is True]
    if open_shops:
        pick = random.choice(open_shops)
        source = "open right now"
    else:
        pick = random.choice(shops)
        source = "all shops (none confirmed open right now)"

    if args.json:
        print(format_json({"ok": True, "command": "surprise", "source": source, "shop": pick}))
        return

    print(f"{yellow('☕')} {bold('Surprise pick')} {dim(f'(from {source})')}\n")
    print(format_shop_detail(pick))


# --- Main ---


def main():
    # Handle global flags before argparse so they work in any position
    no_color = "--no-color" in sys.argv
    fresh = "--fresh" in sys.argv
    argv = [a for a in sys.argv[1:] if a not in ("--no-color", "--fresh")]

    parser = argparse.ArgumentParser(
        prog="jlm-coffee",
        description="Jerusalem specialty coffee shop finder",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List all approved coffee shops")
    p_list.add_argument("limit", nargs="?", type=int, default=None, help="Show only N shops")
    p_list.add_argument("--json", action="store_true", help="JSON output")
    p_list.set_defaults(func=cmd_list)

    # search
    p_search = subparsers.add_parser("search", help="Search shops by name")
    p_search.add_argument("query", help="Name to search for")
    p_search.add_argument("--json", action="store_true", help="JSON output")
    p_search.set_defaults(func=cmd_search)

    # get
    p_get = subparsers.add_parser("get", help="Get shop details by ID or name")
    p_get.add_argument("id", help="Shop ID or name")
    p_get.add_argument("--json", action="store_true", help="JSON output")
    p_get.set_defaults(func=cmd_get)

    # filter
    p_filter = subparsers.add_parser("filter", help="Filter shops by amenity")
    p_filter.add_argument("amenity", help="Amenity to filter by (e.g., wifi, dogs, kosher)")
    p_filter.add_argument("--json", action="store_true", help="JSON output")
    p_filter.set_defaults(func=cmd_filter)

    # open-now
    p_open = subparsers.add_parser("open-now", help="Show shops currently open")
    p_open.add_argument("--json", action="store_true", help="JSON output")
    p_open.set_defaults(func=cmd_open_now)

    # amenities
    p_amenities = subparsers.add_parser("amenities", help="List available amenity filters")
    p_amenities.add_argument("--json", action="store_true", help="JSON output")
    p_amenities.set_defaults(func=cmd_amenities)

    # surprise
    p_surprise = subparsers.add_parser("surprise", help="Pick a random coffee shop")
    p_surprise.add_argument("--json", action="store_true", help="JSON output")
    p_surprise.set_defaults(func=cmd_surprise)

    args = parser.parse_args(argv)
    _init_color(no_color)
    global _force_fresh
    _force_fresh = fresh
    args.func(args)


if __name__ == "__main__":
    main()
