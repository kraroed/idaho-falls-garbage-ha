# Idaho Falls Garbage Pickup for Home Assistant

Tells you your next garbage pickup in Idaho Falls, ID, and shifts the date automatically when a holiday delays collection.

## Features

- **Uses your Home Assistant home location** to look up your collection day from the City of Idaho Falls GIS "Garbage Collection Area" layer (manual weekday fallback if the lookup fails).
- **Holiday-aware.** Per the city's policy, there is no collection on these weekday holidays and pickups for the rest of that week run one day late: New Year's Day, Memorial Day, Independence Day, Labor Day, Thanksgiving, Christmas Day. Holidays on a weekend change nothing.
- **Leaf collection** (seasonal) for your leaf zone, from the city's Leaf Collection GIS layer.
- **Self-correcting:** re-checks the city's map daily and updates your day (with a notification) if the city changes it.

## Entities

| Entity | What it is |
|---|---|
| `sensor.idaho_falls_garbage_next_pickup` | Date of the next pickup. Attributes: `collection_day`, `normal_date`, `delayed`, `delay_reason`, `days_until`, `upcoming` |
| `binary_sensor.idaho_falls_garbage_pickup_today` | On on pickup day, until the cutoff hour |
| `binary_sensor.idaho_falls_garbage_pickup_tomorrow` | On the day before a pickup, handy for "take the bins out" alerts |
| `calendar.idaho_falls_garbage` | All-day events for pickups (delays labeled) and leaf collection |
| `sensor.idaho_falls_garbage_leaf_collection` | Leaf collection date for your zone; attributes `status`, `zone`, `collect_date`, `comments` |
| `button.idaho_falls_garbage_refresh_from_city` | Re-check collection day and leaf data now |

## Options (Configure)

- **Detect collection day automatically**: on by default (off if you chose your day manually).
- **Cutoff hour**: after this local hour on pickup day, *Next pickup* moves to the following pickup and *Pickup today* turns off. `24` = end of day.
- **Holidays that should NOT delay pickup**: for years when the city's rules differ.
- **Extra delay dates**: one-off city-announced delays (weather, etc.), `YYYY-MM-DD`.

Each January and February a Repairs notice reminds you to check the city's holiday schedule; dismiss it once you have.

## Install

**HACS (custom repository):** HACS → ⋮ → Custom repositories → add `https://github.com/kraroed/idaho-falls-garbage-ha` as *Integration* → install → restart Home Assistant.

**Manual:** copy `custom_components/idaho_falls_garbage` into your HA `config/custom_components/` folder and restart.

Then: Settings → Devices & Services → Add Integration → **Idaho Falls Garbage Pickup**.

## Example automation

```yaml
automation:
  - alias: "Garbage reminder"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.idaho_falls_garbage_pickup_tomorrow
        state: "on"
    action:
      - service: notify.notify
        data:
          message: >
            Garbage goes out tonight.
            {% if state_attr('sensor.idaho_falls_garbage_next_pickup','delayed') %}
            (Delayed: {{ state_attr('sensor.idaho_falls_garbage_next_pickup','delay_reason') }})
            {% endif %}
```

## Notes and caveats

- Home Assistant stores your home as coordinates, not a street address, so that is what is sent to the city's GIS service.
- Holiday rules come from the city's published policy and can change year to year (the city's 2023 and 2026 Labor Day notices differed). See the [city Sanitation page](https://idahofallsidaho.gov/365/Sanitation).
- Garbage and leaf collection only. Unofficial; not affiliated with the City of Idaho Falls.

## Development

Run the tests:

```
pip install -r requirements_test.txt
pytest
```

Run a real Home Assistant with the integration linked in (dev container or any Python 3.13 env):

```
pip install -r requirements.txt
./scripts/develop      # http://localhost:8123, home location = Idaho Falls
```
