from __future__ import annotations

import json
import logging
import math
import urllib.request
from typing import Optional

from app.schemas.analysis import SolarResource

logger = logging.getLogger("moz")

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/MRcalc"

FALLBACK_MONTHLY_GHI = [194, 180, 172, 158, 136, 118, 125, 148, 168, 184, 190, 190]
FALLBACK_MONTHLY_DNI = [158, 145, 138, 130, 120, 105, 115, 135, 150, 160, 160, 155]
FALLBACK_MONTHLY_TEMP = [27.9, 27.5, 26.5, 24.8, 22.5, 20.5, 20.2, 22.0, 24.5, 26.8, 27.8, 28.0]

LOSS_BREAKDOWN = {
    "temperature": 0.07,
    "soiling": 0.025,
    "wiring_mismatch": 0.025,
    "inverter": 0.025,
    "battery_dispatch": 0.08,
    "availability": 0.015,
    "year1_degradation": 0.0175,
}

DAYS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _build_solar_hour_shape() -> list[float]:
    shape = [0.0] * 24
    for h in range(6, 18):
        shape[h] = math.sin(math.pi * (h - 6) / 12)
    total = sum(shape)
    return [v / total for v in shape]


SOLAR_HOUR_SHAPE = _build_solar_hour_shape()


def assess_solar_resource(
    lat: float, lon: float
) -> tuple[SolarResource, list[float]]:
    """Fetch solar resource data and produce 8,760-hour generation factors.

    Returns the SolarResource schema for the API response and a list of
    8,760 normalized hourly solar factors for internal use by the sizing engine.
    """
    monthly_ghi, monthly_dni, monthly_temp = [], [], []
    data_source = ""
    warnings: list[str] = []

    try:
        url = (
            f"{PVGIS_URL}?lat={lat}&lon={lon}"
            "&horirrad=1&mr_dni=1&avtemp=1&outputformat=json"
        )
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())

        records = result["outputs"]["monthly"]
        sums: dict[int, dict[str, list[float]]] = {}
        for rec in records:
            m = rec["month"]
            if m not in sums:
                sums[m] = {"ghi": [], "dni": [], "temp": []}
            sums[m]["ghi"].append(rec.get("H(h)_m", 0))
            sums[m]["dni"].append(rec.get("Hb(n)_m", 0))
            sums[m]["temp"].append(rec.get("T2m", 25))

        for m in range(1, 13):
            vals = sums[m]
            monthly_ghi.append(round(sum(vals["ghi"]) / len(vals["ghi"]), 1))
            monthly_dni.append(round(sum(vals["dni"]) / len(vals["dni"]), 1))
            monthly_temp.append(round(sum(vals["temp"]) / len(vals["temp"]), 1))

        meta = result.get("inputs", {}).get("meteo_data", {})
        data_source = f"PVGIS 5.3 ({meta.get('radiation_db', 'unknown')})"
        logger.info("PVGIS data received: %s", data_source)

    except Exception as e:
        logger.warning("PVGIS API failed: %s — using fallback values", e)
        warnings.append(f"PVGIS API unavailable. Using fallback solar data for Mozambique.")
        monthly_ghi = list(FALLBACK_MONTHLY_GHI)
        monthly_dni = list(FALLBACK_MONTHLY_DNI)
        monthly_temp = list(FALLBACK_MONTHLY_TEMP)
        data_source = "Fallback (Global Solar Atlas screening values)"

    annual_ghi = sum(monthly_ghi)
    optimal_tilt = round(abs(lat), 1)

    pr = 1.0
    for loss in LOSS_BREAKDOWN.values():
        pr *= (1 - loss)
    performance_ratio = round(pr, 4)

    specific_yield = round(annual_ghi * performance_ratio, 0)

    hourly_factors = _build_8760_factors(monthly_ghi, annual_ghi)

    resource = SolarResource(
        monthly_ghi_kwh_m2=monthly_ghi,
        monthly_dni_kwh_m2=monthly_dni,
        monthly_temp_c=monthly_temp,
        annual_ghi_kwh_m2=round(annual_ghi, 1),
        optimal_tilt_deg=optimal_tilt,
        specific_yield_kwh_per_kwp=specific_yield,
        performance_ratio=performance_ratio,
        loss_breakdown=LOSS_BREAKDOWN,
        data_source=data_source,
    )
    return resource, hourly_factors


def _build_8760_factors(monthly_ghi: list[float], annual_ghi: float) -> list[float]:
    """Build 8,760 hourly irradiance factors (kWh/m² per hour).

    Usage: solar_gen_kw = pv_kwp * factor[h] * performance_ratio
    sum(factors) ≈ annual_ghi so annual_gen = pv_kwp * PR * annual_ghi.
    """
    if annual_ghi <= 0:
        return [0.0] * 8760

    factors: list[float] = []
    for m in range(12):
        daily_ghi_m = monthly_ghi[m] / DAYS_PER_MONTH[m]
        for _d in range(DAYS_PER_MONTH[m]):
            for h in range(24):
                factors.append(round(daily_ghi_m * SOLAR_HOUR_SHAPE[h], 6))

    while len(factors) < 8760:
        factors.append(0.0)
    return factors[:8760]
