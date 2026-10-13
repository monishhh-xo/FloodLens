"""Curated Chennai zone catalogue.

Coordinates
-----------
Every latitude/longitude below was resolved from OpenStreetMap place data
(Nominatim) and confirmed to fall inside the Chennai bounding box
(lat 12.85-13.25, lon 80.05-80.35) in Chennai district, Tamil Nadu. They are
approximate locality centroids, not administrative boundaries.

Illustrative attributes
-----------------------
Every attribute other than name/id/coordinates is an **illustrative design
assumption** supplied so the scoring prototype has something to reason about.
They are not surveyed measurements. The mapped points are NOT verified flood
hotspots and must not be presented as such.

No per-zone historical flood record is asserted. ``historical_flood_flag`` is an
illustrative binary placeholder that exists solely because the synthetic dataset
has a column of that name; it is never shown to users as a factual claim.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

ILLUSTRATIVE_NOTE = (
    "All zone attributes except id/name/coordinates are illustrative design "
    "assumptions, not surveyed measurements. Mapped points are not verified "
    "flood hotspots."
)


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    latitude: float
    longitude: float
    # --- illustrative attributes below this line ---
    land_cover: str
    soil_type: str
    imperviousness_pct: float
    drainage_capacity_index: float  # 0 (none) - 1 (excellent)
    elevation_class: str  # Low | Mid | High
    water_proximity_m: float
    infrastructure_index: int  # 0 | 1
    historical_flood_flag: int  # 0 | 1 illustrative placeholder only
    descriptive_note: str

    @property
    def attributes_illustrative(self) -> bool:
        return True

    def to_dict(self) -> dict:
        data = asdict(self)
        data["attributes_illustrative"] = True
        data["illustrative_note"] = ILLUSTRATIVE_NOTE
        return data


ZONES: tuple[Zone, ...] = (
    Zone(
        id="velachery",
        name="Velachery",
        latitude=12.98017,
        longitude=80.22285,
        land_cover="Urban",
        soil_type="Clay",
        imperviousness_pct=82.0,
        drainage_capacity_index=0.35,
        elevation_class="Low",
        water_proximity_m=400.0,
        infrastructure_index=1,
        historical_flood_flag=1,
        descriptive_note="Dense built-up locality with an illustrative low elevation class.",
    ),
    Zone(
        id="mudichur",
        name="Mudichur",
        latitude=12.91498,
        longitude=80.06884,
        land_cover="Urban",
        soil_type="Clay",
        imperviousness_pct=55.0,
        drainage_capacity_index=0.30,
        elevation_class="Low",
        water_proximity_m=150.0,
        infrastructure_index=0,
        historical_flood_flag=1,
        descriptive_note="Southern fringe locality, illustrative weak drainage and nearby water body.",
    ),
    Zone(
        id="tambaram",
        name="Tambaram",
        latitude=12.92579,
        longitude=80.11792,
        land_cover="Urban",
        soil_type="Sandy",
        imperviousness_pct=65.0,
        drainage_capacity_index=0.45,
        elevation_class="Mid",
        water_proximity_m=600.0,
        infrastructure_index=1,
        historical_flood_flag=0,
        descriptive_note="Suburban hub with illustrative moderate drainage capacity.",
    ),
    Zone(
        id="saidapet",
        name="Saidapet",
        latitude=13.02082,
        longitude=80.22395,
        land_cover="Urban",
        soil_type="Silt",
        imperviousness_pct=78.0,
        drainage_capacity_index=0.50,
        elevation_class="Low",
        water_proximity_m=250.0,
        infrastructure_index=1,
        historical_flood_flag=1,
        descriptive_note="Riverside locality with an illustrative low elevation class.",
    ),
    Zone(
        id="t_nagar",
        name="T. Nagar",
        latitude=13.03783,
        longitude=80.23184,
        land_cover="Urban",
        soil_type="Clay",
        imperviousness_pct=88.0,
        drainage_capacity_index=0.60,
        elevation_class="Mid",
        water_proximity_m=900.0,
        infrastructure_index=1,
        historical_flood_flag=0,
        descriptive_note="High-density commercial area with illustrative high imperviousness.",
    ),
    Zone(
        id="kotturpuram",
        name="Kotturpuram",
        latitude=13.01937,
        longitude=80.24355,
        land_cover="Urban",
        soil_type="Silt",
        imperviousness_pct=70.0,
        drainage_capacity_index=0.40,
        elevation_class="Low",
        water_proximity_m=120.0,
        infrastructure_index=1,
        historical_flood_flag=1,
        descriptive_note="Adjacent to the Adyar river, illustrative short distance to water.",
    ),
    Zone(
        id="perungudi",
        name="Perungudi",
        latitude=12.97102,
        longitude=80.24181,
        land_cover="Urban",
        soil_type="Clay",
        imperviousness_pct=72.0,
        drainage_capacity_index=0.42,
        elevation_class="Low",
        water_proximity_m=500.0,
        infrastructure_index=1,
        historical_flood_flag=0,
        descriptive_note="Former marshland area, illustrative mixed drainage capacity.",
    ),
    Zone(
        id="adyar",
        name="Adyar",
        latitude=13.00645,
        longitude=80.25778,
        land_cover="Urban",
        soil_type="Sandy",
        imperviousness_pct=68.0,
        drainage_capacity_index=0.55,
        elevation_class="Low",
        water_proximity_m=100.0,
        infrastructure_index=1,
        historical_flood_flag=1,
        descriptive_note="Estuary-side locality, illustrative very short distance to water.",
    ),
    Zone(
        id="kolathur",
        name="Kolathur",
        latitude=13.12365,
        longitude=80.21288,
        land_cover="Urban",
        soil_type="Clay",
        imperviousness_pct=74.0,
        drainage_capacity_index=0.38,
        elevation_class="Mid",
        water_proximity_m=700.0,
        infrastructure_index=0,
        historical_flood_flag=0,
        descriptive_note="Northern locality with illustrative weak drainage capacity.",
    ),
    Zone(
        id="vyasarpadi",
        name="Vyasarpadi",
        latitude=13.11305,
        longitude=80.25872,
        land_cover="Urban",
        soil_type="Silt",
        imperviousness_pct=80.0,
        drainage_capacity_index=0.33,
        elevation_class="Low",
        water_proximity_m=300.0,
        infrastructure_index=0,
        historical_flood_flag=1,
        descriptive_note="North Chennai locality with illustrative low elevation and weak drainage.",
    ),
    Zone(
        id="chetpet",
        name="Chetpet",
        latitude=13.07174,
        longitude=80.24380,
        land_cover="Urban",
        soil_type="Loam",
        imperviousness_pct=76.0,
        drainage_capacity_index=0.58,
        elevation_class="Mid",
        water_proximity_m=350.0,
        infrastructure_index=1,
        historical_flood_flag=0,
        descriptive_note="Central locality beside an illustrative lake feature.",
    ),
    Zone(
        id="porur",
        name="Porur",
        latitude=13.03246,
        longitude=80.15829,
        land_cover="Urban",
        soil_type="Sandy",
        imperviousness_pct=62.0,
        drainage_capacity_index=0.48,
        elevation_class="Mid",
        water_proximity_m=800.0,
        infrastructure_index=1,
        historical_flood_flag=0,
        descriptive_note="Western locality with illustrative moderate drainage capacity.",
    ),
)

ZONES_BY_ID: dict[str, Zone] = {z.id: z for z in ZONES}


def get_zone(zone_id: str) -> Zone | None:
    return ZONES_BY_ID.get(zone_id.strip().lower())


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def nearest_zone(latitude: float, longitude: float, max_km: float = 3.0) -> tuple[Zone, float] | None:
    best: tuple[Zone, float] | None = None
    for zone in ZONES:
        distance = haversine_km(latitude, longitude, zone.latitude, zone.longitude)
        if best is None or distance < best[1]:
            best = (zone, distance)
    if best is None or best[1] > max_km:
        return None
    return best


def custom_zone(latitude: float, longitude: float) -> Zone:
    """Fallback zone for coordinates that match no catalogue entry.

    Uses the catalogue-average illustrative attributes so the response stays
    fully populated, and is labelled as a user-supplied point rather than a
    catalogued locality.
    """
    avg_imperviousness = round(sum(z.imperviousness_pct for z in ZONES) / len(ZONES), 1)
    avg_drainage = round(sum(z.drainage_capacity_index for z in ZONES) / len(ZONES), 3)
    avg_water = round(sum(z.water_proximity_m for z in ZONES) / len(ZONES), 0)
    return Zone(
        id="custom",
        name="User-supplied coordinates",
        latitude=float(latitude),
        longitude=float(longitude),
        land_cover="Urban",
        soil_type="Clay",
        imperviousness_pct=avg_imperviousness,
        drainage_capacity_index=avg_drainage,
        elevation_class="Mid",
        water_proximity_m=avg_water,
        infrastructure_index=1,
        historical_flood_flag=0,
        descriptive_note=(
            "Not a catalogued locality. Illustrative attributes are catalogue "
            "averages applied to the coordinates you supplied."
        ),
    )
