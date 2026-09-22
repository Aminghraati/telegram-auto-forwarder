"""STEP 5 TEST: live-run the real script, watch output until first round completes, then stop it"""
import subprocess
import sys
import time
import os

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dict(os.environ)
env["PYTHONUNBUFFERED"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

proc = subprocess.Popen(
    [sys.executable, "-u", "send_to_folder.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    env=env,
    text=True,
    encoding="utf-8",
    errors="replace",
)

start = time.time()
lines = []
round1_done = False
first_round_forwards = 0

def read_line_nonblocking():
    import select
    # windows: use thread-based peek via readline with timeout trick
    # simplest: rely on -u unbuffered + blocking readline in thread
    return None

import threading
from queue import Queue, Empty

q = Queue()

def reader(pipe, queue):
    for line in iter(pipe.readline, ""):
        queue.put(line)
    queue.put(None)

t = threading.Thread(target=reader, args=(proc.stdout, q), daemon=True)
t.start()

while time.time() - start < 300:
    try:
        line = q.get(timeout=1.0)
    except Empty:
        continue
    if line is None:
        break
    line = line.rstrip()
    lines.append(line)
    # print only meaningful lines live
    if "INFO" not in line and "WARNING" not in line and line:
        print(f"  {line}")
    if "دور 1 تمام شد" in line or "دور ۱ تمام شد" in line:
        round1_done = True
        break

# stop the script (simulate Ctrl+C)
proc.terminate()
try:
    proc.wait(timeout=10)
except Exception:
    proc.kill()

# analyze
# حالت موازی: هر خط «↳ این پیام به X/Y گروه رسید» = یک broadcast موفق کامل
import re
broadcast_ok = 0
for l in lines:
    m = re.search(r"این پیام به (\d+)/(\d+) گروه رسید", l)
    if m and m.group(1) == m.group(2):
        broadcast_ok += 1
fwd_ok = broadcast_ok
errors = [l for l in lines if "❌" in l]
print("\n" + "=" * 50)
print(f"lines captured: {len(lines)}")
print(f"successful forwards: {fwd_ok}")
print(f"error lines: {len(errors)}")
for e in errors:
    print(f"  ERROR: {e}")
print(f"round1 completed banner: {round1_done}")

if errors or fwd_ok == 0:
    print("\nSTEP5: FAIL")
    sys.exit(1)
print(f"\n[OK] {fwd_ok} parallel broadcasts completed (all groups received every message)")
print("\nSTEP5: PASS")
