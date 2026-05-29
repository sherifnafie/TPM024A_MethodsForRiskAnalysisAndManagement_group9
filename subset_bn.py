#!/usr/bin/env python3
"""Subset Bayesian Network prototype for assignment 3.

This version follows the group's filtered scope in ``new_info.drawio``:
two fleet-level FTA branches and two individual-drone top events. It uses
only the Python standard library and is intended for transparent scenario
comparison, not for validated reliability claims.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CSV_OUT = ROOT / "scenario_results_subset_v1.csv"


# Updated FMEA rows from assignment3/FMEA/FMEA Hazard Sheet.xlsx.
# S/O/D are retained for traceability; O is used as ordinal prior input.
FMEA = {
    "2.2.1": {
        "label": "Airspace conflict not detected",
        "level": "Fleet",
        "s": 7.6667,
        "o": 3.8333,
        "d": 5.8333,
        "rpn": 192,
        "lopa":3.42e-8,
    },
    "2.2.2": {
        "label": "Conflicting route updates issued",
        "level": "Fleet",
        "s": 5.8333,
        "o": 4.1667,
        "d": 5.0000,
        "rpn": 120,
        "lopa":3.42e-5,
    },
    "2.2.3": {
        "label": "Minimum separation distance violated",
        "level": "Fleet",
        "s": 6.1667,
        "o": 5.5000,
        "d": 5.6667,
        "rpn": 216,
        "lopa":3.42e-7,
    },
    "2.5.1": {
        "label": "Emergency landing command not executed",
        "level": "Fleet",
        "s": 9.0000,
        "o": 3.1667,
        "d": 7.3333,
        "rpn": 189,
        "lopa":3.42e-9,
    },
    "2.5.2": {
        "label": "Return-to-home triggered incorrectly",
        "level": "Fleet",
        "s": 6.8333,
        "o": 3.5000,
        "d": 6.6667,
        "rpn": 196,
        "lopa":3.42e-7,
    },
    "2.5.3": {
        "label": "Unsafe drones not grounded",
        "level": "Fleet",
        "s": 8.3333,
        "o": 3.5000,
        "d": 6.8333,
        "rpn": 224,
        "lopa":3.42e-7,
    },
    "2.5.4": {
        "label": "Incident response delayed",
        "level": "Fleet",
        "s": 7.6667,
        "o": 4.0000,
        "d": 6.0000,
        "rpn": 192,
        "lopa":3.42e-5,
    },
    "2.1.2": {
        "label": "Unsafe route generated",
        "level": "Fleet",
        "s": 7.1667,
        "o": 4.1667,
        "d": 4.6667,
        "rpn": 140,
        "lopa":3.42e-5,
    },
    "1.1.1": {
        "label": "Motor seizure or complete loss of thrust",
        "level": "Single drone",
        "s": 6.1667,
        "o": 3.8333,
        "d": 6.5000,
        "rpn": 168,
        "lopa":3.42e-8,
    },
    "1.1.2": {
        "label": "Propeller fracture during flight",
        "level": "Single drone",
        "s": 5.8333,
        "o": 4.3333,
        "d": 7.3333,
        "rpn": 168,
        "lopa":1.71e-6,
    },
    "1.2.1": {
        "label": "Battery cell damage",
        "level": "Single drone",
        "s": 5.1667,
        "o": 5.6667,
        "d": 5.3333,
        "rpn": 150,
        "lopa":3.42e-4,
    },
    "1.3.1": {
        "label": "Flight controller software crash",
        "level": "Single drone",
        "s": 5.1667,
        "o": 4.3333,
        "d": 6.1667,
        "rpn": 120,
        "lopa":3.42e-5,
    },
}


BASE_CONTEXT = {
    "Weather": "normal",
    "WindTurbulence": "normal",
    "FleetDensity": "nominal",
    "UrbanObstacleExposure": "normal",
    "GNSSQuality": "good",
    "C2Quality": "good",
    "UTMDataQuality": "current",
    "CloudLoad": "normal",
    "MaintenanceQuality": "nominal",
    "BatteryHealth": "healthy",
    "PayloadSecuring": "normal",
    "OperatorWorkload": "normal",
    "GeofenceData": "current",
}


SCENARIOS = [
    {
        "id": "S0",
        "label": "Baseline selected operation",
        "evidence": {},
    },
    {
        "id": "S1",
        "label": "High-density constrained corridor",
        "evidence": {
            "FleetDensity": "high",
            "UrbanObstacleExposure": "high",
            "C2Quality": "congested",
            "OperatorWorkload": "high",
        },
    },
    {
        "id": "S2",
        "label": "GNSS and telemetry degradation",
        "evidence": {
            "GNSSQuality": "degraded",
            "C2Quality": "congested",
            "CloudLoad": "high",
            "UTMDataQuality": "delayed",
        },
    },
    {
        "id": "S3",
        "label": "Emergency after propulsion warning",
        "evidence": {
            "MaintenanceQuality": "degraded",
            "BatteryHealth": "degraded",
            "OperatorWorkload": "high",
            "C2Quality": "congested",
        },
    },
    {
        "id": "S4",
        "label": "Obstacle-rich urban route",
        "evidence": {
            "UrbanObstacleExposure": "high",
            "FleetDensity": "high",
            "GNSSQuality": "degraded",
            "GeofenceData": "stale",
        },
    },
    {
        "id": "S5",
        "label": "Weather and mechanical stress",
        "evidence": {
            "Weather": "adverse",
            "WindTurbulence": "turbulent",
            "MaintenanceQuality": "degraded",
            "PayloadSecuring": "poor",
            "BatteryHealth": "degraded",
        },
    },
    {
        "id": "S6",
        "label": "Mitigated low-density operation",
        "evidence": {
            "FleetDensity": "low",
            "UrbanObstacleExposure": "low",
            "GNSSQuality": "good",
            "C2Quality": "good",
            "UTMDataQuality": "current",
            "CloudLoad": "normal",
            "MaintenanceQuality": "enhanced",
            "OperatorWorkload": "normal",
            "GeofenceData": "current",
        },
    },
]


def noisy_or(leak: float, causes: list[float]) -> float:
    p_false = 1.0 - leak
    for cause in causes:
        p_false *= 1.0 - min(max(cause, 0.0), 1.0)
    return min(max(1.0 - p_false, 0.0), 1.0)


# def occurrence_to_rate(o_score: float) -> float:
#     """Map ordinal FMEA occurrence to a rough residual per-flight-hour rate."""
#     return 10 ** (-5.0 + 0.42 * o_score)
    
def occurrence_to_rate(fmea_id: str) -> float:
    """Map ordinal FMEA occurrence to a rough residual per-flight-hour rate."""
    return  float(FMEA[fmea_id]["lopa"])

# def fmea_leak(fmea_id: str, scale: float = 0.30) -> float:
#     return occurrence_to_rate(float(FMEA[fmea_id]["o"])) * scale

def fmea_leak(fmea_id: str, scale: float = 0.30) -> float:
    return occurrence_to_rate(fmea_id) * scale


def effect_from_evidence(context: dict[str, str], variable: str, effects: dict[str, float]) -> float:
    return effects.get(context[variable], 0.0)


def effect_from_node(probs: dict[str, float], node: str, strength: float) -> float:
    return probs[node] * strength


def evaluate(context: dict[str, str]) -> dict[str, float]:
    probs: dict[str, float] = {}

    probs["TelemetryDelay"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "C2Quality", {"congested": 0.035, "lost": 0.18}),
            effect_from_evidence(context, "FleetDensity", {"nominal": 0.003, "high": 0.035}),
            effect_from_evidence(context, "CloudLoad", {"high": 0.018, "overloaded": 0.06}),
        ],
    )
    probs["PositionInaccuracy"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "GNSSQuality", {"degraded": 0.045, "lost": 0.18}),
            effect_from_evidence(context, "Weather", {"adverse": 0.020, "severe": 0.070}),
            effect_from_node(probs, "TelemetryDelay", 0.25),
        ],
    )
    probs["CommunicationLoss"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "C2Quality", {"congested": 0.025, "lost": 0.22}),
            effect_from_evidence(context, "UrbanObstacleExposure", {"high": 0.018}),
            effect_from_evidence(context, "FleetDensity", {"high": 0.015}),
        ],
    )
    probs["HighDensityAirspace"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "FleetDensity", {"nominal": 0.005, "high": 0.090}),
            effect_from_evidence(context, "UrbanObstacleExposure", {"normal": 0.006, "high": 0.040}),
        ],
    )
    probs["ReroutingPressure"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "Weather", {"adverse": 0.045, "severe": 0.140}),
            effect_from_evidence(context, "UTMDataQuality", {"delayed": 0.020, "inconsistent": 0.060}),
            effect_from_evidence(context, "FleetDensity", {"high": 0.020}),
        ],
    )
    probs["SoftwareSyncConflict"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "CloudLoad", {"high": 0.020, "overloaded": 0.070}),
            effect_from_evidence(context, "UTMDataQuality", {"delayed": 0.014, "inconsistent": 0.050}),
            effect_from_evidence(context, "FleetDensity", {"high": 0.018}),
        ],
    )
    probs["EmergencyCoordinationLoad"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "FleetDensity", {"high": 0.040}),
            effect_from_evidence(context, "OperatorWorkload", {"high": 0.030, "overloaded": 0.090}),
            effect_from_evidence(context, "C2Quality", {"congested": 0.020, "lost": 0.080}),
        ],
    )
    probs["FaultDetectionFailure"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "MaintenanceQuality", {"degraded": 0.030, "enhanced": 0.0}),
            effect_from_evidence(context, "BatteryHealth", {"degraded": 0.020, "critical": 0.090}),
            effect_from_node(probs, "TelemetryDelay", 0.18),
        ],
    )
    probs["GeofenceBoundaryError"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "GeofenceData", {"stale": 0.050}),
            effect_from_evidence(context, "UTMDataQuality", {"delayed": 0.012, "inconsistent": 0.045}),
            effect_from_node(probs, "PositionInaccuracy", 0.25),
        ],
    )
    probs["NavigationInputCorruption"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "GNSSQuality", {"degraded": 0.040, "lost": 0.170}),
            effect_from_node(probs, "PositionInaccuracy", 0.22),
            effect_from_node(probs, "SoftwareSyncConflict", 0.16),
        ],
    )
    probs["WeatherFlightDisturbance"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "Weather", {"adverse": 0.055, "severe": 0.170}),
            effect_from_evidence(context, "WindTurbulence", {"turbulent": 0.050, "severe": 0.150}),
        ],
    )
    probs["PayloadBalanceShift"] = noisy_or(
        1.0e-4,
        [
            effect_from_evidence(context, "PayloadSecuring", {"poor": 0.055}),
            effect_from_evidence(context, "WindTurbulence", {"turbulent": 0.012, "severe": 0.050}),
        ],
    )

    probs["MotorSeizure_1_1_1"] = noisy_or(
        fmea_leak("1.1.1"),
        [
            effect_from_evidence(context, "Weather", {"adverse": 0.012, "severe": 0.040}),
            effect_from_evidence(context, "MaintenanceQuality", {"degraded": 0.025, "enhanced": 0.0}),
            effect_from_evidence(context, "FleetDensity", {"high": 0.010}),
        ],
    )
    probs["PropellerFracture_1_1_2"] = noisy_or(
        fmea_leak("1.1.2"),
        [
            effect_from_evidence(context, "UrbanObstacleExposure", {"high": 0.020}),
            effect_from_evidence(context, "MaintenanceQuality", {"degraded": 0.020, "enhanced": 0.0}),
            effect_from_evidence(context, "WindTurbulence", {"turbulent": 0.012, "severe": 0.040}),
        ],
    )
    probs["PropulsionSystemFailure_1_1"] = noisy_or(
        5.0e-5,
        [
            effect_from_node(probs, "MotorSeizure_1_1_1", 1.0),
            effect_from_node(probs, "PropellerFracture_1_1_2", 1.0),
        ],
    )
    probs["PowerSystemFault_1_2"] = noisy_or(
        fmea_leak("1.2.1"),
        [
            effect_from_evidence(context, "BatteryHealth", {"degraded": 0.025, "critical": 0.120}),
            effect_from_evidence(context, "Weather", {"adverse": 0.010, "severe": 0.030}),
        ],
    )
    probs["ControlNavigationFault_1_3"] = noisy_or(
        fmea_leak("1.3.1"),
        [
            effect_from_node(probs, "PositionInaccuracy", 0.18),
            effect_from_node(probs, "NavigationInputCorruption", 0.20),
            effect_from_evidence(context, "CloudLoad", {"high": 0.012, "overloaded": 0.050}),
        ],
    )

    probs["AirspaceConflictNotDetected_2_2_1"] = noisy_or(
        fmea_leak("2.2.1"),
        [
            effect_from_node(probs, "TelemetryDelay", 0.30),
            effect_from_node(probs, "PositionInaccuracy", 0.32),
            effect_from_node(probs, "CommunicationLoss", 0.25),
        ],
    )
    probs["RouteCoordinationFails_2_2_2"] = noisy_or(
        fmea_leak("2.2.2"),
        [
            effect_from_node(probs, "SoftwareSyncConflict", 0.30),
            effect_from_node(probs, "ReroutingPressure", 0.28),
            effect_from_evidence(context, "UTMDataQuality", {"delayed": 0.010, "inconsistent": 0.050}),
        ],
    )
    probs["SeparationDistanceViolated_2_2_3"] = noisy_or(
        fmea_leak("2.2.3"),
        [
            effect_from_node(probs, "PositionInaccuracy", 0.30),
            effect_from_node(probs, "TelemetryDelay", 0.30),
            effect_from_node(probs, "HighDensityAirspace", 0.34),
            effect_from_node(probs, "AirspaceConflictNotDetected_2_2_1", 0.25),
        ],
    )
    probs["DronesNotCoordinatedSafely"] = noisy_or(
        0.0,
        [
            probs["AirspaceConflictNotDetected_2_2_1"],
            probs["RouteCoordinationFails_2_2_2"],
            probs["SeparationDistanceViolated_2_2_3"],
        ],
    )

    probs["EmergencyLandingCommandFails_2_5_1"] = noisy_or(
        fmea_leak("2.5.1"),
        [
            effect_from_node(probs, "CommunicationLoss", 0.35),
            effect_from_node(probs, "EmergencyCoordinationLoad", 0.30),
            effect_from_node(probs, "SoftwareSyncConflict", 0.22),
        ],
    )
    probs["ReturnToHomeLogicFails_2_5_2"] = noisy_or(
        fmea_leak("2.5.2"),
        [
            effect_from_node(probs, "PositionInaccuracy", 0.32),
            effect_from_node(probs, "GeofenceBoundaryError", 0.30),
            effect_from_node(probs, "NavigationInputCorruption", 0.30),
        ],
    )
    probs["FleetGroundingFails_2_5_3"] = noisy_or(
        fmea_leak("2.5.3"),
        [
            effect_from_node(probs, "FaultDetectionFailure", 0.40),
            effect_from_node(probs, "TelemetryDelay", 0.25),
            effect_from_evidence(context, "OperatorWorkload", {"high": 0.020, "overloaded": 0.080}),
            effect_from_node(probs, "PropulsionSystemFailure_1_1", 0.25),
        ],
    )
    probs["IncidentHandlingFails_2_5_4"] = noisy_or(
        fmea_leak("2.5.4"),
        [
            effect_from_node(probs, "EmergencyCoordinationLoad", 0.34),
            effect_from_node(probs, "CommunicationLoss", 0.25),
            effect_from_node(probs, "HighDensityAirspace", 0.18),
        ],
    )
    probs["EmergencySafeguardsDoNotRecoverFleet"] = noisy_or(
        0.0,
        [
            probs["EmergencyLandingCommandFails_2_5_1"],
            probs["ReturnToHomeLogicFails_2_5_2"],
            probs["FleetGroundingFails_2_5_3"],
            probs["IncidentHandlingFails_2_5_4"],
        ],
    )

    probs["UnsafeRouteGenerated_2_1_2"] = noisy_or(
        fmea_leak("2.1.2"),
        [
            effect_from_node(probs, "PositionInaccuracy", 0.22),
            effect_from_node(probs, "ReroutingPressure", 0.28),
            effect_from_node(probs, "GeofenceBoundaryError", 0.20),
        ],
    )
    probs["OtherDroneConflict"] = noisy_or(
        0.0,
        [
            effect_from_node(probs, "SeparationDistanceViolated_2_2_3", 0.45),
            effect_from_node(probs, "RouteCoordinationFails_2_2_2", 0.22),
            effect_from_node(probs, "HighDensityAirspace", 0.20),
        ],
    )
    probs["NonDroneObstacleConflict"] = noisy_or(
        0.0,
        [
            effect_from_node(probs, "AirspaceConflictNotDetected_2_2_1", 0.25),
            effect_from_node(probs, "UnsafeRouteGenerated_2_1_2", 0.28),
            effect_from_evidence(context, "UrbanObstacleExposure", {"normal": 0.004, "high": 0.055}),
        ],
    )
    probs["StationaryObstacleConflict"] = noisy_or(
        0.0,
        [
            effect_from_node(probs, "UnsafeRouteGenerated_2_1_2", 0.35),
            effect_from_node(probs, "AirspaceConflictNotDetected_2_2_1", 0.22),
            effect_from_node(probs, "NonDroneObstacleConflict", 0.65),
        ],
    )
    probs["FlightFailing"] = noisy_or(
        0.0,
        [
            effect_from_node(probs, "PropulsionSystemFailure_1_1", 0.80),
            effect_from_node(probs, "PowerSystemFault_1_2", 0.45),
            effect_from_node(probs, "ControlNavigationFault_1_3", 0.45),
        ],
    )
    probs["DroneCollisionWithObstacle"] = noisy_or(
        0.0,
        [
            effect_from_node(probs, "OtherDroneConflict", 0.60),
            effect_from_node(probs, "StationaryObstacleConflict", 0.70),
            effect_from_node(probs, "FlightFailing", 0.55),
        ],
    )

    probs["LossCommunicationWithFleetController"] = noisy_or(
        0.0,
        [
            effect_from_node(probs, "CommunicationLoss", 0.45),
            effect_from_node(probs, "TelemetryDelay", 0.20),
            effect_from_node(probs, "ControlNavigationFault_1_3", 0.18),
        ],
    )
    probs["MechanicalFailure"] = noisy_or(
        0.0,
        [
            effect_from_node(probs, "PropulsionSystemFailure_1_1", 0.80),
            effect_from_node(probs, "PowerSystemFault_1_2", 0.60),
            effect_from_node(probs, "ControlNavigationFault_1_3", 0.40),
        ],
    )
    probs["DisturbanceLossOfControl"] = noisy_or(
        0.0,
        [
            effect_from_node(probs, "WeatherFlightDisturbance", 0.42),
            effect_from_node(probs, "PayloadBalanceShift", 0.35),
            effect_from_node(probs, "PositionInaccuracy", 0.20),
        ],
    )
    probs["LossOfControlDuringFlight"] = noisy_or(
        0.0,
        [
            effect_from_node(probs, "LossCommunicationWithFleetController", 0.55),
            effect_from_node(probs, "MechanicalFailure", 0.75),
            effect_from_node(probs, "DisturbanceLossOfControl", 0.65),
        ],
    )

    probs["AnySelectedSubsetEvent"] = noisy_or(
        0.0,
        [
            probs["DronesNotCoordinatedSafely"],
            probs["EmergencySafeguardsDoNotRecoverFleet"],
            probs["DroneCollisionWithObstacle"],
            probs["LossOfControlDuringFlight"],
        ],
    )

    return probs


OUTPUTS = [
    "DronesNotCoordinatedSafely",
    "EmergencySafeguardsDoNotRecoverFleet",
    "DroneCollisionWithObstacle",
    "LossOfControlDuringFlight",
    "AnySelectedSubsetEvent",
]


def run_scenarios() -> list[dict[str, object]]:
    results = []
    for scenario in SCENARIOS:
        context = dict(BASE_CONTEXT)
        context.update(scenario["evidence"])
        probs = evaluate(context)
        row: dict[str, object] = {
            "scenario_id": scenario["id"],
            "scenario_label": scenario["label"],
        }
        for output in OUTPUTS:
            row[output] = probs[output]
        ranked = sorted(OUTPUTS[:-1], key=lambda node: probs[node], reverse=True)
        row["dominant_outputs"] = "; ".join(
            f"{node}={probs[node]:.4g}" for node in ranked[:2]
        )
        results.append(row)

    baseline = float(results[0]["AnySelectedSubsetEvent"])
    for row in results:
        row["multiplier_vs_baseline"] = (
            float(row["AnySelectedSubsetEvent"]) / baseline
            if baseline
            else float("nan")
        )
    return results


def fieldnames() -> list[str]:
    return [
        "scenario_id",
        "scenario_label",
        "AnySelectedSubsetEvent",
        "multiplier_vs_baseline",
        "DronesNotCoordinatedSafely",
        "EmergencySafeguardsDoNotRecoverFleet",
        "DroneCollisionWithObstacle",
        "LossOfControlDuringFlight",
        "dominant_outputs",
    ]


def print_summary(results: list[dict[str, object]]) -> None:
    print("Subset BN scenario results, probability per flight hour")
    print("-" * 112)
    print(
        f"{'ID':<3} {'Scenario':<34} {'Any':>9} {'x base':>7} "
        f"{'Coord':>9} {'Emerg':>9} {'Collis':>9} {'LoC':>9}"
    )
    print("-" * 112)
    for row in results:
        print(
            f"{row['scenario_id']:<3} {row['scenario_label']:<34.34} "
            f"{float(row['AnySelectedSubsetEvent']):>9.5f} "
            f"{float(row['multiplier_vs_baseline']):>7.2f} "
            f"{float(row['DronesNotCoordinatedSafely']):>9.5f} "
            f"{float(row['EmergencySafeguardsDoNotRecoverFleet']):>9.5f} "
            f"{float(row['DroneCollisionWithObstacle']):>9.5f} "
            f"{float(row['LossOfControlDuringFlight']):>9.5f}"
        )

    print("-" * 112)
    print(
        f"{'ID':<3} {'Scenario':<34} {'Max Indv.':>9} "
        f"{'x base':>7} {'Collis':>9} {'LoC':>9} {'Coord':>9} {'Emerg':>9} "
    )
    print("-" * 112)

    for row in results:

        if float(row["DroneCollisionWithObstacle"]) > float(row["LossOfControlDuringFlight"]):
            limiting_rate = float(row["DroneCollisionWithObstacle"])
            multiplier = limiting_rate / float(results[0]["DroneCollisionWithObstacle"])
        else:            
            limiting_rate = float(row["LossOfControlDuringFlight"])
            multiplier = limiting_rate / float(results[0]["LossOfControlDuringFlight"])

        print(
            f"{row['scenario_id']:<3} {row['scenario_label']:<34.34} "
            f"{limiting_rate:>12.2e} "
            f"{float(multiplier):>7.2f} "
            f"{float(row['DroneCollisionWithObstacle']):>12.2e} "
            f"{float(row['LossOfControlDuringFlight']):>12.2e} "
            f"{float(row['DronesNotCoordinatedSafely']):>12.2e} "
            f"{float(row['EmergencySafeguardsDoNotRecoverFleet']):>12.2e} "
        )



def write_csv(results: list[dict[str, object]], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames())
        writer.writeheader()
        writer.writerows(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the selected-subset BN.")
    parser.add_argument(
        "--write-csv",
        nargs="?",
        const=str(DEFAULT_CSV_OUT),
        default=None,
        metavar="PATH",
        help="Optionally write the scenario table to CSV.",
    )
    args = parser.parse_args()

    results = run_scenarios()
    print_summary(results)

    if args.write_csv:
        out = Path(args.write_csv)
        write_csv(results, out)
        print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
