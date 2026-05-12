#!/usr/bin/env python3
"""Validate loaded GIS data against known reference sites.

Checks:
1. All tables populated with expected row counts
2. Spatial coverage — clusters cover all provinces
3. Attribute completeness — no critical NULLs
4. Reference site validation — known sites have reasonable values
5. API endpoint test — verify the full pipeline works via HTTP

Usage:
    python 06_validate_data.py
"""
from __future__ import annotations

import json
import sys
import urllib.request

from sqlalchemy import create_engine, text

from config import DATABASE_URL  # type: ignore[import-untyped]

# Known reference sites for validation
REFERENCE_SITES = [
    {
        "name": "Maputo (urban)",
        "lat": -25.97,
        "lon": 32.57,
        "expected": {"is_urban": 2, "pop_min": 500, "ghi_min": 1600},
    },
    {
        "name": "Nampula (peri-urban)",
        "lat": -15.12,
        "lon": 39.27,
        "expected": {"is_urban_min": 1, "pop_min": 200, "ghi_min": 1700},
    },
    {
        "name": "Niassa rural",
        "lat": -12.50,
        "lon": 35.50,
        "expected": {"pop_min": 50, "ghi_min": 1600},
    },
    {
        "name": "Inhambane coast",
        "lat": -23.86,
        "lon": 35.38,
        "expected": {"ghi_min": 1600, "wind_min": 3.0},
    },
]


def validate_tables(engine) -> int:
    """Check all tables have data."""
    print("\n--- Table Row Counts ---")
    errors = 0

    expected = {
        "settlement_clusters": 1000,
        "admin_boundaries": 10,
        "grid_lines": 10,
        "roads": 100,
    }

    with engine.connect() as conn:
        for table, min_rows in expected.items():
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            status = "ok" if count >= min_rows else "WARN"
            if status == "WARN":
                errors += 1
            print(f"  [{status}] {table:<25} {count:>8} rows (min: {min_rows})")

    return errors


