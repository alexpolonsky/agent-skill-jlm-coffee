#!/bin/bash
# Integration tests for jlm-coffee.py

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI="$SCRIPT_DIR/scripts/jlm-coffee.py"
PASS=0
FAIL=0

test_cmd() {
    local name="$1"
    local cmd="$2"
    local expected="$3"

    output=$(python3 "$CLI" $cmd 2>&1)
    if echo "$output" | grep -q "$expected"; then
        echo "  pass  $name"
        ((PASS++))
    else
        echo "  FAIL  $name"
        echo "  Expected: $expected"
        echo "  Got: ${output:0:150}..."
        ((FAIL++))
    fi
}

echo "=== JLM Coffee CLI Integration Tests ==="
echo ""

# List
test_cmd "list shows shop count" "list" "shops"
test_cmd "list shows a known shop" "list" "סיבריס"
test_cmd "list --json" "list --json" '"ok": true'

# Search
test_cmd "search Hebrew name" "search סיבריס" "סיבריס"
test_cmd "search English name" "search Cafe" "Cafe Pepa"
test_cmd "search partial name" "search רוסטרס" "2 match"
test_cmd "search --json" "search סיבריס --json" '"command": "search"'
test_cmd "search no results" "search zzzznotfound" "No shops found"

# Get by name
test_cmd "get by name" "get בארוק" "בארוק"
test_cmd "get shows rating" "get בארוק" "Rating:"
test_cmd "get shows amenities" "get בארוק" "Amenities:"
test_cmd "get shows web link" "get בארוק" "coffee.amsterdamski.com/shop/"
test_cmd "get --json" "get בארוק --json" '"ok": true'

# Get by ID
test_cmd "get by ID" "get EljFiggwObssQpypWMf0" "אבו סיר"

# Filter
test_cmd "filter wifi" "filter wifi" "WiFi"
test_cmd "filter dogs" "filter dogs" "Dog-friendly"
test_cmd "filter kosher" "filter kosher" "Kosher"
test_cmd "filter alias 'shabbat'" "filter shabbat" "Open Saturday"
test_cmd "filter alias 'outside'" "filter outside" "Outdoor seating"
test_cmd "filter --json" "filter wifi --json" '"amenity": "wifi"'
test_cmd "filter unknown" "filter zzz" "Unknown amenity"

# Open now
test_cmd "open-now runs" "open-now" "shops"
test_cmd "open-now --json" "open-now --json" '"command": "open-now"'

# Surprise
test_cmd "surprise runs" "surprise" "Surprise pick"
test_cmd "surprise --json" "surprise --json" '"command": "surprise"'

# Amenities
test_cmd "amenities list" "amenities" "wifi"
test_cmd "amenities shows all" "amenities" "kosher"
test_cmd "amenities --json" "amenities --json" '"amenities"'

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
exit $FAIL
