# Waiting-aware teammate selection: an exploratory extension

This directory contains a separate experimental matcher. `matchmaker.hpp`, the
normal command-line program, and the original experiment remain unchanged.

The baseline gives the oldest feasible anchor priority, then minimizes the
team's mean pairwise score gap. The extension also gives waiting teammates a
small, capped selection reward. It does not change the anchor, the expanding
score band, or the 32 role-mask states.

## Objective and implementation

For team `T`, let `G(T)` be its mean absolute score difference over ten pairs,
and let

```
R(T) = (1/5) sum_i min(now - requestedAt_i, C),   C = 120 seconds.
J_lambda(T) = G(T) - lambda * R(T).
```

`lambda` has units of score points per second. The cap limits the influence of
very old requests; it is not a wait-time guarantee. For sorted team scores, the
baseline identity still applies:

```
10 G(T) = sum_{k=0}^4 (2k - 4) * score_k.
100 J_lambda(T) = 10 * sum_{k=0}^4 (2k - 4) * score_k
                 - 20 * lambda * sum_i min(wait_i, C).
```

The waiting term is additive, so the same DP remains exact for this local
objective, with unchanged asymptotic complexity. Costs are represented as
integers. The API takes `lambdaTwentyUnits = 20 * lambda`; all seven values in
the sweep are represented exactly. Equal objectives use the original sorted
request-time/ID key. Setting `lambda=0` reproduces the baseline, including ties.

## A local score-loss certificate

Fix one queue snapshot, its first feasible anchor, and that anchor's candidate
band. Let `T_0` minimize `G` and `T_lambda` minimize `J_lambda` over the same
candidate teams. Then

```
0 <= G(T_lambda) - G(T_0)
   <= lambda * (R(T_lambda) - R(T_0))
   <= (4/5) * lambda * C.
```

The middle inequality follows by comparing the two objective values. The last
inequality uses their shared anchor: only four capped waits can differ, each by
at most `C`. With `C=120`, the permitted local loss is at most `96*lambda` score
points. A user-facing budget `epsilon` can therefore be converted to
`lambda = epsilon / 96` (the prototype currently supports increments of 0.05).
For example, `lambda=0.1` gives a 9.6-point local certificate.

This bound compares alternative teams **at the same snapshot**. It does not
bound the difference between average gaps in complete simulations: selecting a
different team changes future queues, anchors, and candidate bands.

## Reproduce

Run these commands from the repository root:

```sh
clang++ -std=c++17 -O2 -Wall -Wextra -Wpedantic research/waiting_extension.cpp -o research/waiting_extension
./research/waiting_extension results/waiting_extension.json
```

Optional memory/undefined-behavior validation:

```sh
clang++ -std=c++17 -O1 -g -Wall -Wextra -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer research/waiting_extension.cpp -o research/waiting_extension_sanitized
./research/waiting_extension_sanitized research/waiting_extension_sanitized.json
```

The experiment imports `makeStream`, the baseline metric collector, and JSON
metric writer directly from `experiments.cpp`. Thus the streams, finite horizon,
percentile convention, pooling, and censoring definitions are identical to the
main report. Each scenario uses seeds 1 through 5, 1,000 arrivals per seed,
5 arrivals per second at times 0 through 199, scores in [1000,2000], and matching
through second 319. The balanced workload has 200 players per role; support-scarce
has 225 in each other role and 100 supports. All policies have initial band 50,
growth 10 points/second, and maximum band 1,000,000.

The output includes every seed and pooled metrics for the full
sweep `lambda in {0, 0.1, 0.25, 0.5, 1, 2, 5}`. The `pooled.original_metrics`
object follows the original experiment schema. `pooled.p95_pending_age_seconds`
is an additional nearest-rank percentile over pending players pooled across
five seeds.

## Results

