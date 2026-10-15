#include "matchmaker.hpp"

#include <iostream>
#include <sstream>
#include <string>

void requireEnd(std::istringstream& input) {
    std::string extra;
    if (input >> extra) throw std::invalid_argument("Unexpected extra input");
}

int main() {
    Matchmaker queue;
    std::cout << "Commands (time in seconds, nondecreasing):\n"
              << "  join ID ROLE SCORE TIME   (roles: top jun mid adc sup)\n"
              << "  match TIME\n  cancel ID\n  status\n  quit\n";
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream input(line);
        std::string command;
        input >> command;
        if (command.empty()) continue;
        try {
            if (command == "quit") {
                requireEnd(input);
                break;
            }
            if (command == "join") {
                int id, score;
                Time time;
                std::string role;
                if (!(input >> id >> role >> score >> time)) {
                    throw std::invalid_argument("Use: join ID ROLE SCORE TIME");
                }
                requireEnd(input);
                queue.join({id, parseRole(role), score, time});
                std::cout << "Queued " << id << '\n';
            } else if (command == "match") {
                Time time;
                if (!(input >> time)) throw std::invalid_argument("Use: match TIME");
                requireEnd(input);
                auto teams = queue.match(time);
                for (const auto& team : teams) {
                    std::cout << "Team:";
                    for (const auto& p : team.players) {
                        std::cout << ' ' << roleName(p.role) << '=' << p.id << '(' << p.score << ')';
                    }
                    std::cout << " | average wait=" << team.averageWait()
                              << "s, average pairwise gap=" << team.averageGap() << '\n';
                }
                std::cout << teams.size() << " team(s), " << queue.size() << " waiting\n";
            } else if (command == "cancel") {
                int id;
                if (!(input >> id)) throw std::invalid_argument("Use: cancel ID");
                requireEnd(input);
                std::cout << (queue.cancel(id) ? "Cancelled\n" : "Player not queued\n");
            } else if (command == "status") {
                requireEnd(input);
                std::cout << queue.size() << " waiting\n";
            } else {
                throw std::invalid_argument("Unknown command");
            }
        } catch (const std::exception& error) {
            std::cout << "Error: " << error.what() << '\n';
        }
    }
}
