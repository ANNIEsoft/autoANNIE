"""
monitor_jobs.py - memory and disk monitor for autoANNIE grid jobs

- Runs in the background of `master_script.py` during event building and BeamCluster, and stops at the end. Turn it on or off with monitor_mem_disk, and set the check interval with monitor_interval (default 5 min).
- Every check: a table of your jobs that are HELD or at ≥ 90% of their memory or disk allocation.
- When a run finishes, before its files are copied to persistent, writes MemDisk_R<run>.summary into the run’s output folder.
  - One row per job and a MAX line, all as peak/allocated MB (%).
  - Resubmitted jobs are added as new rows, never overwritten.
- At the end, the max per run, plus memory and disk histograms, printed on screen.
- Standalone: `python3 lib/monitor_jobs.py` shows the per-run max for your jobs in the queue.

"""
import atexit
import os
import re
import subprocess
import threading
import time

WARN_PCT = 90
ATTRS = ["JobsubJobId", "JobStatus", "MemoryUsage", "RequestMemory", "DiskUsage", "RequestDisk",
         "Args", "Arguments", "Owner", "AcctGroupUser", "ResidentSetSize_RAW", "DiskUsage_RAW"]


def num(x):
    try:
        return float(x)
    except ValueError:      # 'undefined'
        return 0.0


def pct(used, alloc):
    return 100 * used / alloc if alloc > 0 else 0


def fmt(used, alloc):
    return f"{used:.0f}/{alloc:.0f} MB ({pct(used, alloc):.0f}%)"


def job_name(args, job_id):
    m = re.search(r"BC_(\d+) (\d+) (\d+)", args)
    if m:
        return f"BC_R{m[1]}_p{m[2]}-{m[3]}", m[1]
    m = re.search(r"(\d+)_(\d+)_(\d+)", args)
    if m:
        return f"EB_R{m[1]}_p{m[2]}-{m[3]}", m[1]
    return job_id.split("@")[0], "unknown"


