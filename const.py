"""Constants for the Idaho Falls Garbage Pickup integration."""

DOMAIN = "idaho_falls_garbage"

CONF_COLLECTION_DAY = "collection_day"
CONF_AUTO_DETECT = "auto_detect"
CONF_CUTOFF_HOUR = "cutoff_hour"
CONF_NO_DELAY_HOLIDAYS = "no_delay_holidays"
CONF_EXTRA_DELAY_DATES = "extra_delay_dates"

# Hour (24h, local) after which today's pickup counts as done. 24 = end of day.
DEFAULT_CUTOFF_HOUR = 24

GIS_BASE = "https://cifgis.idahofalls.gov/arcgis/rest/services"
# Sanitation / "Garbage Collection Area" polygons (field: CollectionDay)
GARBAGE_QUERY_URL = f"{GIS_BASE}/Sanitation/MapServer/20/query"
# LeafCollection / "Leaf Collection Area" polygons (fields: AreaName, CollectDate, Comments)
LEAF_QUERY_URL = f"{GIS_BASE}/LeafCollection/MapServer/10/query"

CITY_SANITATION_URL = "https://idahofallsidaho.gov/365/Sanitation"
