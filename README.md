# jlm-coffee - Jerusalem specialty coffee shop finder

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-compatible-green.svg)](https://agentskills.io)

> **[Agent Skills](https://agentskills.io) format** - works with OpenClaw, Claude, Cursor, Codex, and other compatible clients

Search community-curated specialty coffee shops in Jerusalem by name, amenities, ratings, and opening hours. Data from [coffee.amsterdamski.com](https://coffee.amsterdamski.com), created and curated by [Shaul Amsterdamski](https://x.com/amsterdamski2).

## The problem

You're visiting Jerusalem and want specialty coffee - not tourist-trap instant. The info is scattered across Hebrew Instagram posts, Google Maps reviews in 3 languages, and word of mouth. Shaul Amsterdamski ([@amsterdamski2](https://x.com/amsterdamski2)) built [coffee.amsterdamski.com](https://coffee.amsterdamski.com) to curate the definitive list. This skill lets you search, filter, and check hours without opening a browser.

## Installation

```bash
npx skills add jlm-coffee
```

<details>
<summary>Manual install</summary>

**OpenClaw / Claude / Cursor**

Clone or copy the `jlm-coffee` folder into your skills directory:
- OpenClaw: `~/clawd/skills/jlm-coffee/`
- Claude: `~/.claude/skills/jlm-coffee/`
- Cursor: `.cursor/skills/jlm-coffee/`

**Standalone CLI**

```bash
python3 scripts/jlm-coffee.py list
```

**CLI shortcut** (optional)

```bash
ln -sf /path/to/jlm-coffee/jlm-coffee /usr/local/bin/jlm-coffee
jlm-coffee list
```

Requirements: Python 3.9+ (stdlib only, no pip install needed)
</details>

## Try it

Ask your assistant:
> "Which coffee shops in Jerusalem have WiFi and are open on Saturday?"

Or use the CLI directly:
```bash
jlm-coffee filter wifi
jlm-coffee surprise
```

## What you can ask

- "What specialty coffee shops are open right now in Jerusalem?"
- "Find me a dog-friendly cafe in Jerusalem"
- "Which Jerusalem coffee shops have outdoor seating and local roasting?"
- "Tell me about Cafe Pepa in Jerusalem"
- "Where can I work with a laptop in Jerusalem? I need WiFi and power outlets"
- "Are there kosher specialty coffee shops in Jerusalem?"
- "What coffee shops are open on Shabbat in Jerusalem?"

## Commands

| Command | Description |
|---------|-------------|
| `list` | All approved specialty coffee shops |
| `search <query>` | Search by name (Hebrew or English) |
| `get <id_or_name>` | Full details for a specific shop |
| `filter <amenity>` | Filter by amenity (wifi, dogs, kosher, outdoor, etc.) |
| `open-now` | Shops currently open based on Google Places hours |
| `amenities` | List available amenity filters |
| `surprise` | Pick a random shop (prefers open ones) |

<details>
<summary>Options and amenity reference</summary>

**Options**

| Option | Commands | Description |
|--------|----------|-------------|
| `--json` | all | JSON output for programmatic use |
| `--no-color` | all | Disable colored output (auto-detected for non-TTY, respects `NO_COLOR` env) |

**Amenity filters**

Use with the `filter` command. Common aliases are accepted (e.g., "shabbat" maps to "open-saturday", "outside" maps to "outdoor").

| Key | Label |
|-----|-------|
| `wifi` | WiFi |
| `dogs` | Dog-friendly |
| `laptop` | Laptop-friendly |
| `outdoor` | Outdoor seating |
| `accessible` | Wheelchair accessible |
| `vegan` | Vegan options |
| `kids` | Kid-friendly |
| `quiet` | Quiet atmosphere |
| `smoking` | Smoking area |
| `local-roasting` | Local roasting |
| `sell-beans` | Sells beans |
| `filter-coffee` | Filter coffee |
| `kosher` | Kosher |
| `open-saturday` | Open Saturday |
| `power` | Power outlets |
| `parking` | Parking |

</details>

<details>
<summary>Output examples</summary>

**List output**
```
Jerusalem Specialty Coffee - N shops

  Cafe Pepa  (5 stars, 4 reviews)  [Laptop-friendly, Quiet, WiFi, Kid-friendly]  id:GP7ImH...
  סיבריס  (5 stars, 3 reviews)  [Laptop-friendly, Dog-friendly, Outdoor seating]  id:bDvpGS...
```

**Get output**
```
=== סיבריס ===
  ID: bDvpGSCJdQKy1q4Gjeln
  Rating: 5 stars (3 reviews)
  Description: אחד מבתי הקפה האהובים עלי בעיר...
  Amenities: Laptop-friendly, Dog-friendly, Outdoor seating, WiFi, Local roasting, Sells beans
  Location: 31.773579, 35.2156026
  Google Maps: https://www.google.com/maps?q=31.773579,35.2156026
  Hours (OPEN NOW):
    Sun: 07:00 - 21:30
    Mon: 07:00 - 21:30
    ...
  Web: https://coffee.amsterdamski.com/shop/bDvpGSCJdQKy1q4Gjeln
```
</details>

<details>
<summary>Testing</summary>

```bash
bash tests/test_commands.sh
```

Runs integration tests covering all commands, JSON output, Hebrew/English search, amenity aliases, and error handling.
</details>

## How it works

Reads the public Firestore database behind coffee.amsterdamski.com. The `coffeeShops` collection is readable without authentication. Opening hours come from Google Places data cached by the site.

## Limitations

- Jerusalem only (database grows over time)
- Individual reviews are not accessible (only average rating and count)
- Opening hours depend on the site's Google Places cache freshness
- Search is name-only (no full-text search on descriptions)

Data from the site's public database. May not reflect current status. Does not write data or place orders. Provided "as is" without warranty of any kind.

## Author

[Alex Polonsky](https://github.com/alexpolonsky) - [GitHub](https://github.com/alexpolonsky) - [LinkedIn](https://linkedin.com/in/alexpolonsky)

---

Part of [Agent Skills](https://github.com/alexpolonsky/agent-skills) - [Specification](https://agentskills.io/specification)
