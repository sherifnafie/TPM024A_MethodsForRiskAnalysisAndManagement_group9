#!/usr/bin/env python3
"""Subset Bayesian Network v2 for assignment 3.

This version follows the group's filtered scope in ``new_info.drawio``:
two fleet-level FTA branches and two individual-drone top events. It uses
the reconciled teammate LOPA values as first-pass prior rates for
FMEA-derived nodes, while retaining the final multiplier-based scenario
logic. The model is intended for transparent scenario comparison.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CSV_OUT = ROOT / "scenario_results_subset_v2.csv"
DEFAULT_SCENARIO_CONFIG = ROOT / "scenario_config_subset_v1.json"


# Updated FMEA rows from assignment3/FMEA/FMEA Hazard Sheet.xlsx.
# S/O/D/RPN are retained for traceability only. Direct prior rates are no
# longer inferred from occurrence numbers here; they are taken from the LOPA
# residual frequencies below.
FMEA = {
    "2.2.1": {
        "label": "Airspace conflict not detected",
        "level": "Fleet",
        "s": 7.6667,
        "o": 3.8333,
        "d": 5.8333,
        "rpn": 192,
    },
    "2.2.2": {
        "label": "Conflicting route updates issued",
        "level": "Fleet",
        "s": 5.8333,
        "o": 4.1667,
        "d": 5.0000,
        "rpn": 120,
    },
    "2.2.3": {
        "label": "Minimum separation distance violated",
        "level": "Fleet",
        "s": 6.1667,
        "o": 5.5000,
        "d": 5.6667,
        "rpn": 216,
    },
    "2.5.1": {
        "label": "Emergency landing command not executed",
        "level": "Fleet",
        "s": 9.0000,
        "o": 3.1667,
        "d": 7.3333,
        "rpn": 189,
    },
    "2.5.2": {
        "label": "Return-to-home triggered incorrectly",
        "level": "Fleet",
        "s": 6.8333,
        "o": 3.5000,
        "d": 6.6667,
        "rpn": 196,
    },
    "2.5.3": {
        "label": "Unsafe drones not grounded",
        "level": "Fleet",
        "s": 8.3333,
        "o": 3.5000,
        "d": 6.8333,
        "rpn": 224,
    },
    "2.5.4": {
        "label": "Incident response delayed",
        "level": "Fleet",
        "s": 7.6667,
        "o": 4.0000,
        "d": 6.0000,
        "rpn": 192,
    },
    "2.1.2": {
        "label": "Unsafe route generated",
        "level": "Fleet",
        "s": 7.1667,
        "o": 4.1667,
        "d": 4.6667,
        "rpn": 140,
    },
    "1.1.1": {
        "label": "Motor seizure or complete loss of thrust",
        "level": "Single drone",
        "s": 6.1667,
        "o": 3.8333,
        "d": 6.5000,
        "rpn": 168,
    },
    "1.1.2": {
        "label": "Propeller fracture during flight",
        "level": "Single drone",
        "s": 5.8333,
        "o": 4.3333,
        "d": 7.3333,
        "rpn": 168,
    },
    "1.2.1": {
        "label": "Battery cell damage",
        "level": "Single drone",
        "s": 5.1667,
        "o": 5.6667,
        "d": 5.3333,
        "rpn": 150,
    },
    "1.3.1": {
        "label": "Flight controller software crash",
        "level": "Single drone",
        "s": 5.1667,
        "o": 4.3333,
        "d": 6.1667,
        "rpn": 120,
    },
}


# Reconciled LOPA values from the teammate BN table. These are used as direct
# first-pass prior rates for all FMEA-derived nodes with a listed value.
LOPA_RESIDUAL_FREQ = {
    "2.2.1": 3.42e-8,
    "2.2.2": 3.42e-5,
    "2.2.3": 3.42e-7,
    "2.5.1": 3.42e-9,
    "2.5.2": 3.42e-7,
    "2.5.3": 3.42e-7,
    "2.5.4": 3.42e-5,
    "2.1.2": 3.42e-5,
    "1.1.1": 3.42e-8,
    "1.1.2": 1.71e-6,
    "1.2.1": 3.42e-4,
    "1.3.1": 3.42e-5,
}


def noisy_or(leak: float, causes: list[float]) -> float:
    p_false = 1.0 - leak
    for cause in causes:
        p_false *= 1.0 - min(max(cause, 0.0), 1.0)
    return min(max(1.0 - p_false, 0.0), 1.0)


def lopa_prior(fmea_id: str) -> float:
    """Return the residual frequency used as a BN prior for one LOPA row."""
    return LOPA_RESIDUAL_FREQ[fmea_id]


def load_scenario_config(
    path: Path,
) -> tuple[dict[str, str], list[dict[str, object]]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")

    base_context_raw = data.get("base_context")
    scenarios_raw = data.get("scenarios")
    if not isinstance(base_context_raw, dict):
        raise ValueError(f"{path} must define a 'base_context' object")
    if not isinstance(scenarios_raw, list) or not scenarios_raw:
        raise ValueError(f"{path} must define a non-empty 'scenarios' list")

    base_context = {str(key): str(value) for key, value in base_context_raw.items()}
    scenarios: list[dict[str, object]] = []

    for index, scenario_raw in enumerate(scenarios_raw, start=1):
        if not isinstance(scenario_raw, dict):
            raise ValueError(f"scenario #{index} in {path} must be an object")
        indicator_settings_raw = scenario_raw.get("indicator_settings")
        if indicator_settings_raw is None:
            indicator_settings_raw = scenario_raw.get("evidence", {})
        if not isinstance(indicator_settings_raw, dict):
            raise ValueError(
                f"scenario #{index} in {path} must define indicator_settings as an object"
            )

        indicator_settings = {
            str(key): str(value) for key, value in indicator_settings_raw.items()
        }
        unknown = sorted(set(indicator_settings) - set(base_context))
        if unknown:
            raise ValueError(
                f"scenario {scenario_raw.get('id', index)!r} references unknown "
                f"context variable(s): {', '.join(unknown)}"
            )

        scenarios.append(
            {
                "id": str(scenario_raw["id"]),
                "label": str(scenario_raw["label"]),
                "indicator_settings": indicator_settings,
            }
        )

    return base_context, scenarios


def multiplier_from_indicator(
    context: dict[str, str], variable: str, multipliers: dict[str, float]
) -> float:
    return multipliers.get(context[variable], 1.0)


def apply_multipliers(
    rate: float, context: dict[str, str], modifiers: list[tuple[str, dict[str, float]]]
) -> float:
    adjusted = rate
    for variable, multipliers in modifiers:
        adjusted *= multiplier_from_indicator(context, variable, multipliers)
    return min(max(adjusted, 0.0), 1.0)


def adjusted_lopa_rate(
    fmea_id: str, context: dict[str, str], modifiers: list[tuple[str, dict[str, float]]]
) -> float:
    return apply_multipliers(lopa_prior(fmea_id), context, modifiers)


def weighted_or(weighted_rates: list[tuple[float, float]]) -> float:
    return noisy_or(0.0, [rate * weight for rate, weight in weighted_rates])


def evaluate(context: dict[str, str]) -> dict[str, float]:
    rates: dict[str, float] = {}

    rates["AirspaceConflictNotDetected_2_2_1"] = adjusted_lopa_rate(
        "2.2.1",
        context,
        [
            ("C2Quality", {"congested": 2.0, "lost": 8.0}),
            ("GNSSQuality", {"degraded": 2.2, "lost": 6.0}),
            ("FleetDensity", {"low": 0.7, "high": 1.8}),
            ("UTMDataQuality", {"delayed": 1.4, "inconsistent": 2.5}),
        ],
    )
    rates["SeparationDistanceViolated_2_2_3"] = adjusted_lopa_rate(
        "2.2.3",
        context,
        [
            ("FleetDensity", {"low": 0.5, "high": 3.0}),
            ("UrbanObstacleExposure", {"low": 0.7, "high": 1.8}),
            ("GNSSQuality", {"degraded": 2.2, "lost": 6.0}),
            ("C2Quality", {"congested": 1.8, "lost": 4.0}),
            ("UTMDataQuality", {"delayed": 1.5, "inconsistent": 2.5}),
        ],
    )
    rates["RouteCoordinationFails_2_2_2"] = adjusted_lopa_rate(
        "2.2.2",
        context,
        [
            ("CloudLoad", {"high": 1.8, "overloaded": 3.5}),
            ("UTMDataQuality", {"delayed": 1.8, "inconsistent": 3.0}),
            ("FleetDensity", {"low": 0.7, "high": 1.6}),
        ],
    )
    rates["DronesNotCoordinatedSafely"] = noisy_or(
        0.0,
        [
            rates["AirspaceConflictNotDetected_2_2_1"],
            rates["RouteCoordinationFails_2_2_2"],
            rates["SeparationDistanceViolated_2_2_3"],
        ],
    )

    rates["EmergencyLandingCommandFails_2_5_1"] = adjusted_lopa_rate(
        "2.5.1",
        context,
        [
            ("C2Quality", {"congested": 5.0, "lost": 15.0}),
            ("OperatorWorkload", {"high": 3.0, "overloaded": 8.0}),
            ("CloudLoad", {"high": 2.0, "overloaded": 4.0}),
            ("FleetDensity", {"high": 1.6}),
        ],
    )
    rates["ReturnToHomeLogicFails_2_5_2"] = adjusted_lopa_rate(
        "2.5.2",
        context,
        [
            ("GNSSQuality", {"degraded": 2.5, "lost": 8.0}),
            ("GeofenceData", {"stale": 3.0}),
            ("UTMDataQuality", {"delayed": 1.5, "inconsistent": 2.5}),
            ("Weather", {"adverse": 1.3, "severe": 2.0}),
        ],
    )
    rates["FleetGroundingFails_2_5_3"] = adjusted_lopa_rate(
        "2.5.3",
        context,
        [
            ("MaintenanceQuality", {"enhanced": 0.5, "degraded": 2.0}),
            ("BatteryHealth", {"degraded": 2.2, "critical": 6.0}),
            ("OperatorWorkload", {"high": 2.5, "overloaded": 7.0}),
            ("C2Quality", {"congested": 1.6, "lost": 4.0}),
            ("FleetDensity", {"low": 0.7, "high": 1.5}),
        ],
    )
    rates["IncidentHandlingFails_2_5_4"] = adjusted_lopa_rate(
        "2.5.4",
        context,
        [
            ("OperatorWorkload", {"high": 4.0, "overloaded": 8.0}),
            ("C2Quality", {"congested": 2.0, "lost": 5.0}),
            ("CloudLoad", {"high": 2.0, "overloaded": 4.0}),
            ("FleetDensity", {"high": 2.0}),
        ],
    )
    rates["EmergencySafeguardsDoNotRecoverFleet"] = noisy_or(
        0.0,
        [
            rates["EmergencyLandingCommandFails_2_5_1"],
            rates["ReturnToHomeLogicFails_2_5_2"],
            rates["FleetGroundingFails_2_5_3"],
            rates["IncidentHandlingFails_2_5_4"],
        ],
    )

    rates["MotorSeizure_1_1_1"] = adjusted_lopa_rate(
        "1.1.1",
        context,
        [
            ("Weather", {"adverse": 2.0, "severe": 5.0}),
            ("WindTurbulence", {"turbulent": 1.8, "severe": 4.0}),
            ("MaintenanceQuality", {"enhanced": 0.5, "degraded": 2.5}),
            ("FleetDensity", {"high": 1.3}),
        ],
    )
    rates["PropellerFracture_1_1_2"] = adjusted_lopa_rate(
        "1.1.2",
        context,
        [
            ("UrbanObstacleExposure", {"low": 0.7, "high": 1.8}),
            ("MaintenanceQuality", {"enhanced": 0.5, "degraded": 1.8}),
            ("WindTurbulence", {"turbulent": 2.2, "severe": 5.0}),
            ("Weather", {"adverse": 1.4, "severe": 2.5}),
        ],
    )
    rates["PropulsionSystemFailure_1_1"] = noisy_or(
        0.0,
        [
            rates["MotorSeizure_1_1_1"],
            rates["PropellerFracture_1_1_2"],
        ],
    )
    rates["PowerSystemFault_1_2"] = adjusted_lopa_rate(
        "1.2.1",
        context,
        [
            ("BatteryHealth", {"healthy": 0.8, "degraded": 3.0, "critical": 8.0}),
            ("MaintenanceQuality", {"enhanced": 0.5, "degraded": 1.7}),
            ("Weather", {"adverse": 1.5, "severe": 2.5}),
        ],
    )
    rates["ControlNavigationFault_1_3"] = adjusted_lopa_rate(
        "1.3.1",
        context,
        [
            ("GNSSQuality", {"degraded": 1.8, "lost": 5.0}),
            ("CloudLoad", {"high": 1.7, "overloaded": 3.0}),
            ("C2Quality", {"congested": 1.4, "lost": 3.0}),
        ],
    )

    rates["UnsafeRouteGenerated_2_1_2"] = adjusted_lopa_rate(
        "2.1.2",
        context,
        [
            ("GeofenceData", {"stale": 2.5}),
            ("UTMDataQuality", {"delayed": 1.7, "inconsistent": 3.0}),
        ],
    )
    rates["OtherDroneConflict"] = apply_multipliers(
        weighted_or(
            [
                (rates["SeparationDistanceViolated_2_2_3"], 0.60),
                (rates["RouteCoordinationFails_2_2_2"], 0.25),
            ]
        ),
        context,
        [
            ("FleetDensity", {"low": 0.6, "high": 2.2}),
            ("UrbanObstacleExposure", {"high": 1.3}),
        ],
    )
    rates["NonDroneObstacleConflict"] = apply_multipliers(
        weighted_or(
            [
                (rates["AirspaceConflictNotDetected_2_2_1"], 0.25),
                (rates["UnsafeRouteGenerated_2_1_2"], 0.35),
            ]
        ),
        context,
        [
            ("UrbanObstacleExposure", {"low": 0.6, "normal": 1.2, "high": 3.5}),
            ("GNSSQuality", {"degraded": 1.5, "lost": 3.0}),
        ],
    )
    rates["StationaryObstacleConflict"] = weighted_or(
        [
            (rates["UnsafeRouteGenerated_2_1_2"], 0.35),
            (rates["NonDroneObstacleConflict"], 0.65),
        ]
    )
    rates["FlightFailing"] = weighted_or(
        [
            (rates["PropulsionSystemFailure_1_1"], 0.80),
            (rates["PowerSystemFault_1_2"], 0.45),
            (rates["ControlNavigationFault_1_3"], 0.45),
        ]
    )
    rates["DroneCollisionWithObstacle"] = noisy_or(
        0.0,
        [
            rates["OtherDroneConflict"] * 0.60,
            rates["StationaryObstacleConflict"] * 0.70,
            rates["FlightFailing"] * 0.55,
        ],
    )

    rates["LossCommunicationWithFleetController"] = apply_multipliers(
        weighted_or(
            [
                (rates["AirspaceConflictNotDetected_2_2_1"], 0.15),
                (rates["ControlNavigationFault_1_3"], 0.18),
            ]
        ),
        context,
        [
            ("C2Quality", {"congested": 2.5, "lost": 8.0}),
            ("CloudLoad", {"high": 1.6, "overloaded": 3.0}),
        ],
    )
    rates["WeatherFlightDisturbance"] = apply_multipliers(
        lopa_prior("1.1.2") * 0.08,
        context,
        [
            ("Weather", {"adverse": 3.0, "severe": 7.0}),
            ("WindTurbulence", {"turbulent": 3.0, "severe": 8.0}),
        ],
    )
    rates["PayloadBalanceShift"] = apply_multipliers(
        lopa_prior("1.1.2") * 0.04,
        context,
        [
            ("PayloadSecuring", {"poor": 5.0}),
            ("WindTurbulence", {"turbulent": 1.5, "severe": 3.0}),
        ],
    )
    rates["MechanicalFailure"] = weighted_or(
        [
            (rates["PropulsionSystemFailure_1_1"], 0.80),
            (rates["PowerSystemFault_1_2"], 0.60),
            (rates["ControlNavigationFault_1_3"], 0.40),
        ]
    )
    rates["DisturbanceLossOfControl"] = weighted_or(
        [
            (rates["WeatherFlightDisturbance"], 0.42),
            (rates["PayloadBalanceShift"], 0.35),
            (rates["ControlNavigationFault_1_3"], 0.15),
        ]
    )
    rates["LossOfControlDuringFlight"] = noisy_or(
        0.0,
        [
            rates["LossCommunicationWithFleetController"] * 0.55,
            rates["MechanicalFailure"] * 0.75,
            rates["DisturbanceLossOfControl"] * 0.65,
        ],
    )

    return rates


OUTPUTS = [
    "DronesNotCoordinatedSafely",
    "EmergencySafeguardsDoNotRecoverFleet",
    "DroneCollisionWithObstacle",
    "LossOfControlDuringFlight",
]


def run_scenarios(
    base_context: dict[str, str], scenarios: list[dict[str, object]]
) -> list[dict[str, object]]:
    results = []
    for scenario in scenarios:
        context = dict(base_context)
        indicator_settings = scenario["indicator_settings"]
        if not isinstance(indicator_settings, dict):
            raise ValueError(
                f"scenario {scenario['id']!r} has invalid indicator settings"
            )
        context.update(indicator_settings)
        probs = evaluate(context)
        row: dict[str, object] = {
            "scenario_id": scenario["id"],
            "scenario_label": scenario["label"],
        }
        for output in OUTPUTS:
            row[output] = probs[output]
        ranked = sorted(OUTPUTS, key=lambda node: probs[node], reverse=True)
        row["dominant_outputs"] = "; ".join(
            f"{node}={probs[node]:.4g}" for node in ranked[:2]
        )
        results.append(row)

    baseline = {output: float(results[0][output]) for output in OUTPUTS}
    for row in results:
        multipliers = [
            float(row[output]) / baseline[output]
            for output in OUTPUTS
            if baseline[output]
        ]
        row["largest_output_multiplier_vs_baseline"] = max(multipliers)
    return results


def fieldnames() -> list[str]:
    return [
        "scenario_id",
        "scenario_label",
        "largest_output_multiplier_vs_baseline",
        "DronesNotCoordinatedSafely",
        "EmergencySafeguardsDoNotRecoverFleet",
        "DroneCollisionWithObstacle",
        "LossOfControlDuringFlight",
        "dominant_outputs",
    ]


def print_summary(results: list[dict[str, object]]) -> None:
    print("Subset BN scenario results, selected top-event rates per flight hour")
    print("-" * 118)
    print(
        f"{'ID':<3} {'Scenario':<34} {'max x':>7} "
        f"{'Coord':>12} {'Emerg':>12} {'Collision':>12} {'LoC':>12}"
    )
    print("-" * 118)
    for row in results:
        print(
            f"{row['scenario_id']:<3} {row['scenario_label']:<34.34} "
            f"{float(row['largest_output_multiplier_vs_baseline']):>7.2f} "
            f"{float(row['DronesNotCoordinatedSafely']):>12.3e} "
            f"{float(row['EmergencySafeguardsDoNotRecoverFleet']):>12.3e} "
            f"{float(row['DroneCollisionWithObstacle']):>12.3e} "
            f"{float(row['LossOfControlDuringFlight']):>12.3e}"
        )


def write_csv(results: list[dict[str, object]], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames())
        writer.writeheader()
        writer.writerows(results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the selected-subset BN.")
    parser.add_argument(
        "--scenario-config",
        default=str(DEFAULT_SCENARIO_CONFIG),
        metavar="PATH",
        help="Scenario JSON file to load.",
    )
    parser.add_argument(
        "--write-csv",
        nargs="?",
        const=str(DEFAULT_CSV_OUT),
        default=None,
        metavar="PATH",
        help="Optionally write the scenario table to CSV.",
    )
    args = parser.parse_args()

    base_context, scenarios = load_scenario_config(Path(args.scenario_config))
    results = run_scenarios(base_context, scenarios)
    print_summary(results)

    if args.write_csv:
        out = Path(args.write_csv)
        write_csv(results, out)
        print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
