#!/usr/bin/env python3

import json
import csv
import sys
import re
import statistics

with open(sys.argv[1], "r") as f:
    json_data = json.loads(f.read())

cpus_data = json_data["cpus"]
DTS_HEADER = """/*
 * Auto-generated simplified EAS energy model for incorporation in SoC device tree.
 * Generated by freqbench postprocessing scripts using freqbench results.
 * More info at https://github.com/kdrag0n/freqbench
 */

/ {
\tcpus {"""

print(DTS_HEADER)

mode = "power"
voltages = {}
for arg in sys.argv[2:]:
    cluster, freq, voltage = map(int, re.split(r"\.|=", arg))
    voltages[(cluster, freq)] = voltage

# Performance efficiency
unscaled_cpu_cm_mhz = {}
for cpu, cpu_data in cpus_data.items():
    last_freq, last_freq_data = max(cpu_data["freqs"].items(), key=lambda f: f[0])
    cm_mhz = last_freq_data["active"]["coremarks_per_mhz"]
    unscaled_cpu_cm_mhz[int(cpu)] = cm_mhz

# Scale performance efficiency
max_cm_mhz = max(unscaled_cpu_cm_mhz.values())
scaled_cpu_cm_mhz = {
    cpu: cm_mhz / max_cm_mhz * 1024
    for cpu, cm_mhz in unscaled_cpu_cm_mhz.items()
}

for cpu, cpu_data in cpus_data.items():
    cpu = int(cpu)

    dpcs = []
    for freq, freq_data in cpu_data["freqs"].items():
        freq = int(freq)

        if (cpu, freq) not in voltages:
            continue

        if mode == "power":
            # µW
            cost = freq_data["active"]["power_mean"] * 1000
        elif mode == "energy":
            cost = freq_data["active"]["energy_millijoules"] * 10

        mhz = freq / 1000
        v = voltages[(cpu, freq)] / 1_000_000

        dpc = cost / mhz / v**2
        dpcs.append(dpc)

    cm_mhz_norm = scaled_cpu_cm_mhz[cpu]
    if dpcs:
        dpc = statistics.mean(dpcs)
    else:
        dpc = 0

    lb = "{"
    rb = "}"
    print(f"""\t\tcpu@{0 if cpu == 1 else cpu} {lb}
\t\t\tefficiency = <{cm_mhz_norm:.0f}>;
\t\t\tcapacity-dmips-mhz = <{cm_mhz_norm:.0f}>;
\t\t\tdynamic-power-coefficient = <{dpc:.0f}>;
\t\t{rb};
""")

print("""\t};
};""")
