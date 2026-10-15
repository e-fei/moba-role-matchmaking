# Five-role MOBA team matching

This C++17 project forms a team of five players,
with exactly one **top, jungle (jun), mid, ADC, and support**. Each player has one
fixed role, a ranking score, and a request time. Matching two opposing teams is
outside the assignment's scope.

**GitHub:** https://github.com/e-fei/moba-role-matchmaking

**Open source under the [MIT License](LICENSE).** The repository includes the
matching implementation, independent exhaustive tests, baseline experiments,
waiting-aware extension, saved measurements, and the report's vector artwork.

[English report](output/pdf/MOBA_Matchmaking_Report.pdf) ·
[Source guide](docs/REPOSITORY_STRUCTURE.md) ·
[Extension study](research/README.md)

## Quick start

```sh
make test
make run
```

A C++17 compiler, Make, and Python 3 are enough for the matcher and tests.
Use `make CXX=g++ test` on systems where GCC is preferred. For the complete
replay and packaging instructions, see the [source guide](docs/REPOSITORY_STRUCTURE.md).
Report generation additionally requires the packages in `requirements-report.txt`
and the macOS fonts listed in its generator.

## Objectives and tradeoff

For a team formed at time `t`, define:

```text
average waiting time W = sum(t - player.requestedAt) / 5
average score gap    G = sum(|score[i] - score[j]| for i < j) / 10
```

There are ten unordered pairs in a five-player team. The photo does not specify
how to measure a score gap; this solution uses mean absolute pairwise difference.

These objectives generally conflict. Matching available players immediately
reduces waiting but can produce large gaps. Waiting for more players can improve
skill balance. Without a tradeoff rule or a model of future arrivals, there is no
single policy that guarantees both global minima.

The policy here prioritizes the oldest player who can form a team within an
expanding score band, then minimizes `G` for that player within the band. This is
an online heuristic for the combined objectives; its per-anchor gap optimization
is exact. It does not claim to minimize average wait, maximize the number of teams
in a batch, or minimize total gap across all future teams.

## Queue and matching algorithm

Each queued record contains `(ID, role, score, requestedAt)`. An arrival-ordered
vector preserves FIFO priority. For each team selection, create a score-sorted
copy and prefix counts for the five roles.

1. Consider players in arrival order. Call the current player the **anchor**.
2. Compute their allowed rating distance:
   `band = min(maximumBand, initialBand + growthPerSecond * waitingSeconds)`.
3. Use binary search and role prefix counts to check the interval
   `[anchor.score - band, anchor.score + band]`. If any role is missing, try the
   next anchor. This avoids blocking the whole queue behind an infeasible player.
4. For the first feasible anchor, choose the team with minimum pairwise gap from
   that interval. The anchor must be included, and all five roles must differ.
5. Break equal-gap ties by comparing sorted `(requestTime, ID)` lists, preferring
   earlier requests, then smaller IDs.
6. Remove all five players together and repeat until no feasible team remains.

Default parameters are an initial distance of 50 points and growth of 10 points
per second, capped at 1,000,000. Scores are integers in `[0, 1,000,000]`. These are
illustrative parameters, not claims about any commercial game's matching rules.
The implementation floors fractional band widths, which preserves eligibility
for integer scores.

The band is a **team selection policy based on the anchor's wait**. It is not an
individual guarantee for every member: two selected players can differ by up to
twice the band, and newly arrived players can join an older player's wider band.
If individual limits are required, that is an additional constraint needing a
different eligibility check and optimizer.

## Exact gap optimization with 32 states

For five scores sorted as `x0 <= x1 <= x2 <= x3 <= x4`:

```text
sum(i < j) |xi - xj| = -4*x0 - 2*x1 + 0*x2 + 2*x3 + 4*x4
```

The score at position `k` is larger than `k` selected scores and smaller than
`4-k` selected scores, so its coefficient is `2*k - 4`.

