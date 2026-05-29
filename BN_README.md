# Bayesian Network Method

This folder contains the Bayesian Network (BN) work for assignment 3. The BN is the probability-assessment step after the FMEA/FTA filtering.

The full FMEA/FTA is not modelled here. The group first filtered the work to a smaller subset, then this BN estimates how likely those selected events are under different operating scenarios.

## What The BN Models

The BN has four selected outputs:

| Output | Level | Meaning |
|---|---|---|
| `DronesNotCoordinatedSafely` | fleet | fleet coordination or separation logic fails |
| `EmergencySafeguardsDoNotRecoverFleet` | fleet | emergency landing, RTH, grounding, or incident response fails |
| `DroneCollisionWithObstacle` | individual drone | a drone collides with another drone or non-drone obstacle |
| `LossOfControlDuringFlight` | individual drone | an individual drone loses stable controlled flight |

The script also calculates:

| Output | Meaning |
|---|---|
| `AnySelectedSubsetEvent` | probability that at least one of the four selected outputs occurs |

`AnySelectedSubsetEvent` is mainly for comparing scenarios. The four separate outputs are more useful for later ETA and ground-risk work.

## What The Connections Mean

In the diagram:

```text
child cause -> OR gate -> parent event
```

Solid arrows are the selected FTA logic translated into BN direction. They mean that the child event contributes to the parent event probability.

The purple `OR` gate means:

```text
if any child cause occurs, the parent event can occur
```

In the Python model this is calculated with a simple noisy-OR formula:

```text
P(parent) = 1 - product(1 - child contribution)
```

So adding more active causes increases the parent probability, but probabilities remain capped between 0 and 1.

## What The Colors Mean

| Diagram element | Meaning |
|---|---|
| Green boxes | scenario/evidence inputs, such as GNSS quality, fleet density, weather, or maintenance quality |
| Pink boxes | selected/highlighted FTA or FMEA elements carried into the BN |
| Blue boxes | support FTA nodes kept because they are needed to preserve the selected logic |
| Yellow boxes | selected output events |
| Red box | combined selected-subset output |
| Purple circle | OR gate inherited from the FTA |
| Dashed teal lane border | the lane is conditioned by the scenario/evidence inputs |

The green evidence boxes are not drawn with arrows into every affected node because that made the diagram look like extra FTA logic. In the script, they still change the probabilities.

## What The Probabilities Mean

All output probabilities are expressed per flight hour:

```text
P(event) / flight hour
```

Example:

```text
P = 0.0184 /fh
```

This means an estimated probability/rate of about `0.0184` for that event per flight hour under the selected scenario. It is not a measured real-world accident rate.

The current numbers come from:

| Input source | How it is used |
|---|---|
| Updated FMEA occurrence scores | converted into rough baseline probabilities for relevant failure nodes |
| Filtered FTA logic | defines which nodes connect to which outputs |
| Scenario settings | represent operating conditions such as high density, degraded GNSS, poor weather, or mechanical stress |
| Provisional causal strengths | our assumed effect sizes for how strongly one condition affects another |

The model is therefore suitable for scenario comparison, not final reliability claims.

## How The Numbers Are Produced

We do **not** propagate all of `S`, `O`, and `D` through the BN.

The current script uses them like this:

| FMEA value | Used in BN probabilities? | Role here |
|---|---:|---|
| `S` severity | no | kept for traceability and later consequence/risk evaluation |
| `O` occurrence | yes | converted into the baseline probability for FMEA-derived nodes |
| `D` detection | no | kept for traceability and possible mitigation discussion |
| `RPN = S x O x D` | no | useful for filtering/prioritising, but not propagated as probability |

The probability pipeline is:

```text
FMEA occurrence score O
  -> rough baseline rate per flight hour
  -> baseline leak probability for a BN node
  -> scenario evidence adds extra conditional contributions
  -> noisy-OR combines child contributions
  -> selected output probabilities
```

In the script, the occurrence conversion is:

```text
baseline_rate = 10^(-5 + 0.42 x O)
leak_probability = 0.30 x baseline_rate
```

Example:

```text
2.2.3 Minimum separation distance violated
O = 5.50
baseline_rate = 10^(-5 + 0.42 x 5.50) = about 0.00204 /fh
leak_probability = 0.30 x 0.00204 = about 0.00061 /fh
```

That leak is only the baseline for that node. The final scenario probability can be higher because other parents also contribute. For example, degraded GNSS, telemetry congestion, high fleet density, and airspace conflict can all increase the probability of separation violation.

Then the FTA/BN connections combine events. For example:

```text
Airspace conflict not detected
Conflicting route updates
Minimum separation distance violated
  -> OR
  -> Drones not coordinated safely
```

The output is therefore not just copied from one FMEA row. It is the result of baseline occurrence inputs plus scenario effects propagated through the selected FTA structure.

## Fleet vs Individual-Drone Treatment

The BN intentionally mixes two fleet-level outputs and two individual-drone outputs in one model.

This is because the selected subset mixes both levels. Some conditions, such as high fleet density or degraded positioning, affect both fleet coordination and individual-drone collision risk.

Grouped labels such as:

```text
1.1 / 1.2 / 1.3
2.1.2 / 2.2.1 / 2.2.3
```

mean that the BN node is a compact support category combining several source FTA/FMEA items.

## Scenario Outputs

Run:

```bash
python3 subset_bn_v1.py
```

The table reports:

| Column | Meaning |
|---|---|
| `Any` | probability of at least one selected output in that scenario |
| `x base` | multiplier relative to the baseline scenario |
| `Coord` | `DronesNotCoordinatedSafely` |
| `Emerg` | `EmergencySafeguardsDoNotRecoverFleet` |
| `Collis` | `DroneCollisionWithObstacle` |
| `LoC` | `LossOfControlDuringFlight` |

High `x base` values show which scenarios are most stressful for the selected subset.

## Files

| File | Purpose |
|---|---|
| `subset_bn_v1.py` | executable BN scenario model |
| `bn_subset_network_v1.drawio` | editable BN diagram |
| `bn_section_v1.tex` | draft report section |
| `bn_appendix_v1.tex` | appendix figure snippet |
| `README_verbose.md` | longer working explanation and traceability notes |
