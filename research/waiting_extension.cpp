#include "waiting_aware_matchmaker.hpp"

// Import the exact stream generator and metric definitions used in the paper.
// The renamed demonstration main is never called; C++'s implicit main return
// no longer applies to that unused function after the preprocessor rename.
#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wreturn-type"
#elif defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreturn-type"
#endif
#define main baseline_experiment_main_unused
#include "../experiments.cpp"
#undef main
#if defined(__clang__)
#pragma clang diagnostic pop
#elif defined(__GNUC__)
#pragma GCC diagnostic pop
#endif

#include <cassert>
#include <functional>
#include <set>

constexpr std::array<int, 7> lambdaTwentyUnitsSweep{{0, 2, 5, 10, 20, 40, 100}};
constexpr Time rewardCap = 120;

struct ExtendedMetrics {
    Metrics base;
    std::vector<Time> pendingAges;
    void merge(const ExtendedMetrics& other) {
        base.merge(other.base);
        pendingAges.insert(pendingAges.end(), other.pendingAges.begin(), other.pendingAges.end());
    }
};

void check(bool condition, const char* message) {
    if (!condition) throw std::logic_error(message);
}

bool sameTeams(const std::vector<Team>& first, const std::vector<Team>& second) {
    if (first.size() != second.size()) return false;
    for (std::size_t i = 0; i < first.size(); ++i) {
        if (first[i].formedAt != second[i].formedAt) return false;
        for (int r = 0; r < 5; ++r) {
            if (first[i].players[r].id != second[i].players[r].id) return false;
        }
    }
    return true;
}

ExtendedMetrics simulateExtension(const std::vector<Player>& arrivals, int lambdaTwentyUnits) {
    WaitingAwareMatchmaker matcher({50, 10, 1000000}, lambdaTwentyUnits, rewardCap);
    Matchmaker baseline({50, 10, 1000000});
    std::map<int, Player> pending;
    ExtendedMetrics result;
    result.base.runs = 1;
    result.base.arrivals = static_cast<int>(arrivals.size());
    std::size_t next = 0;
    for (Time now = 0; now <= lastTick; ++now) {
        while (next < arrivals.size() && arrivals[next].requestedAt == now) {
            const auto& player = arrivals[next++];
            pending.emplace(player.id, player);
            matcher.join(player);
            if (lambdaTwentyUnits == 0) baseline.join(player);
        }
        const auto formed = matcher.match(now);
        if (lambdaTwentyUnits == 0) {
            check(sameTeams(formed, baseline.match(now)), "lambda=0 changed the baseline schedule");
        }
        for (const auto& team : formed) {
            result.base.addTeam(team);
            for (const auto& player : team.players) {
                check(pending.erase(player.id) == 1, "Duplicate or unqueued player");
            }
        }
    }
    check(pending.size() == matcher.size(), "Pending count mismatch");
    for (const auto& entry : pending) {
        const auto& player = entry.second;
        ++result.base.pendingByRole[static_cast<int>(player.role)];
        const Time age = lastTick - player.requestedAt;
        result.base.oldestPendingAge = std::max(result.base.oldestPendingAge, age);
        result.base.pendingAgeSum += age;
        result.pendingAges.push_back(age);
    }
    check(result.base.teams * 5 + static_cast<int>(pending.size()) == arrivalsPerRun,
          "Population conservation failed");
    return result;
}

void emitExtended(std::ostream& out, const ExtendedMetrics& result) {
    out << "{\"original_metrics\":";
    emitMetrics(out, result.base);
    auto ages = result.pendingAges;
    std::sort(ages.begin(), ages.end());
    out << ",\"p95_pending_age_seconds\":";
    if (ages.empty()) out << "null";
    else out << ages[(95 * ages.size() + 99) / 100 - 1];
    out << '}';
}

struct ExpectedWeightedTeam {
    std::array<Player, 5> players;
    std::int64_t cost;
    std::array<std::pair<Time, int>, 5> ageKey;
};