Represent the roles already selected by a five-bit mask. `dp[mask]` stores the
lowest partial weighted sum and the corresponding players after processing a
prefix of the eligible players in score order. Initialize only `dp[0] = 0`.

For each eligible player with score `s`, role bit `b`, and each reachable mask
that does not contain `b`, let `k = popcount(mask)` and update:

```text
dp[mask | b] = min(dp[mask | b], dp[mask] + (2*k - 4)*s)
```

Skipping a player retains the previous state. Exclude other players in the
anchor's role, forcing a complete team to include the anchor. Process masks in
descending order. `dp[31]` is the minimum sum for all five roles; divide by ten
for the average gap. Partial sums can be negative, which is expected.

Correctness follows because every legal team is a score-ordered subsequence,
each transition selects one unused role, and the additive identity gives exactly
that team's pairwise difference sum. Future contributions depend only on how
many roles have been selected and the subsequent players; keeping the best
partial state per mask therefore preserves an optimal completion.

## Complexity

For `n` waiting players and `m <= n` eligible candidates:

- Sort and build prefix counts: `O(n log n)` time, `O(n)` space.
- Find the oldest feasible anchor: `O(n log n)` time using two binary searches per anchor.
- Optimize their team: `O(32*m)` time and 32 states, each holding at most five players.
- Remove the team: `O(n)` time.

Total per team selection: `O(n log n + 32*n)` time and `O(n)` space.
The simple implementation rebuilds the sorted index after each team, so a full
batch costs at most `O(n² log n)`. Joining and cancelling are `O(n)` because the
reference implementation checks IDs and removes entries by scanning a vector.
For a larger service, maintain ID indexes and role-specific ordered indexes
incrementally, and serialize queue changes and team removal in one matching
worker per pool.

## Run

```sh
make
make run
```

Example input:

```text
join 1 top 1500 0
join 2 jun 1510 1
join 3 mid 1490 2
join 4 adc 1520 3
join 5 sup 1480 4
match 4
quit
```

This produces one team with average wait **2 seconds** and average pairwise gap
**20 points**. `status` reports queue size; `cancel ID` removes a queued player.
IDs must be positive and unique among currently queued players. An ID can rejoin
after matching or cancellation. Request times and match times must be
nonnegative and globally nondecreasing, and are measured in seconds.

Malformed commands, including trailing tokens and numeric suffixes, are rejected
before any queue mutation. The CLI runs matching only when `match TIME` is entered. In a running game service,
call matching after arrivals and on a periodic timer, such as once per second,
so expanding bands are reconsidered even without new arrivals. This program
simulates timestamps; it does not run a background timer or network server.

## Verification and limitations

```sh
make test
```

Tests cover role completeness, empty queues, globally missing roles, band expansion,
fractional boundaries and caps, score and timestamp extremes, cancellation and
rejoining, invalid input and policies, exact ties, and no player reuse. They also
compare each resulting team's exact player IDs, gap, anchor, tie key, and band
membership against exhaustive enumeration across 1,000 seeded random queues.
The current suite verifies 1,437 random team selections and five malformed CLI
commands. Run `make sanitize` for AddressSanitizer and UndefinedBehaviorSanitizer.

An expanding band reduces skill-related starvation, but no algorithm can promise
a finite wait if a required role never arrives. A smaller maximum band can also
leave incompatible players waiting indefinitely. Greedy team choices affect
which players remain available for later teams.

To evaluate a policy, replay the same arrival stream under different band
parameters and compare mean and 95th-percentile wait, mean pairwise gap, team
count, and the number and ages of players still waiting, including breakdowns
by role. Reporting only matched players' average wait can hide starvation.

## Optimizations and report

The reviewed implementation uses five fixed player slots per DP state and maintains
the sorted age/ID tie key as candidates are appended. This avoids heap allocation
inside transitions and repeated key sorting during comparisons. A global role mask
also returns before sorting when a role is absent. These changes preserve selection
behavior; the general per-team and batch complexity bounds remain unchanged.

