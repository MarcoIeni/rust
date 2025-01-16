"""
Retry a command if stderr contains a specific regex pattern.
"""

import sys
import subprocess
import re
import time
import select
import os

# Regex patterns to match in stderr
ERROR_PATTERNS = [
    r"a .* error occurred"  # Matches "a <something> error occurred"
]

def stream_output(pipe, is_stderr=False):
    """Stream output from pipe to appropriate destination"""
    for line in iter(pipe.readline, b''):
        print("analyzing line:", line)
        if is_stderr:
            sys.stderr.buffer.write(line)
            sys.stderr.buffer.flush()
        else:
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
    pipe.close()

def run_command(cmd_args):
    """Run command and stream output in real-time"""
    try:
        process = subprocess.Popen(
            cmd_args,
            stderr=subprocess.PIPE
        )

        stderr_lines = []
        while True:
            reads = [process.stderr.fileno()]
            ret = select.select(reads, [], [])

            for fd in ret[0]:
                if fd == process.stderr.fileno():
                    line = os.read(fd, 1024)
                    print("line:", line)
                    if line:
                        sys.stderr.buffer.write(line)
                        stderr_lines.append(line)
                        sys.stderr.buffer.flush()

            if process.poll() is not None:
                break

        return process.returncode, b''.join(stderr_lines).decode()

    except Exception as e:
        print(f"Failed to execute command: {e}")
        sys.exit(1)

def should_retry(stderr):
    """Check if stderr matches any retry patterns"""
    for line in stderr.splitlines():
        for pattern in ERROR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                print(f"Retrying because line `{line}` matched pattern `{pattern}`")
                return True
    return False


def get_command():
    if len(sys.argv) < 2:
        print("Usage: python command-retry.py <command>")
        sys.exit(1)

    return sys.argv[1:]

def main():
    cmd = get_command()
    max_retries = 3
    # Seconds to wait before retrying
    retry_delay = 10

    for attempt in range(max_retries):
        print(f"\nRunning command with retry. Attempt: {attempt+1}/{max_retries}")
        if attempt > 0:
            # We already tried once, wait before retrying
            time.sleep(retry_delay)

        returncode, stderr = run_command(cmd)
        print("returncode:", returncode)

        if returncode == 0:
            # Command was successful
            sys.exit(0)

        if not should_retry(stderr):
            break

    sys.exit(returncode)

if __name__ == "__main__":
    main()
