#include "matchmaker.hpp"

#include <cassert>
#include <functional>
#include <iostream>
#include <limits>
#include <random>
#include <set>

template <class F>
void rejects(F operation) {
    bool rejected = false;
    try { operation(); } catch (const std::invalid_argument&) { rejected = true; }
    assert(rejected);
}

struct ExpectedTeam {
    Player anchor;
    int band;
    std::int64_t gapSum;
    std::array<Player, 5> players;
    std::array<std::pair<Time, int>, 5> ageKey;
};

// Independent oracle: enumerate role combinations and sum actual pair distances.
// It deliberately does not reuse the DP recurrence or its incremental tie key.
std::optional<ExpectedTeam> bruteForce(const std::vector<Player>& pending,
                                     Time now, Matchmaker::Policy policy) {
    for (const auto& anchor : pending) {
        int band = static_cast<int>(std::min<double>(policy.maximumBand,
            policy.initialBand + policy.growthPerSecond * (now - anchor.requestedAt)));
        std::array<std::vector<Player>, 5> choices;
        for (const auto& p : pending) {
            if (std::abs(p.score - anchor.score) > band) continue;
            if (p.role == anchor.role && p.id != anchor.id) continue;
            choices[static_cast<int>(p.role)].push_back(p);
        }
        bool complete = true;
        for (const auto& role : choices) if (role.empty()) complete = false;
        if (!complete) continue;
        std::optional<ExpectedTeam> best;
        std::array<Player, 5> selected{};
        std::function<void(int)> visit = [&](int role) {
            if (role == 5) {
                std::int64_t sum = 0;
                for (int i = 0; i < 5; ++i) {
                    for (int j = i + 1; j < 5; ++j) {
                        sum += std::abs(selected[i].score - selected[j].score);
                    }
                }
                std::array<std::pair<Time, int>, 5> key{};
                for (int i = 0; i < 5; ++i) {
                    key[i] = {selected[i].requestedAt, selected[i].id};
                }
                std::sort(key.begin(), key.end());
                if (!best || sum < best->gapSum ||
                    (sum == best->gapSum && key < best->ageKey)) {
                    best = ExpectedTeam{anchor, band, sum, selected, key};
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

void verifyBatch(const std::vector<Team>& teams, std::vector<Player>& pending,
                 Time now, Matchmaker::Policy policy) {
    std::set<int> used;
    for (const auto& team : teams) {
        auto expected = bruteForce(pending, now, policy);
        assert(expected);
        assert(std::abs(team.averageGap() - static_cast<double>(expected->gapSum) / 10) < 1e-9);
        bool includesAnchor = false;
        for (int role = 0; role < 5; ++role) {
            const auto& p = team.players[role];
            assert(static_cast<int>(p.role) == role && used.insert(p.id).second);
            assert(p.requestedAt <= team.formedAt && team.formedAt == now);
            assert(p.id == expected->players[role].id);  // Verify the full tie result.
            assert(std::abs(p.score - expected->anchor.score) <= expected->band);
            includesAnchor |= p.id == expected->anchor.id;
            auto it = std::find_if(pending.begin(), pending.end(),
                [&](const Player& queued) { return queued.id == p.id; });
            assert(it != pending.end());
            assert(p.role == it->role && p.score == it->score && p.requestedAt == it->requestedAt);
            pending.erase(it);
        }
        assert(includesAnchor);
    }
    assert(!bruteForce(pending, now, policy));  // Matching must exhaust feasible teams.
}

int main() {
    {
        Matchmaker q;
        assert(q.match(0).empty());
        for (int r = 0; r < 4; ++r) q.join({r + 1, static_cast<Role>(r), 1000, 0});
        assert(q.match(100000).empty());  // Time cannot create a missing role.
        q.join({5, Role::Support, 1000, 100000});
        auto teams = q.match(100000);
        assert(teams.size() == 1 && q.size() == 0);
        assert(teams[0].averageGap() == 0 && teams[0].averageWait() == 80000);
    }
    {
        Matchmaker q({10, 10, 100});
        for (int r = 0; r < 5; ++r) q.join({r + 1, static_cast<Role>(r), r == 4 ? 1100 : 1000, 0});
        assert(q.match(8).empty());
        assert(q.match(9).size() == 1);  // Inclusive band boundary.
    }
    {
        Matchmaker q({20, 0, 20});
        q.join({1, Role::Top, 0, 0});
        for (int r = 0; r < 5; ++r) q.join({r + 2, static_cast<Role>(r), 1000, 1});
        auto teams = q.match(1);
        assert(teams.size() == 1 && teams[0].players[0].id == 2);
        assert(q.size() == 1);  // An infeasible oldest player does not block others.
        assert(q.cancel(1) && !q.cancel(1));
        rejects([&] { q.join({1, Role::Top, 0, 0}); });
        q.join({1, Role::Top, 1000, 2});
        rejects([&] { q.join({1, Role::Mid, 1000, 2}); });
        rejects([&] { q.match(1); });
        rejects([&] { q.join({2, static_cast<Role>(5), 1000, 2}); });
        rejects([&] { q.join({2, Role::Mid, -1, 2}); });
        rejects([] { Matchmaker invalid({100, -1, 1000}); });
    }
    {
        Matchmaker q({100, 0, 100});
        q.join({1, Role::Top, 1000, 0});
        q.join({10, Role::Jungle, 1000, 1});
        q.join({2, Role::Jungle, 1000, 2});
        for (int r = 2; r < 5; ++r) q.join({r + 2, static_cast<Role>(r), 1000, 2});
        auto teams = q.match(2);
        assert(teams.size() == 1 && teams[0].players[1].id == 10);  // Age before ID.
    }
    {
        // More than five players, but no support: the global role check must fail.
        Matchmaker q;
        for (int i = 0; i < 12; ++i) q.join({i + 1, static_cast<Role>(i % 4), 1000, 0});
        assert(q.match(100000).empty() && q.size() == 12);
        q.join({13, Role::Support, 1000, 100000});
        assert(q.cancel(13));
        assert(q.match(100001).empty());
        q.join({13, Role::Support, 1000, 100001});
        assert(q.match(100001).size() == 1 && q.size() == 8);
    }
    {
        // Anchor priority is FIFO at equal times; teammate ties use smaller IDs.
        Matchmaker::Policy policy{0, 0, 0};
        Matchmaker q(policy);
        std::vector<Player> pending;
        for (int r = 0; r < 5; ++r) {
            for (int id : {100 - 10 * r, r + 1}) {
                Player p{id, static_cast<Role>(r), 1000, 0};
                pending.push_back(p);
                q.join(p);
            }
        }
        auto teams = q.match(0);
        assert(teams.size() == 2 && teams[0].players[0].id == 100);
        for (int r = 1; r < 5; ++r) assert(teams[0].players[r].id == r + 1);
        verifyBatch(teams, pending, 0, policy);
        assert(pending.empty() && q.size() == 0);
        q.join({100, Role::Top, 1000, 0});  // IDs may rejoin after matching.
        assert(q.size() == 1);
    }
    {
        // Domain extremes and the maximum possible five-player mean pairwise gap.
        Matchmaker q({1000000, 0, 1000000});
        for (int r = 0; r < 5; ++r) q.join({r + 1, static_cast<Role>(r), r < 3 ? 0 : 1000000, 0});
        auto teams = q.match(0);
        assert(teams.size() == 1 && teams[0].averageGap() == 600000);
    }
    {
        // A fractional band admits distance 2 at t=4, not t=3; the cap stays binding.
        Matchmaker q({0, 0.5, 2});
        for (int r = 0; r < 5; ++r) q.join({r + 1, static_cast<Role>(r), r == 4 ? 1002 : 1000, 0});
        assert(q.match(3).empty());
        assert(q.match(4).size() == 1);
        for (int r = 0; r < 5; ++r) q.join({r + 1, static_cast<Role>(r), r == 4 ? 1003 : 1000, 4});
        assert(q.match(1000000).empty());
    }
    {
        // First, middle, and last score-order positions must all force the anchor.
        for (int anchorScore : {0, 500000, 1000000}) {
            Matchmaker::Policy policy{1000000, 0, 1000000};
            Matchmaker q(policy);
            std::vector<Player> pending{{10, Role::Top, anchorScore, 0},
                                        {1, Role::Top, 500000, 1}};
            for (int r = 1; r < 5; ++r) pending.push_back({r + 1, static_cast<Role>(r), r * 200000, 1});
            for (const auto& p : pending) q.join(p);
            auto teams = q.match(1);
            assert(teams.size() == 1 && teams[0].players[0].id == 10);
            verifyBatch(teams, pending, 1, policy);
        }
    }
    {
        // Time differences remain representable, even at the largest timestamp.
        const Time end = std::numeric_limits<Time>::max();
        Matchmaker q;
        for (int r = 0; r < 5; ++r) q.join({r + 1, static_cast<Role>(r), 1000, end - 4 + r});
        auto teams = q.match(end);
        assert(teams.size() == 1 && teams[0].averageWait() == 2);
        Matchmaker old;
        for (int r = 0; r < 5; ++r) old.join({r + 1, static_cast<Role>(r), r * 250000, 0});
        teams = old.match(end);
        assert(teams.size() == 1 && std::isfinite(teams[0].averageWait()));
    }
    {
        rejects([] { Matchmaker invalid({-1, 1, 100}); });
        rejects([] { Matchmaker invalid({20, 1, 10}); });
        rejects([] { Matchmaker invalid({0, 1, 1000001}); });
        rejects([] { Matchmaker invalid({0, std::numeric_limits<double>::quiet_NaN(), 100}); });
        rejects([] { Matchmaker invalid({0, std::numeric_limits<double>::infinity(), 100}); });
        Matchmaker q;
        rejects([&] { q.join({0, Role::Top, 1000, 0}); });
        rejects([&] { q.join({-1, Role::Top, 1000, 0}); });
        rejects([&] { q.join({1, static_cast<Role>(-1), 1000, 0}); });
        rejects([&] { q.join({1, Role::Top, 1000001, 0}); });
        rejects([&] { q.join({1, Role::Top, 1000, -1}); });
        rejects([&] { q.match(-1); });
        rejects([] { parseRole("invalid"); });
        assert(q.size() == 0);
    }
    std::mt19937 random(20260917);
    int verifiedTeams = 0;
    for (int trial = 0; trial < 500; ++trial) {
        Matchmaker::Policy policy{static_cast<int>(random() % 150), 5, 500};
        Matchmaker q(policy);
        std::vector<Player> pending;
        for (int i = 0; i < 15; ++i) {
            Player p{i + 1, static_cast<Role>(random() % 5), static_cast<int>(random() % 1001), i};
            pending.push_back(p);
            q.join(p);
        }
        for (Time now : {Time{14}, Time{40}, Time{100}}) {
            auto teams = q.match(now);
            verifyBatch(teams, pending, now, policy);
            verifiedTeams += static_cast<int>(teams.size());
            assert(q.size() == pending.size());
        }
    }
    // Collision-heavy scores, simultaneous arrivals, and shuffled IDs expose tie bugs.
    for (int trial = 0; trial < 500; ++trial) {
        Matchmaker::Policy policy{static_cast<int>(random() % 3), 0.5, 10};
        Matchmaker q(policy);
        std::array<int, 20> ids{};
        for (int i = 0; i < 20; ++i) ids[i] = i + 1;
        std::shuffle(ids.begin(), ids.end(), random);
        std::vector<Player> pending;
        for (int i = 0; i < 20; ++i) {
            Player p{ids[i], static_cast<Role>(random() % 5), static_cast<int>(random() % 5), i / 4};
            pending.push_back(p);
            q.join(p);
        }
        for (Time now : {Time{4}, Time{10}, Time{30}}) {
            auto teams = q.match(now);
            verifyBatch(teams, pending, now, policy);
            verifiedTeams += static_cast<int>(teams.size());
            assert(q.size() == pending.size());
        }
    }
    std::cout << "All tests passed; " << verifiedTeams
              << " teams (including exact tie choices) verified against exhaustive search "
              << "across 1000 random queues.\n";
}
