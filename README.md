# Timewarrior Project Allocation (`allocated`)

A Python-based extension for [Timewarrior](https://timewarrior.net/) that tracks actual time spent against defined monthly project allocations. It automatically calculates your monthly capacity based on your specific schedule, monitors progress via fixed hours or percentages, and ensures no time falls through the cracks.

---

## Features

* **Project-Based Tracking:** Define "Projects" using sets of tags, and assign them a monthly budget (either a fixed number of hours or a percentage of your total monthly capacity).
* **Dynamic Capacity Calculation:** Calculates your total available working hours for the month dynamically using purely Timewarrior's native `exclusions` windows. No hardcoded 8-hour days necessary.
* **Daily Breakdown with Alternating Colors:** A detailed chronological view of what projects you worked on each day, including what percentage of your daily effort went to each project. Rows alternate colors by day for high readability.
* **Advanced Monthly Dashboard:** A scannable summary showing Project Goals, Actuals, Remaining Hours, and visual progress bars (`[######....]`).
* **Dual Percentage Tracking:** Instantly see two metrics for every project:
    * `% Logged`: How your effort was distributed across the hours you actually tracked.
    * `% Capacity`: How much of your total available monthly schedule has been burned on that project.
* **Unallocated Time Safety Net:** Automatically catches and totals any tracked time that doesn't match a defined project, preventing data drift.
* **Shared Tag Filtering:** Respects the `projected.ignore_tags` configuration. Tags like `Lunch` or `SideQuest` are stripped out before calculating daily totals or project actuals, listed at the top of the report, with an optional summary of "lost" time at the bottom.
* **Automated Roll-over:** Automatically generates a new `YYYY-MM-Allocation.data` TOML file for the current month. If a previous month exists, it copies your project definitions forward.

---

## Example Output

```text
Excluded tags: Lunch, SideQuest

Allocation Report: April 2026
Monthly Capacity: 160:00 hrs

Date             Project              Worked     % of Day   Day Total 
----------------------------------------------------------------------
Apr Wed 01       Client Alpha         4:30       50.0%      
Apr Wed 01       Internal R&D         2:00       22.2%      
Apr Wed 01       Unallocated          2:30       27.8%      9:00      
Apr Thu 02       Client Alpha         8:00       100.0%     8:00      
Apr Fri 03       Internal R&D         4:00       100.0%     4:00      

Project Summary      Goal       Actual     % Logged   % Capacity   Remaining  Status
--------------------------------------------------------------------------------------
Client Alpha         40:00      12:30      59.5%      7.8%         27:30      [###.......]
Internal R&D         20:00      6:00       28.6%      3.8%         14:00      [###.......]
Admin & Meetings     16:00      0:00       0.0%       0.0%         16:00      [..........]
--------------------------------------------------------------------------------------
Unallocated          -          2:30       11.9%      1.6%        
TOTAL LOGGED         -          21:00      100.0%     13.1%       

Excluded Time Summary:
------------------------------
Lunch                2:30
SideQuest            1:15
```

---

## Installation & Setup

### 1. Requirements
This script uses `tomllib` to read project configurations.
* **Python 3.11+**: Built-in, no action required.
* **Python 3.10 or older**: Install the backport via pip: `pip install tomli`

### 2. Link the Extension

Create a symbolic link in the Timewarrior extensions directory without the `.py` extension:

```bash
# Link the script
ln -s /path/to/your/repo/allocated.py ~/.timewarrior/extensions/allocated
# Make it executable
chmod +x ~/.timewarrior/extensions/allocated
```

### 3. Timewarrior Configuration

Add this to your `~/.timewarrior/timewarrior.cfg`.

```ini
# --- Required: Allocations Directory ---
# Where the script will store and read your monthly TOML files
allocated.folder = /home/username/.timewarrior/allocations

# --- Schedule (Calculates Monthly Capacity) ---
# The script uses the duration between these exclusions to calculate your total monthly hours.
# E.g., <19:00 >21:00 means EXACTLY 2 hours are expected that day.
# >0:00 means the entire day is excluded (0 hours).
exclusions.monday:    <19:00 >21:00
exclusions.tuesday:   <19:00 >21:00
exclusions.wednesday: <19:00 >21:00
exclusions.thursday:  <19:00 >21:00
exclusions.friday:    <19:00 >21:00
exclusions.saturday:  <12:00 >16:00
exclusions.sunday:    >0:00

# --- Tag Filtering (Shared with Projected script) ---
projected.ignore_tags = Lunch SideQuest Personal

# --- Holiday Calendar ---
# Holidays automatically drop that day's expected capacity to 0.0 hours
holidays.US.2026-01-01: New Year's Day
```

### 4. Defining Your Projects (TOML)

When you run the script for a new month, it will automatically generate a file (e.g., `2026-04-Allocation.data`) in your `allocated.folder`. You can edit this file to define your projects:

```toml
# Use 'percentage' (e.g., 0.25 for 25% of the month's total capacity) 
# or 'fixed' (e.g., 20.0 for 20 hours)

[[projects]]
name = "Client Alpha"
tags = ["alpha", "development"]
allocation_type = "percentage"
value = 0.25

[[projects]]
name = "Internal R&D"
tags = ["research", "prototyping"]
allocation_type = "fixed"
value = 20.0
```

---

## Recommended Aliases

Add these to your `~/.bashrc` or `~/.zshrc` for quick access:

```bash
alias twa='timew allocated :month'
alias twla='timew allocated :lastmonth'
```

---

## Troubleshooting

* **Error: 'allocated.folder' not defined:** You must add the `allocated.folder = /path/to/dir` line to your `timewarrior.cfg`.
* **Zero Monthly Capacity:** Ensure your `exclusions` in the config file strictly follow the `<HH:MM >HH:MM` format. The script calculates your capacity based on the time *between* the excluded blocks. If a day has no exclusions defined, it defaults to 0 expected hours.
* **Extension not found:** Ensure the symlink in `~/.timewarrior/extensions/` is executable and does **not** have the `.py` suffix.
* **Timezone Mismatch:** The script uses your system's local timezone to process UTC Timewarrior data. Verify your system clock is correct.

---

## Development & Debugging

### The "Tee" Hack

To see the raw data Timewarrior pipes into extensions, create a symlink to the `tee` command:

```bash
ln -s /usr/bin/tee ~/.timewarrior/extensions/Tee
```

Running `timew Tee :month` will dump the exact JSON and configuration headers to your terminal.

### Manual Testing

Capture a debug file to test logic changes without triggering Timewarrior:

```bash
timew Tee :month > debug.json
cat debug.json | python3 allocated.py
```