def query(user):
    """Your jobs in the queue (memory and disk in MB), or None if jobsub_q fails."""
    try:
        out = subprocess.run(["jobsub_q", "-G", "annie", "--user", user, "-af:t"] + ATTRS,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             universal_newlines=True, timeout=600, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    jobs = []
    for line in out.splitlines():
        f = line.split("\t")
        if len(f) < len(ATTRS) or not f[1].isdigit() or user not in (f[8], f[9]):
            continue
        name, run = job_name(f[6] + " " + f[7], f[0])
        jobs.append({"id": f[0], "name": name, "run": run, "held": f[1] == "5",
                     "mem": num(f[10]) / 1024 or num(f[2]), "mem_alloc": num(f[3]),
                     "disk": (num(f[11]) or num(f[4])) / 1024, "disk_alloc": num(f[5]) / 1024})
    return jobs


def by_run(jobs):
    runs = {}
    for j in jobs:
        runs.setdefault(j["run"], []).append(j)
    return runs


def print_max(jobs):
    print(f"  {'run':<10} {'jobs':>5}   {'max memory peak/allocated':<26} max disk peak/allocated")
    for run, rows in sorted(by_run(jobs).items()):
        m = max(rows, key=lambda j: j["mem"])
        d = max(rows, key=lambda j: j["disk"])
        print(f"  {run:<10} {len(rows):>5}   {fmt(m['mem'], m['mem_alloc']):<26} {fmt(d['disk'], d['disk_alloc'])}")


def print_hist(jobs, key, step=1000):
    peaks = [j[key] for j in jobs if j[key] > 0]
    if not peaks:
        return
    print(f"\n  {key} peak (MB)    jobs")
    for b in range(int(max(peaks) // step) + 1):
        n = sum(b * step <= p < (b + 1) * step for p in peaks)
        print(f"  {b*step:>5}-{(b+1)*step:<6} {n:>5}  {'#' * min(n, 60)}")


class Monitor:

    def __init__(self, user, outdir, interval):
        self.user, self.outdir, self.interval = user, outdir, interval
        self.written = set()
        self.jobs = {}      # job id -> job, with peak mem/disk
        self.started = time.strftime("%Y-%m-%d %H:%M")
        self.done = threading.Event()

    def save_run(self, run):
        run = str(run)
        rows = [j for j in list(self.jobs.values()) if j["run"] == run]
        if rows and run not in self.written:
            self.write(run, rows)
            self.written.add(run)

    def check(self):
        stamp = time.strftime("%Y-%m-%d %H:%M")
        jobs = query(self.user)
        if jobs is None:
            print(f"[monitor] {stamp}  jobsub_q failed, trying again next check")
            return
        flagged = []
        for j in jobs:
            if j["held"] or pct(j["mem"], j["mem_alloc"]) >= WARN_PCT or pct(j["disk"], j["disk_alloc"]) >= WARN_PCT:
                flagged.append(j)
            old = self.jobs.get(j["id"], j)
            self.jobs[j["id"]] = dict(j, mem=max(old["mem"], j["mem"]), disk=max(old["disk"], j["disk"]))

        print(f"\n[monitor] {stamp}  jobs: {len(jobs)}  |  HELD or >= {WARN_PCT}%: {len(flagged)}")
        if flagged:
            print(f"  {'job name':<20} {'held':<5} {'memory used/allocated':<26} disk used/allocated")
        for j in flagged:
            print(f"  {j['name']:<20} {'yes' if j['held'] else 'no':<5} "
                  f"{fmt(j['mem'], j['mem_alloc']):<26} {fmt(j['disk'], j['disk_alloc'])}")

    def write(self, run, rows):
        lines = [f"# monitored {self.started} -> {time.strftime('%Y-%m-%d %H:%M')}",
                 f"{'job name':<20} {'job id':<14} {'memory peak/allocated':<26} disk peak/allocated"]
        for j in rows:
            lines.append(f"{j['name']:<20} {j['id'].split('@')[0]:<14} "
                         f"{fmt(j['mem'], j['mem_alloc']):<26} {fmt(j['disk'], j['disk_alloc'])}")
        m = max(rows, key=lambda j: j["mem"])
        d = max(rows, key=lambda j: j["disk"])
        lines.append(f"{'MAX':<20} {'':<14} {fmt(m['mem'], m['mem_alloc']):<26} {fmt(d['disk'], d['disk_alloc'])}")

        path = os.path.join(self.outdir, run, f"MemDisk_R{run}.summary")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            old = ""
            if os.path.exists(path):        # keep earlier sessions, add this one below
                with open(path) as f:
                    old = f.read() + "\n"
                os.remove(path)             # /pnfs files can't be edited in place
            with open(path, "w") as f:
                f.write(old + "\n".join(lines) + "\n")
        except OSError as err:
            print(f"[monitor] could not write {path}: {err}")

    def loop(self):
        while not self.done.is_set():
            try:
                self.check()
            except Exception as err:
                print(f"[monitor] check failed: {err!r}")
            self.done.wait(self.interval * 60)

    def stop(self):
        if self.done.is_set():      # already stopped
            return
        self.done.set()
        print("\n[monitor] writing MemDisk summaries ...")
        self.thread.join(timeout=10)
        jobs = list(self.jobs.values())
        for run, rows in by_run(jobs).items():
            if run not in self.written and run != "unknown":
                self.write(run, rows)
        print(f"\n[monitor] max peak per run  (files: {self.outdir}<run>/MemDisk_R<run>.summary)")
        print_max(jobs)
        print_hist(jobs, "mem")
        print_hist(jobs, "disk")


def start(user, outdir, interval=10):
    mon = Monitor(user, outdir, interval)
    atexit.register(mon.stop)       # also runs if the master script exits early or on Ctrl-C
    mon.thread = threading.Thread(target=mon.loop, daemon=True)
    mon.thread.start()
    return mon


if __name__ == "__main__":
    import sys
    user = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("USER", "")
    jobs = query(user)
    if jobs is None:
        sys.exit("jobsub_q failed (token expired?)")
    print_max(jobs)
