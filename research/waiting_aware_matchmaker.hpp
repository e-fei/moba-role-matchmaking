#pragma once

#include "../matchmaker.hpp"

// Experimental extension. The baseline in matchmaker.hpp is unchanged.
// For a candidate team T, minimize J(T) = G(T) - lambda * R(T), where
// G is mean pairwise score gap and R is mean wait capped per player.
// Thus 100 J(T) = 10 * pairwise gap sum - 20 lambda * capped wait sum.
// Anchor eligibility, age tie-breaks, band expansion, and 32 DP states are
// identical to the baseline; only the additive transition cost changes.
class WaitingAwareMatchmaker {
public:
    using Policy = Matchmaker::Policy;

    // lambda is represented exactly as lambdaTwentyUnits / 20 score points per second.
    // Integer arithmetic makes lambda=0 and all sweep ties exactly reproducible.
    // Multiplying costs by 100 changes no optimum or tie-break.
    explicit WaitingAwareMatchmaker(Policy policy = Policy{}, int lambdaTwentyUnits = 0,
                                    Time waitCap = 120)
        : policy_(policy), lambdaTwentyUnits_(lambdaTwentyUnits), waitCap_(waitCap) {
        // Reuse the baseline's public policy validation without altering it.
        Matchmaker validation(policy);
        if (lambdaTwentyUnits < 0 || lambdaTwentyUnits > 1000000 || waitCap < 0 || waitCap > 1000000) {
            throw std::invalid_argument("Invalid waiting reward or cap");
        }
    }

    void join(Player player) {
        if (player.id <= 0 || static_cast<int>(player.role) < 0 ||
            static_cast<int>(player.role) >= 5 || player.score < 0 || player.score > 1000000) {
            throw std::invalid_argument("Require positive ID, valid role, and score in [0, 1000000]");
        }
        if (player.requestedAt < currentTime_) throw std::invalid_argument("Time cannot go backward");
        for (const auto& p : waiting_) {
            if (p.id == player.id) throw std::invalid_argument("Player already queued");
        }
        currentTime_ = player.requestedAt;
        waiting_.push_back(player);
    }

    bool cancel(int id) {
        auto it = std::find_if(waiting_.begin(), waiting_.end(),
                               [id](const Player& p) { return p.id == id; });
        if (it == waiting_.end()) return false;
        waiting_.erase(it);
        return true;
    }

    std::size_t size() const { return waiting_.size(); }

    std::vector<Team> match(Time now) {
        if (now < currentTime_) throw std::invalid_argument("Time cannot go backward");
        currentTime_ = now;
        std::vector<Team> teams;
        while (auto team = matchOne(now)) {
            teams.push_back(*team);
            waiting_.erase(std::remove_if(waiting_.begin(), waiting_.end(), [&](const Player& p) {
                for (const auto& chosen : team->players) {
                    if (p.id == chosen.id) return true;
                }
                return false;
            }), waiting_.end());
        }
        return teams;
    }

private:
    struct Selection {
        std::int64_t cost = 0;
        std::array<Player, 5> players{};
        std::array<std::pair<Time, int>, 5> ageKey{};
        int count = 0;

        void append(const Player& p) {
            players[count] = p;
            const auto entry = std::make_pair(p.requestedAt, p.id);
            int position = count;
            while (position > 0 && entry < ageKey[position - 1]) {
                ageKey[position] = ageKey[position - 1];
                --position;
            }
            ageKey[position] = entry;
            ++count;
        }
    };

    // Equal-quality teams prefer earlier request times, then smaller IDs.
    static bool better(const Selection& a, const Selection& b) {
        if (a.cost != b.cost) return a.cost < b.cost;
        // Compared states always have equal counts; unused entries are zero.
        return a.ageKey < b.ageKey;
    }

    std::optional<Team> matchOne(Time now) const {
        if (waiting_.size() < 5) return std::nullopt;
        int availableRoles = 0;
        for (const auto& p : waiting_) availableRoles |= 1 << static_cast<int>(p.role);
        if (availableRoles != 31) return std::nullopt;
        auto sorted = waiting_;
        std::sort(sorted.begin(), sorted.end(), [](const Player& a, const Player& b) {
            return a.score != b.score ? a.score < b.score : a.id < b.id;
        });
        // Prefix counts answer whether an interval contains all five roles.
        std::vector<std::array<std::size_t, 5>> counts(sorted.size() + 1);
        for (std::size_t i = 0; i < sorted.size(); ++i) {
            counts[i + 1] = counts[i];
            ++counts[i + 1][static_cast<int>(sorted[i].role)];
        }
        // waiting_ preserves arrival order, including ties in request time.
        for (const auto& anchor : waiting_) {
            const int band = static_cast<int>(std::min<double>(policy_.maximumBand,
                policy_.initialBand + policy_.growthPerSecond * (now - anchor.requestedAt)));
            auto left = std::lower_bound(sorted.begin(), sorted.end(), anchor.score - band,
                [](const Player& p, int score) { return p.score < score; });
            auto right = std::upper_bound(sorted.begin(), sorted.end(), anchor.score + band,
                [](int score, const Player& p) { return score < p.score; });
            bool complete = true;
            for (int role = 0; role < 5; ++role) {
                if (counts[right - sorted.begin()][role] == counts[left - sorted.begin()][role]) {
                    complete = false;
                }
            }
            if (!complete) continue;

            std::array<std::optional<Selection>, 32> dp;
            dp[0] = Selection{};
            for (auto it = left; it != right; ++it) {
                const auto& p = *it;
                if (p.role == anchor.role && p.id != anchor.id) continue;
                const int bit = 1 << static_cast<int>(p.role);
                for (int mask = 31; mask >= 0; --mask) {
                    if (!dp[mask] || (mask & bit)) continue;
                    Selection next = *dp[mask];
                    const int k = next.count;
                    // In a sorted five-player team, score k has coefficient 2k - 4.
                    next.cost += static_cast<std::int64_t>(10 * (2 * k - 4)) * p.score
                               - static_cast<std::int64_t>(lambdaTwentyUnits_) *
                                 std::min<Time>(now - p.requestedAt, waitCap_);
                    next.append(p);
                    auto& target = dp[mask | bit];
                    if (!target || better(next, *target)) target = std::move(next);
                }
            }
            Team team{{}, now};
            for (const auto& p : dp[31]->players) team.players[static_cast<int>(p.role)] = p;
            return team;
        }
        return std::nullopt;
    }

    Policy policy_;
    int lambdaTwentyUnits_;
    Time waitCap_;
    Time currentTime_ = 0;
    std::vector<Player> waiting_;
};
