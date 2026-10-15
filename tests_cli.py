"""Exercise the real command-line program and verify invalid input has no effect."""
import subprocess

commands = """join 1 top 1500 0 extra
status
join 1 top 1500 0
match 0junk
cancel 1 extra
status
status extra
quit extra
status
cancel 1
status
quit
"""
result = subprocess.run(["./build/main"], input=commands, text=True,
                        capture_output=True, check=True)
assert result.stdout.count("Error: Unexpected extra input") == 5, result.stdout
assert result.stdout.count("0 waiting\n") == 2, result.stdout
assert result.stdout.count("1 waiting\n") == 2, result.stdout
assert result.stdout.count("Queued 1\n") == 1, result.stdout
assert "Cancelled\n" in result.stdout, result.stdout
print("CLI regression passed: 5 malformed commands rejected without side effects.")