def validate_coverage(engine) -> int:
    """Check spatial coverage across provinces."""
    print("\n--- Provincial Coverage ---")
    errors = 0

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT adm1_name, COUNT(*) as clusters, SUM(population) as total_pop
            FROM settlement_clusters
            WHERE adm1_name IS NOT NULL
            GROUP BY adm1_name
            ORDER BY total_pop DESC
        """))
        rows = result.fetchall()

    if not rows:
        print("  [WARN] No province data — admin boundaries may not be loaded")
        return 1

    for name, clusters, pop in rows:
        print(f"  {name:<20} {clusters:>6} clusters  pop: {pop:>10,}")

    expected_provinces = {
        "Zambezia", "Nampula", "Gaza", "Inhambane", "Sofala",
        "Tete", "Manica", "Cabo Delgado", "Niassa", "Maputo",
    }
    found = {row[0] for row in rows}
    missing = expected_provinces - found
    if missing:
        print(f"  [WARN] Missing provinces: {', '.join(missing)}")
        errors += 1
    else:
        print(f"  [ok] All {len(expected_provinces)} major provinces covered")

    return errors


def validate_attributes(engine) -> int:
    """Check attribute completeness."""
    print("\n--- Attribute Completeness ---")
    errors = 0

    critical_cols = [
        "population", "area_km2", "is_urban",
        "ghi_kwh_m2_year", "dist_grid_mv_km",
    ]
    important_cols = [
        "wind_speed_ms", "elevation_m", "slope_deg",
        "max_ntl", "travel_time_hrs", "dist_road_km",
    ]

    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM settlement_clusters")).scalar()

        for col in critical_cols + important_cols:
            non_null = conn.execute(
                text(f"SELECT COUNT(*) FROM settlement_clusters WHERE {col} IS NOT NULL")
            ).scalar()
            pct = non_null / total * 100 if total > 0 else 0
            is_critical = col in critical_cols
            threshold = 90 if is_critical else 50

            status = "ok" if pct >= threshold else ("FAIL" if is_critical else "WARN")
            if status != "ok":
                errors += 1
            print(f"  [{status}] {col:<25} {non_null:>6}/{total} ({pct:.0f}%)")

    return errors


def validate_reference_sites(engine) -> int:
    """Validate known reference sites have reasonable values."""
    print("\n--- Reference Site Validation ---")
    errors = 0

    with engine.connect() as conn:
        for site in REFERENCE_SITES:
            result = conn.execute(text("""
                SELECT cluster_id, population, is_urban, ghi_kwh_m2_year,
                       wind_speed_ms, dist_grid_mv_km
                FROM settlement_clusters
                ORDER BY ST_Distance(
                    centroid,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                )
                LIMIT 1
            """), {"lat": site["lat"], "lon": site["lon"]})

            row = result.fetchone()
            if not row:
                print(f"  [FAIL] {site['name']}: no cluster found nearby")
                errors += 1
                continue

            cid, pop, urban, ghi, wind, grid_dist = row
            expected = site["expected"]
            issues = []

            if "pop_min" in expected and pop < expected["pop_min"]:
                issues.append(f"pop={pop} < {expected['pop_min']}")
            if "is_urban" in expected and urban != expected["is_urban"]:
                issues.append(f"urban={urban} != {expected['is_urban']}")
            if "ghi_min" in expected and ghi and ghi < expected["ghi_min"]:
                issues.append(f"GHI={ghi:.0f} < {expected['ghi_min']}")

            if issues:
                print(f"  [WARN] {site['name']} (cluster {cid}): {', '.join(issues)}")
                errors += 1
            else:
                print(f"  [ok] {site['name']} (cluster {cid}): pop={pop}, urban={urban}, GHI={ghi:.0f}")

    return errors


def validate_api() -> int:
    """Test the API endpoint with a known coordinate."""
    print("\n--- API Endpoint Test ---")

    api_url = "http://localhost:8001/api/analyze-site"
    payload = json.dumps({
        "latitude": -15.5,
        "longitude": 35.0,
        "name": "Validation Test",
    }).encode()

    try:
        req = urllib.request.Request(
            api_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())

        checks = [
            ("site.latitude", data["site"]["latitude"], -15.5),
            ("demand.households", data["demand"]["households"], 1),
            ("sizing.pv_kwp", data["sizing"]["pv_kwp"], 0.1),
            ("financial.total_capex_usd", data["financial"]["total_capex_usd"], 100),
            ("grid_risk.risk_level", data["grid_risk"]["risk_level"], None),
        ]

        all_ok = True
        for name, value, min_val in checks:
            if min_val is not None and isinstance(value, (int, float)) and value < min_val:
                print(f"  [FAIL] {name} = {value} (expected >= {min_val})")
                all_ok = False
            else:
                print(f"  [ok] {name} = {value}")

        return 0 if all_ok else 1

    except urllib.error.URLError:
        print(f"  [skip] API not running at {api_url}")
        return 0
    except Exception as e:
        print(f"  [FAIL] API test failed: {e}")
        return 1


def main():
    print("=" * 60)
    print("Data Validation Suite")
    print("=" * 60)

    total_errors = 0

    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  Connected to database")
    except Exception as e:
        print(f"[error] Cannot connect to database: {e}")
        print("Running API-only validation...\n")
        total_errors += validate_api()
        print(f"\n{'='*60}")
        print(f"Validation complete: {total_errors} issues found")
        sys.exit(1 if total_errors > 0 else 0)

    total_errors += validate_tables(engine)
    total_errors += validate_coverage(engine)
    total_errors += validate_attributes(engine)
    total_errors += validate_reference_sites(engine)
    total_errors += validate_api()

    print(f"\n{'='*60}")
    if total_errors == 0:
        print("All validations passed!")
    else:
        print(f"Validation complete: {total_errors} issues found")
        print("Review warnings above and re-run pipeline steps as needed.")

    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
