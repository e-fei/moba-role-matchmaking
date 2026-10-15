# Figure revision, 14 October 2026

The revision preserves the paper's typography, layout, algorithm, and recorded
experiments. All artwork is original vector drawing.

## Visual references

- Park and Sung, *Reward Dimension Reduction for Scalable Multi-Objective
  Reinforcement Learning*, ICLR 2025, Figures 1–2:
  https://proceedings.iclr.cc/paper_files/paper/2025/file/0fb3f8550a7624c4693388a2cbd55e1e-Paper-Conference.pdf
  The objective-space representation is useful for showing a trade-off directly.
  Our figure does not reproduce their artwork or claim a measured Pareto frontier.
- Kim and Oh, *Queueing Matching Bandits with Preference Feedback*, NeurIPS 2024,
  Figures 1–2:
  https://proceedings.neurips.cc/paper_files/paper/2024/file/76d2f8e328e1081c22a77ca0fa330ca5-Paper-Conference.pdf
  Their separate process illustration and metric panels motivate assigning a
  distinct explanatory purpose to each figure. Their learning method is not used
  by this homework's matcher.

## Decisions

- Burgundy, ochre, charcoal, and warm gray replace the previous blue palette.
  The algorithm overview uses a neutral warm background only for eligibility and
  anchor emphasis. Color is paired with symbols, labels, or outlines.
- Figure 2 shows exactly four pooled policy outcomes per scenario, positioned by
  mean completed wait and mean team pairwise gap. Direct labels replace a legend.
  The panels state completion rates and disclose their different horizontal ranges.
  No policy-connecting line implies an interpolated strategy or global frontier.
- Figure 3 uses paired endpoints and a thin connector to compare two population
  means. The connector is not a per-player trajectory or additive decomposition.
- Radar polygons were considered but rejected: seconds, points, and completion
  rates do not share a natural normalization. Polygon area would suggest an
  aggregate quality measure that the assignment does not define.
- Figure 2 now uses pooled observations, matching Table 3, rather than an
  unweighted average of run means. The distinction is small but real for Fixed 50.
  Captions and reporting conventions are updated accordingly. Per-seed results
  and run-level standard deviations remain available in the accompanying data;
  the sparse plot does not depict uncertainty intervals.