// Independent oracle: enumerate every role combination and sum all 10 gaps.
// It does not use the DP recurrence or the DP's incremental age-key insertion.
std::optional<ExpectedWeightedTeam> weightedOracle(const std::vector<Player>& pending,
        Time now, Matchmaker::Policy policy, int lambdaTwentyUnits, Time cap) {
    for (const auto& anchor : pending) {
        const int band = static_cast<int>(std::min<double>(policy.maximumBand,
            policy.initialBand + policy.growthPerSecond * (now - anchor.requestedAt)));
        std::array<std::vector<Player>, 5> choices;
        for (const auto& player : pending) {
            if (std::abs(player.score - anchor.score) > band) continue;
            if (player.role == anchor.role && player.id != anchor.id) continue;
            choices[static_cast<int>(player.role)].push_back(player);
        }
        if (std::any_of(choices.begin(), choices.end(), [](const auto& v) { return v.empty(); })) continue;
        std::array<Player, 5> selected{};
        std::optional<ExpectedWeightedTeam> best;
        std::function<void(int)> visit = [&](int role) {
            if (role == 5) {
                std::int64_t cost = 0;
                for (int i = 0; i < 5; ++i) {
                    cost -= static_cast<std::int64_t>(lambdaTwentyUnits) *
                            std::min<Time>(now - selected[i].requestedAt, cap);
                    for (int j = i + 1; j < 5; ++j) cost += 10 * static_cast<std::int64_t>(std::abs(selected[i].score - selected[j].score));
                }
                std::array<std::pair<Time, int>, 5> ageKey{};
                for (int i = 0; i < 5; ++i) ageKey[i] = {selected[i].requestedAt, selected[i].id};
                std::sort(ageKey.begin(), ageKey.end());
                if (!best || cost < best->cost || (cost == best->cost && ageKey < best->ageKey)) {
                    best = ExpectedWeightedTeam{selected, cost, ageKey};
                }
                return;
            }
            for (const auto& p : choices[role]) {
                selected[role] = p;
                visit(role + 1);
            }
        };
        visit(0);
        return best;
    }
    return std::nullopt;
}

int checkRandomized() {
    SplitMix64 random(20261011);
    int checkedTeams = 0;
    for (int lambdaTwentyUnits : lambdaTwentyUnitsSweep) {
        for (int trial = 0; trial < 300; ++trial) {
            const bool collisions = trial >= 150;
            const Matchmaker::Policy policy{
                collisions ? static_cast<int>(random.bounded(3)) : static_cast<int>(random.bounded(150)),
                collisions ? 0.5 : 5,
                collisions ? 10 : 500};
            WaitingAwareMatchmaker matcher(policy, lambdaTwentyUnits, rewardCap);
            Matchmaker baseline(policy);
            std::array<int, 20> ids{};
            for (int i = 0; i < 20; ++i) ids[i] = i + 1;
            for (int i = 20; i > 1; --i) std::swap(ids[i - 1], ids[random.bounded(i)]);
            std::vector<Player> pending;
            for (int i = 0; i < 20; ++i) {
                const Player p{ids[i], static_cast<Role>(random.bounded(5)),
                    static_cast<int>(random.bounded(collisions ? 5 : 1001)), i / 4};
                pending.push_back(p);
                matcher.join(p);
                if (lambdaTwentyUnits == 0) baseline.join(p);
            }
            for (Time now : {Time{4}, Time{20}, Time{120}, Time{200}}) {
                const auto teams = matcher.match(now);
                if (lambdaTwentyUnits == 0) check(sameTeams(teams, baseline.match(now)), "Random lambda=0 mismatch");
                for (const auto& team : teams) {
                    const auto expected = weightedOracle(pending, now, policy, lambdaTwentyUnits, rewardCap);
                    check(expected.has_value(), "DP returned an infeasible team");
                    check(team.formedAt == now, "Invalid team timestamp");
                    const auto qualityOnly = weightedOracle(pending, now, policy, 0, rewardCap);
                    check(qualityOnly.has_value(), "Missing local quality-only optimum");
                    const std::int64_t qualityGapSum = qualityOnly->cost / 10;
                    std::int64_t gapSum = 0;
                    for (int i = 0; i < 5; ++i) {
                        for (int j = i + 1; j < 5; ++j) {
                            gapSum += std::abs(team.players[i].score - team.players[j].score);
                        }
                    }
                    check(gapSum >= qualityGapSum, "Quality-only oracle not minimal");
                    // The anchor is shared: only the other four capped waits differ.
                    // G_lambda - G_0 <= (4/5) lambda C, with C=120.
                    check(5 * (gapSum - qualityGapSum) <=
                          2 * static_cast<std::int64_t>(lambdaTwentyUnits) * rewardCap,
                          "Local score-loss certificate violated");
                    for (int r = 0; r < 5; ++r) {
                        check(team.players[r].id == expected->players[r].id, "Weighted optimum or tie mismatch");
                        check(static_cast<int>(team.players[r].role) == r, "Invalid role");
                        const auto it = std::find_if(pending.begin(), pending.end(), [&](const Player& p) {
                            return p.id == team.players[r].id;
                        });
                        check(it != pending.end(), "Selected player is no longer pending");
                        pending.erase(it);
                    }
                    ++checkedTeams;
                }
                check(!weightedOracle(pending, now, policy, lambdaTwentyUnits, rewardCap), "Did not exhaust feasible teams");
                check(matcher.size() == pending.size(), "Pending mismatch in random test");
            }
        }
    }
    return checkedTeams;
}

