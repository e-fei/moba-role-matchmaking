CXX := clang++
CXXFLAGS := -std=c++17 -Wall -Wextra -Wpedantic -g
TARGET := build/main
SOURCE := main.cpp

.PHONY: all run test experiment waiting-experiment benchmark benchmark-compare sanitize clean

all: $(TARGET)

$(TARGET): $(SOURCE) matchmaker.hpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) $(SOURCE) -o $(TARGET)

run: $(TARGET)
	./$(TARGET)

test: build/tests $(TARGET)
	./build/tests
	python3 tests_cli.py

build/tests: tests.cpp matchmaker.hpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) tests.cpp -o build/tests

experiment: build/experiments
	./build/experiments > experiment_results.json

build/experiments: experiments.cpp matchmaker.hpp
	@mkdir -p build
	$(CXX) -std=c++17 -O2 -Wall -Wextra -Wpedantic experiments.cpp -o build/experiments

waiting-experiment: build/waiting_extension
	@mkdir -p results
	./build/waiting_extension results/waiting_extension.json

build/waiting_extension: research/waiting_extension.cpp research/waiting_aware_matchmaker.hpp experiments.cpp matchmaker.hpp
	@mkdir -p build
	$(CXX) -std=c++17 -O2 -Wall -Wextra -Wpedantic research/waiting_extension.cpp -o build/waiting_extension

benchmark: build/benchmarks
	./build/benchmarks

build/benchmarks: benchmarks.cpp matchmaker.hpp
	@mkdir -p build
	$(CXX) -std=c++17 -O2 -Wall -Wextra -Wpedantic benchmarks.cpp -o build/benchmarks

benchmark-compare: build/benchmarks build/benchmarks_before
	@mkdir -p results
	./build/benchmarks_before > results/benchmark_before.json
	./build/benchmarks > results/benchmark_after.json

build/benchmarks_before: benchmarks.cpp reference/matchmaker_before.hpp
	@mkdir -p build
	$(CXX) -std=c++17 -O2 -Wall -Wextra -Wpedantic '-DMATCHMAKER_HEADER="reference/matchmaker_before.hpp"' benchmarks.cpp -o build/benchmarks_before

sanitize:
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -fsanitize=address,undefined -fno-omit-frame-pointer tests.cpp -o build/tests_sanitized
	./build/tests_sanitized

clean:
	rm -f $(TARGET) build/tests build/tests_sanitized build/experiments build/benchmarks build/benchmarks_before build/waiting_extension
