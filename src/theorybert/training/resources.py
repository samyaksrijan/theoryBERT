"""Read-only system monitoring. Never deletes user files or kills other jobs."""

import json
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path


def snapshot(path="."):
    data = {"time": time.time(), "disk_free_gb": shutil.disk_usage(path).free / 2**30}
    if platform.system() == "Darwin":
        pressure = subprocess.run(["memory_pressure", "-Q"], capture_output=True, text=True)
        match = re.search(r"free percentage: (\d+)%", pressure.stdout)
        if match:
            data["memory_free_percent"] = int(match[1])
        swap = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True)
        match = re.search(r"used = ([\d.]+)M", swap.stdout)
        if match:
            data["swap_used_gb"] = float(match[1]) / 1024
    return data


class ResourceGuard:
    def __init__(self, output, min_disk_gb=3, max_swap_growth_gb=1.5):
        self.path = Path(output)
        self.path.mkdir(parents=True, exist_ok=True)
        self.min_disk_gb = min_disk_gb
        self.max_swap_growth_gb = max_swap_growth_gb
        self.initial = snapshot(self.path)
        self.check("start")

    def check(self, phase, reserve_gb=0):
        data = {**snapshot(self.path), "phase": phase}
        with (self.path / "resources.jsonl").open("a") as handle:
            handle.write(json.dumps(data) + "\n")
        reason = None
        if data["disk_free_gb"] < self.min_disk_gb + reserve_gb:
            reason = f"Free disk space is below {self.min_disk_gb} GiB plus the {reserve_gb} GiB write reserve."
        if data.get("memory_free_percent", 100) < 8:
            reason = "System memory availability fell below 8%."
        if data.get("swap_used_gb", 0) - self.initial.get("swap_used_gb", 0) > self.max_swap_growth_gb:
            reason = "System swap grew beyond the training allowance."
        if reason:
            raise RuntimeError("Resource guard stopped training: " + reason)
        return data