All balanced policies match 5,000/5,000 players, with no pending players. Every
support-scarce policy matches 2,500/5,000 players; all 2,500 pending players are
in the four non-support roles. The rare role imposes the same capacity ceiling.

Balanced workload (pooled):

| lambda | Mean gap | Mean matched wait (s) | Matched p95 wait (s) | All-arrival observed mean queue time (s) |
|---:|---:|---:|---:|---:|
| 0 | 104.6944 | 9.121 | 30 | 9.121 |
| 0.1 | 104.1346 | 9.026 | 30 | 9.026 |
| 0.25 | 103.3944 | 9.165 | 30 | 9.165 |
| 0.5 | 101.4612 | 9.010 | 29 | 9.010 |
| 1 | 103.0192 | 9.031 | 29 | 9.031 |
| 2 | 101.8184 | 9.137 | 29 | 9.137 |
| 5 | 101.3248 | 9.173 | 28 | 9.173 |

Support-scarce workload (pooled):

| lambda | Mean gap | Mean matched wait (s) | Matched p95 wait (s) | Mean pending age (s) | Pending p95 age (s) | All-arrival observed mean queue time (s) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 113.4844 | 34.5712 | 123 | 185.2528 | 256 | 109.912 |
| 0.1 | 118.0152 | 40.4500 | 119 | 179.3740 | 244 | 109.912 |
| 0.25 | 109.9096 | 42.2396 | 115 | 177.5844 | 238 | 109.912 |
| 0.5 | 115.3248 | 42.9724 | 113 | 176.8576 | 235 | 109.915 |
| 1 | 116.2300 | 43.4868 | 111 | 176.3352 | 233 | 109.911 |
| 2 | 112.6208 | 43.8672 | 110 | 175.9548 | 230 | 109.911 |
| 5 | 116.9604 | 44.1740 | 108 | 175.6560 | 228 | 109.915 |

In these streams the added reward shifts service toward older waiting players.
For `lambda=0.1`, scarce-support pending p95 age falls by 12 seconds, and matched
p95 wait falls by 4 seconds. The mean wait among matched players rises by
5.8788 seconds because the matched population includes older requests. The
all-arrival observed mean queue time is unchanged to the displayed precision.
This is redistribution of waiting, not increased capacity or an overall waiting
reduction. Five-seed synthetic observations do not establish general superiority.
Neither monotonic score-gap improvement nor the best value of lambda should be
inferred from this small parameter sweep.

The all-arrival metric is `(sum of completed waits + sum of ages still pending
at 319) / all arrivals`. It is truncated residence time, not eventual waiting
time. Under a common arrival stream, it equals queue occupancy integrated over
the observation window and divided by arrivals. Policies with the same team
completion times therefore have the same total observed queue residence, even
when they choose different players. This explains why matched-only averages
must be interpreted alongside pending ages.

## Checks and an illustration

The executable checks 2,100 randomized queues against an independent exhaustive
oracle, including collision-heavy scores, simultaneous arrivals, shuffled IDs,
band boundaries, cap saturation, and exact tie outcomes. It verifies 3,822 team
selections and the local score-loss certificate for every selected team. Lambda
zero additionally matches every team ID and formation time from the baseline in
300 random queues and all 10 experiment streams (3,200 matching ticks).

A six-player snapshot isolates the selection effect. At `t=100`, the anchor and
three fixed teammates have score 1000 and have waited 100 seconds. Two junglers
are available: A has score 1001 and has waited 100 seconds; B has score 1000 and
has just arrived. The baseline selects B, giving `G=0, R=80`; `lambda=0.1` selects
A, giving `G=0.4, R=100`. Their weighted objectives are `-8` and `-9.6`,
respectively. This is a snapshot illustration with a single matching call, not
a continuous-arrival simulation. The executable checks this example too.

This extension is presented as a small, interpretable design experiment. It is
not a claim of a novel general matchmaking algorithm, a global optimum,
starvation-freedom, or improved outcomes on real game traffic.