void checkIllustrativeExample() {
    Matchmaker qualityOnly;
    WaitingAwareMatchmaker waitingAware(Matchmaker::Policy{}, 2, 120);  // lambda=0.1
    const std::vector<Player> arrivals{
        {1, Role::Top, 1000, 0}, {2, Role::Jungle, 1001, 0},
        {3, Role::Mid, 1000, 0}, {4, Role::Adc, 1000, 0},
        {5, Role::Support, 1000, 0}, {6, Role::Jungle, 1000, 100}};
    // A single matching snapshot at t=100, to isolate teammate selection.
    for (const auto& player : arrivals) {
        qualityOnly.join(player);
        waitingAware.join(player);
    }
    const auto first = qualityOnly.match(100);
    const auto second = waitingAware.match(100);
    check(first.size() == 1 && second.size() == 1, "Illustration team count mismatch");
    check(first[0].players[1].id == 6 && second[0].players[1].id == 2,
          "Illustration teammate mismatch");
    check(first[0].averageGap() == 0 && second[0].averageGap() == 0.4,
          "Illustration score gap mismatch");
    check(first[0].averageWait() == 80 && second[0].averageWait() == 100,
          "Illustration mean age mismatch");
}

int main(int argc, char** argv) {
    try {
        if (argc > 2) throw std::invalid_argument("Usage: waiting_extension [output.json]");
        checkIllustrativeExample();
        const int checkedTeams = checkRandomized();
        std::ofstream file;
        if (argc == 2) {
            file.open(argv[1]);
            if (!file) throw std::runtime_error("Cannot open output file");
        }
        auto& out = argc == 2 ? file : std::cout;
        out << std::fixed << std::setprecision(6);
        out << "{\n  \"experiment\":\"Capped waiting reward within first feasible anchor band\",\n"
            << "  \"objective\":\"J_lambda(T)=G(T)-lambda R(T), R(T)=mean_i min(now-requestedAt_i,120); 10J=pairwise_gap_sum-2lambda*capped_wait_sum\",\n"
            << "  \"parameters\":{\"lambda_score_points_per_second\":[0,0.1,0.25,0.5,1,2,5],\"cap_seconds\":120,"
            << "\"initial_band\":50,\"growth_per_second\":10,\"maximum_band\":1000000},\n"
            << "  \"workload\":{\"source\":\"makeStream in experiments.cpp, imported directly\",\"seeds\":[1,2,3,4,5],"
            << "\"arrivals_per_run\":1000,\"arrivals_per_second\":5,\"last_arrival_second\":199,"
            << "\"last_matching_second\":319,\"score_range\":[1000,2000],"
            << "\"balanced_role_counts\":[200,200,200,200,200],\"support_scarce_role_counts\":[225,225,225,225,100]},\n"
            << "  \"validation\":{\"random_queues\":2100,\"independent_exhaustive_team_checks\":" << checkedTeams
            << ",\"lambda_zero_random_queues\":300,\"lambda_zero_streams\":10,\"lambda_zero_stream_ticks\":3200,"
            << "\"exact_team_ids_and_times_checked\":true,\"local_loss_bound_checked_for_every_oracle_team\":true,\"all_passed\":true},\n"
            << "  \"metric_notes\":{\"original_metrics\":\"Same emitMetrics and Metrics definitions as experiments.cpp; matched-only waits, team-average gaps, pending ages and censored all-arrival queue residence.\","
            << "\"p95\":\"Nearest rank; pooled across all players from five seeds, not average of five p95 values.\","
            << "\"pooling\":\"Counts and durations summed; gap team-weighted; pending age player-weighted; oldest pending maximum.\","
            << "\"scope\":\"Synthetic exploratory sweep. This changes local teammate selection and is neither globally optimal nor a guarantee of fairness or lower wait.\"},\n"
            << "  \"scenarios\":[\n";
        for (int scenario = 0; scenario < 2; ++scenario) {
            if (scenario) out << ",\n";
            out << "    {\"name\":\"" << (scenario ? "support_scarce" : "balanced") << "\",\"results\":[\n";
            for (std::size_t p = 0; p < lambdaTwentyUnitsSweep.size(); ++p) {
                if (p) out << ",\n";
                const int lambdaTwentyUnits = lambdaTwentyUnitsSweep[p];
                ExtendedMetrics pooled;
                out << "      {\"lambda\":" << lambdaTwentyUnits / 20.0 << ",\"per_seed\":[";
                for (std::size_t s = 0; s < seeds.size(); ++s) {
                    if (s) out << ',';
                    const auto result = simulateExtension(makeStream(scenario != 0, seeds[s]), lambdaTwentyUnits);
                    pooled.merge(result);
                    out << "{\"seed\":" << seeds[s] << ",\"metrics\":";
                    emitExtended(out, result);
                    out << '}';
                }
                out << "],\"pooled\":";
                emitExtended(out, pooled);
                out << '}';
            }
            out << "\n    ]}";
        }
        out << "\n  ]\n}\n";
        std::cerr << "Validated " << checkedTeams << " exhaustive team selections across 2100 queues.\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
