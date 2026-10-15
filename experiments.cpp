#include "matchmaker.hpp"

#include <array>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <string>
#include <vector>

// Portable experiment generator: no implementation-defined standard distributions.
class SplitMix64 {
public:
    explicit SplitMix64(std::uint64_t seed) : state_(seed) {}
    std::uint64_t next() {
        std::uint64_t z = (state_ += UINT64_C(0x9e3779b97f4a7c15));
        z = (z ^ (z >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
        z = (z ^ (z >> 27)) * UINT64_C(0x94d049bb133111eb);
        return z ^ (z >> 31);
    }
    std::uint64_t bounded(std::uint64_t bound) {
        const std::uint64_t threshold = (std::uint64_t{0} - bound) % bound;
        std::uint64_t value;
        do { value = next(); } while (value < threshold);
        return value % bound;
    }
private:
    std::uint64_t state_;
};

constexpr int arrivalsPerRun = 1000;
constexpr Time lastArrival = 199;
constexpr Time lastTick = 319;
constexpr std::array<std::uint64_t, 5> seeds{{1, 2, 3, 4, 5}};

struct Metrics {
    int runs = 0;
    int arrivals = 0;
    int teams = 0;
    double gapSum = 0;
    std::vector<Time> matchedWaits;
    std::array<int, 5> pendingByRole{};
    Time oldestPendingAge = 0;
    std::int64_t pendingAgeSum = 0;

    void addTeam(const Team& team) {
        ++teams;
        gapSum += team.averageGap();
        for (const auto& player : team.players) {
            matchedWaits.push_back(team.formedAt - player.requestedAt);
        }
    }

    void merge(const Metrics& other) {
        runs += other.runs;
        arrivals += other.arrivals;
        teams += other.teams;
        gapSum += other.gapSum;
        matchedWaits.insert(matchedWaits.end(), other.matchedWaits.begin(), other.matchedWaits.end());
        for (int i = 0; i < 5; ++i) pendingByRole[i] += other.pendingByRole[i];
        oldestPendingAge = std::max(oldestPendingAge, other.oldestPendingAge);
        pendingAgeSum += other.pendingAgeSum;
    }
};

struct PolicySpec {
    const char* name;
    bool fifo;
    Matchmaker::Policy policy;
};

const std::array<PolicySpec, 4> policies{{
    {"role_fifo", true, {50, 0, 1000000}},
    {"fixed_50", false, {50, 0, 1000000}},
    {"adaptive_10", false, {50, 10, 1000000}},
    {"adaptive_30", false, {50, 30, 1000000}},
}};

std::vector<Player> makeStream(bool scarce, std::uint64_t seed) {
    SplitMix64 generator(seed);
    std::vector<Role> roles;
    for (int role = 0; role < 5; ++role) {
        const int count = scarce ? (role == 4 ? 100 : 225) : 200;
        for (int i = 0; i < count; ++i) roles.push_back(static_cast<Role>(role));
    }
    for (std::size_t i = roles.size(); i > 1; --i) {
        std::swap(roles[i - 1], roles[generator.bounded(i)]);
    }
    std::vector<Player> stream;
    for (int i = 0; i < arrivalsPerRun; ++i) {
        stream.push_back({i + 1, roles[i], 1000 + static_cast<int>(generator.bounded(1001)), i / 5});
    }
    return stream;
}

Metrics simulate(const std::vector<Player>& arrivals, const PolicySpec& spec) {
    Matchmaker matcher(spec.policy);
    std::array<std::deque<Player>, 5> fifo;
    std::map<int, Player> pending;
    Metrics result;
    result.runs = 1;
    result.arrivals = static_cast<int>(arrivals.size());
    std::size_t next = 0;
    for (Time now = 0; now <= lastTick; ++now) {
        while (next < arrivals.size() && arrivals[next].requestedAt == now) {
            const auto& player = arrivals[next++];
            pending.emplace(player.id, player);
            if (spec.fifo) fifo[static_cast<int>(player.role)].push_back(player);
            else matcher.join(player);
        }
        std::vector<Team> formed;
        if (spec.fifo) {
            while (std::all_of(fifo.begin(), fifo.end(), [](const auto& queue) { return !queue.empty(); })) {
                Team team{{}, now};
                for (int role = 0; role < 5; ++role) {
                    team.players[role] = fifo[role].front();
                    fifo[role].pop_front();
                }
                formed.push_back(team);
            }
        } else {
            formed = matcher.match(now);
        }
        for (const auto& team : formed) {
            result.addTeam(team);
            for (const auto& player : team.players) {
                if (pending.erase(player.id) != 1) throw std::logic_error("Duplicate or unqueued player");
            }
        }
    }
    if (!spec.fifo && pending.size() != matcher.size()) throw std::logic_error("Pending count mismatch");
    for (const auto& entry : pending) {
        const auto& player = entry.second;
        ++result.pendingByRole[static_cast<int>(player.role)];
        const Time age = lastTick - player.requestedAt;
        result.oldestPendingAge = std::max(result.oldestPendingAge, age);
        result.pendingAgeSum += age;
    }
    if (result.teams * 5 + static_cast<int>(pending.size()) != arrivalsPerRun) {
        throw std::logic_error("Population conservation failed");
    }
    return result;
}

void emitMetrics(std::ostream& out, const Metrics& result) {
    auto waits = result.matchedWaits;
    std::sort(waits.begin(), waits.end());
    const std::size_t count = waits.size();
    const int pending = std::accumulate(result.pendingByRole.begin(), result.pendingByRole.end(), 0);
    const auto totalWait = std::accumulate(waits.begin(), waits.end(), std::int64_t{0});
    out << "{\"runs\":" << result.runs
        << ",\"arrivals\":" << result.arrivals
        << ",\"teams\":" << result.teams
        << ",\"matched_players\":" << count
        << ",\"match_rate\":" << static_cast<double>(count) / result.arrivals
        << ",\"matched_wait_sum_seconds\":" << totalWait
        << ",\"mean_matched_wait_seconds\":" << (count ? static_cast<double>(totalWait) / count : 0)
        << ",\"p95_matched_wait_seconds\":" << (count ? waits[(95 * count + 99) / 100 - 1] : 0)
        << ",\"mean_team_pairwise_gap\":" << (result.teams ? result.gapSum / result.teams : 0)
        << ",\"pending_players\":" << pending
        << ",\"pending_age_sum_seconds\":" << result.pendingAgeSum
        << ",\"mean_pending_age_seconds\":" << (pending ? static_cast<double>(result.pendingAgeSum) / pending : 0)
        << ",\"observed_mean_queue_time_seconds\":" << static_cast<double>(totalWait + result.pendingAgeSum) / result.arrivals
        << ",\"oldest_pending_age_seconds\":";
    if (pending) out << result.oldestPendingAge;
    else out << "null";
    out << ",\"pending_by_role\":{\"top\":" << result.pendingByRole[0]
        << ",\"jun\":" << result.pendingByRole[1]
        << ",\"mid\":" << result.pendingByRole[2]
        << ",\"adc\":" << result.pendingByRole[3]
        << ",\"sup\":" << result.pendingByRole[4] << "}}";
}

int main(int argc, char** argv) {
    std::ofstream file;
    if (argc > 2) {
        std::cerr << "Usage: experiments [output.json]\n";
        return 1;
    }
    if (argc == 2) {
        file.open(argv[1]);
        if (!file) { std::cerr << "Cannot open output file\n"; return 1; }
    }
    std::ostream& out = argc == 2 ? file : std::cout;
    out << std::fixed << std::setprecision(6);
    out << "{\n  \"experiment\":\"Seeded role-constrained matchmaking comparison\",\n"
        << "  \"workload\":{\"seeds\":[1,2,3,4,5],\"arrivals_per_run\":1000,"
        << "\"arrivals_per_second\":5,\"first_arrival_second\":0,\"last_arrival_second\":" << lastArrival
        << ",\"last_matching_second\":" << lastTick << ",\"drain_ticks\":120,"
        << "\"score_min_inclusive\":1000,\"score_max_inclusive\":2000,"
        << "\"balanced_role_counts\":[200,200,200,200,200],"
        << "\"support_scarce_role_counts\":[225,225,225,225,100],"
        << "\"role_order\":[\"top\",\"jun\",\"mid\",\"adc\",\"sup\"],"
        << "\"schedule\":\"At each integer tick enqueue all five arrivals, then exhaust all feasible teams; no arrivals after second 199.\","
        << "\"generator\":\"SplitMix64 initialized with each seed; unbiased rejection sampling for bounded integers; Fisher-Yates shuffle exact role populations first, then generate scores in arrival order. Reinitialize the generator per scenario and seed.\"},\n"
        << "  \"metric_definitions\":{"
        << "\"wait\":\"Match time minus request time, in seconds; mean and nearest-rank p95 use matched players only.\","
        << "\"pairwise_gap\":\"For each team, mean absolute score difference over its ten unordered pairs; average equally across formed teams.\","
        << "\"observed_mean_queue_time\":\"Matched waiting times plus pending ages at second 319, divided by all arrivals; truncated queue residence time for every arrival, not an estimate of eventual completed wait.\","
        << "\"pooling\":\"Pool player waits and team gaps across five seeds; sum counts; report the maximum oldest pending age across seeds.\","
        << "\"censoring\":\"Pending players at second 319 are excluded from matched-wait statistics; their counts and ages are reported separately.\","
        << "\"scope\":\"Synthetic sensitivity experiment only; no production, commercial-game, statistical-significance, or global-optimality claim.\"},\n"
        << "  \"policies\":[";
    for (std::size_t i = 0; i < policies.size(); ++i) {
        if (i) out << ',';
        const auto& policy = policies[i];
        out << "{\"name\":\"" << policy.name << "\",\"initial_band\":";
        if (policy.fifo) out << "null,\"growth_per_second\":null,\"maximum_band\":null";
        else out << policy.policy.initialBand << ",\"growth_per_second\":" << policy.policy.growthPerSecond
                 << ",\"maximum_band\":" << policy.policy.maximumBand;
        out << '}';
    }
    out << "],\n  \"scenarios\":[\n";
    for (int scenario = 0; scenario < 2; ++scenario) {
        if (scenario) out << ",\n";
        out << "    {\"name\":\"" << (scenario ? "support_scarce" : "balanced") << "\",\"results\":[\n";
        for (std::size_t p = 0; p < policies.size(); ++p) {
            if (p) out << ",\n";
            Metrics pooled;
            out << "      {\"policy\":\"" << policies[p].name << "\",\"per_seed\":[";
            for (std::size_t s = 0; s < seeds.size(); ++s) {
                if (s) out << ',';
                const auto result = simulate(makeStream(scenario != 0, seeds[s]), policies[p]);
                pooled.merge(result);
                out << "{\"seed\":" << seeds[s] << ",\"metrics\":";
                emitMetrics(out, result);
                out << '}';
            }
            out << "],\"pooled\":";
            emitMetrics(out, pooled);
            out << '}';
        }
        out << "\n    ]}";
    }
    out << "\n  ]\n}\n";
}
