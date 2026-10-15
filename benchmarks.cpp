#ifndef MATCHMAKER_HEADER
#define MATCHMAKER_HEADER "matchmaker.hpp"
#endif
#include MATCHMAKER_HEADER

#include <chrono>
#include <iomanip>
#include <iostream>
#include <random>

int main() {
    constexpr int repetitions = 7;
    std::cout << std::fixed << std::setprecision(3) << "{\n";
    for (int scenario = 0; scenario < 3; ++scenario) {
        const char* names[] = {"equal_scores_500", "mixed_scores_500", "missing_role_5000_100_ticks"};
        std::vector<double> milliseconds;
        for (int run = 0; run < repetitions; ++run) {
            Matchmaker q({1000000, 0, 1000000});
            std::mt19937 rng(20260919);
            int n = scenario == 2 ? 5000 : 500;
            for (int i = 0; i < n; ++i) {
                q.join({i + 1, static_cast<Role>(i % (scenario == 2 ? 4 : 5)),
                        scenario == 1 ? static_cast<int>(rng() % 1001 + 1000) : 1500, 0});
            }
            const auto start = std::chrono::steady_clock::now();
            std::size_t teams = 0;
            for (int tick = 0; tick < (scenario == 2 ? 100 : 1); ++tick) teams += q.match(tick).size();
            const auto end = std::chrono::steady_clock::now();
            if (teams != (scenario == 2 ? 0u : 100u)) return 1;
            milliseconds.push_back(std::chrono::duration<double, std::milli>(end - start).count());
        }
        std::sort(milliseconds.begin(), milliseconds.end());
        std::cout << "  \"" << names[scenario] << "\": {\"median_ms\": "
                  << milliseconds[repetitions / 2] << ", \"min_ms\": " << milliseconds.front()
                  << ", \"max_ms\": " << milliseconds.back() << "}"
                  << (scenario == 2 ? "\n" : ",\n");
    }
    std::cout << "}\n";
}