The English submission is `output/pdf/MOBA_Matchmaking_Report.pdf`. The current
revision has five pages of main text and a one-page reproducibility appendix,
with a two-column layout inspired by the official ICML example paper. It includes
the derivation, correctness argument, complexity analysis, worked examples, test
results, local microbenchmarks, synthetic policy comparisons, and a bounded age-reward
extension. An original vector overview follows the same players through queueing,
eligibility, subset search, and team formation. It is a homework
report, not a conference submission. The previous PDF is preserved under
`output/archive/`.

```sh
make experiment          # Writes experiment_results.json
make benchmark-compare   # Writes results/benchmark_before.json and benchmark_after.json
```

The experiment uses five fixed seeds, 1,000 arrivals per seed, balanced and
support-scarce role populations, four policies, and a finite cutoff at second 319.
It reports matched waits, gaps, pending counts and ages, and observed queue time
through the cutoff for all arrivals. The JSON includes definitions and all per-seed
data. Results describe synthetic workloads, not commercial games or global optima.

`reference/matchmaker_before.hpp` preserves the original implementation for timing
comparisons. `benchmarks.cpp` excludes queue construction and reports the median,
minimum, and maximum of seven runs. Compiler settings are visible in the Makefile.
The report can be regenerated with `report/build_report.py` using Python with
ReportLab and the specified macOS fonts; simulation JSON and benchmark summaries
must exist first.

The current figures use burgundy, ochre, charcoal, and warm gray. Figure 2 is an
objective-space comparison of mean matched wait and team gap, with four directly
labeled pooled policy outcomes per scenario. Completion rates are stated above
each panel; horizontal ranges differ and are disclosed in the caption. Figure 3
is a dumbbell comparison of pooled completed waits and cutoff-inclusive queue
residence. The connectors compare two population means, not individual trajectories.

`python3 report/paper_statistics.py` validates the saved experiments and writes
`results/paper_statistics.json`. Per-seed results and sample standard deviations
remain available there; the sparse new figures do not display uncertainty
intervals. Both plots use pooled metrics, matching the main results table.
The figures and displayed equations are vector artwork in the PDF.
`report/figure_design_notes.md` records the conference references and chart choices.


## Optional waiting-aware extension

The normal matcher and original experiment are unchanged. The separate prototype
under `research/` adds a capped reward for serving older teammates:

```text
R(T) = mean_i min(now - requestedAt_i, 120)
J_lambda(T) = G(T) - lambda * R(T)
```

Its DP remains exact with 32 states. For the same anchor and candidate pool,
the loss relative to the minimum-gap team is at most `96*lambda` score points.
Thus `lambda=0.1` permits at most 9.6 extra points locally. This bound does not
compare entire online schedules, whose later candidate pools differ.

```sh
make waiting-experiment
```

This command checks 3,822 selections against an exhaustive oracle and replays
seven weights on both five-seed workloads, writing `results/waiting_extension.json`.
At weight 0.1 in the scarce-support simulation, pending p95 age falls from 256
to 244 seconds, while mean gap rises from 113.48 to 118.02 points. Completed mean
wait increases as older players are served; all-arrival observed queue residence
stays at 109.912 seconds. This is service redistribution, not greater capacity
or a general waiting-time guarantee. `research/README.md` gives the full sweep,
proof, exact weight representation, and sanitizer commands.

Report generation requires the saved baseline, benchmark, and extension JSON,
Python with ReportLab, and the macOS fonts named in the generator:

```sh
python3 report/build_report.py
```

The three vector figures are defined in `report/overview.py` and
`report/charts.py`. The PDF and standalone PNG previews of the figures are
included in the submission archive. Earlier PDFs are preserved separately in
`output/archive/` and are not included in the current submission package.
