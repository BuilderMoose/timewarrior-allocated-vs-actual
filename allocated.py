#!/usr/bin/env python3
import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# --- CONFIGURATION & CONSTANTS ---
COLOR_HEADER = "\033[1;34m"
COLOR_SUCCESS = "\033[32m"
COLOR_WARN = "\033[33m"
COLOR_DANGER = "\033[31m"
COLOR_RESET = "\033[0m"

DEFAULT_TEMPLATE = """[[projects]]
name = "Work"
tags = ["Development", "Design"]
allocation_type = "percentage"
value = 1.00
"""

# --- UTILITIES ---

def format_hours(hours):
    h, m = int(abs(hours)), int((abs(hours) - int(abs(hours))) * 60)
    sign = "-" if hours < 0 else ""
    return f"{sign}{h}:{m:02d}"

def get_config_val(lines, key):
    for line in lines:
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return None

def calculate_monthly_capacity(start_dt, end_dt, exclusions, holidays, hpd):
    """Calculates total possible work hours for the date range."""
    total_hours = 0.0
    curr = start_dt.date()
    while curr < end_dt.date():
        day_name = curr.strftime('%A').lower()
        date_str = curr.strftime('%Y-%m-%d')
        
        if date_str in holidays:
            # 9-80 logic: If holiday is Friday, 0. If M-Th, subtract 8 (leaving 1 for 9hr day)
            day_goal = 0.0 if day_name == 'friday' else max(0.0, hpd - 8.0)
        elif day_name in ['saturday', 'sunday']:
            day_goal = 0.0
        else:
            day_goal = exclusions.get(day_name, hpd)
            
        total_hours += day_goal
        curr += timedelta(days=1)
    return total_hours

# --- FILE MANAGEMENT ---

def get_allocation_file(folder_path, target_date):
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: allocated.folder '{folder}' does not exist.")
        sys.exit(1)
        
    filename = target_date.strftime("%Y-%m-Allocation.data")
    file_path = folder / filename
    
    if not file_path.exists():
        # Try to find previous month
        prev_date = (target_date.replace(day=1) - timedelta(days=1))
        prev_file = folder / prev_date.strftime("%Y-%m-Allocation.data")
        
        if prev_file.exists():
            with open(file_path, "w") as f:
                f.write(prev_file.read_text())
        else:
            with open(file_path, "w") as f:
                f.write(DEFAULT_TEMPLATE)
    
    return file_path

# --- MAIN LOGIC ---

def main():
    # 1. Parse CLI Args (for CRUD operations)
    parser = argparse.ArgumentParser(description="Timewarrior Allocation Extension")
    parser.add_argument("command", nargs="?", help="add | rm | set")
    args, unknown = parser.parse_known_args()

    # 2. Read Timewarrior Input
    input_data = sys.stdin.read().strip().split('\n')
    json_start = next((i for i, line in enumerate(input_data) if line.strip().startswith('[')), -1)
    if json_start == -1: return

    config_lines = input_data[:json_start]
    json_text = '\n'.join(input_data[json_start:])
    
    # 3. Extract Meta-Data & Handle Dates Safely
    alloc_folder = get_config_val(config_lines, "allocated.folder")
    if not alloc_folder:
        print("Error: 'allocated.folder' not defined in timewarrior.cfg")
        sys.exit(1)

    report_start_str = get_config_val(config_lines, "temp.report.start")
    report_end_str = get_config_val(config_lines, "temp.report.end")
    
    local_offset = datetime.now().astimezone().utcoffset()

    if report_start_str:
        # Convert Timewarrior's UTC boundary to local time
        utc_start = datetime.strptime(report_start_str, '%Y%m%dT%H%M%SZ')
        report_start = utc_start + local_offset
    else:
        # Fallback: Current month
        report_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if report_end_str:
        utc_end = datetime.strptime(report_end_str, '%Y%m%dT%H%M%SZ')
        report_end = utc_end + local_offset
    else:
        # Fallback: End of the current month
        next_month = (report_start.replace(day=28) + timedelta(days=4))
        report_end = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 4. Load or Generate Allocation File
    Path(alloc_folder).mkdir(parents=True, exist_ok=True)
    alloc_file = get_allocation_file(alloc_folder, report_start)
    
    with open(alloc_file, "rb") as f:
        alloc_data = tomllib.load(f)
    
    # 5. Handle Capacity Calculation
    hpd_str = get_config_val(config_lines, "totals.hours_per_day")
    hpd = float(hpd_str) if hpd_str else 8.0
    holidays = {line.split('.')[2].split(':')[0] for line in config_lines if "holidays." in line}
    
    exclusions = {}
    for day in ['monday','tuesday','wednesday','thursday','friday']:
        for line in config_lines:
            if f"exclusions.{day}" in line and ">" in line:
                exclusions[day] = 9.0 if day != 'friday' else 8.0

    monthly_capacity = calculate_monthly_capacity(report_start, report_end, exclusions, holidays, hpd)

    # 6. Process Intervals
    try:
        intervals = json.loads(json_text)
    except ValueError:
        intervals = []
        
    projects = alloc_data.get("projects", [])
    project_stats = {p['name']: {'goal': 0.0, 'actual': 0.0, 'tags': set(p['tags']), 'type': p['allocation_type'], 'val': p['value']} for p in projects}
    unallocated_time = 0.0

    daily_data = defaultdict(lambda: defaultdict(float))

    for entry in intervals:
        start = datetime.strptime(entry['start'], '%Y%m%dT%H%M%SZ')
        end = datetime.strptime(entry['end'], '%Y%m%dT%H%M%SZ') if 'end' in entry else datetime.utcnow()
        duration = (end - start).total_seconds() / 3600.0
        
        # Group by local date
        local_start = start + local_offset
        local_date = local_start.date()

        entry_tags = set(entry.get('tags', []))
        
        matched = False
        for p_name, p_info in project_stats.items():
            if entry_tags & p_info['tags']:
                p_info['actual'] += duration
                daily_data[local_date][p_name] += duration
                matched = True
                break
        
        if not matched:
            unallocated_time += duration
            daily_data[local_date]['Unallocated'] += duration

    # 7. Final Calculations & Output
    print(f"\n{COLOR_HEADER}Allocation Report: {report_start.strftime('%B %Y')}{COLOR_RESET}")
    print(f"Monthly Capacity: {format_hours(monthly_capacity)} hrs\n")
    
    # --- DAILY BREAKDOWN ---
    if daily_data:
        daily_header = f"{'Date':<16} {'Project':<20} {'Worked':<10} {'Day Total':<10}"
        print(daily_header)
        print("-" * len(daily_header))

        for d_obj in sorted(daily_data.keys()):
            date_str = d_obj.strftime('%b %a %d')
            day_total = sum(daily_data[d_obj].values())
            
            projects_worked = [(p, h) for p, h in daily_data[d_obj].items() if h > 0]
            projects_worked.sort(key=lambda x: (x[0] == 'Unallocated', x[0]))

            for i, (proj, hrs) in enumerate(projects_worked):
                d_label = date_str if i == 0 else ""
                t_label = format_hours(day_total) if i == len(projects_worked) - 1 else ""
                print(f"{d_label:<16} {proj:<20} {format_hours(hrs):<10} {t_label:<10}")
            
        print() 

    # --- MONTHLY SUMMARY ---
    summary_header = f"{'Project Summary':<20} {'Goal':<10} {'Actual':<10} {'Remaining':<10} {'Status'}"
    print(summary_header)
    print("-" * len(summary_header))

    total_actual = 0.0
    for name, data in project_stats.items():
        goal = data['val'] * monthly_capacity if data['type'] == 'percentage' else data['val']
        actual = data['actual']
        remaining = goal - actual
        total_actual += actual
        
        color = COLOR_SUCCESS if remaining >= 0 else COLOR_DANGER
        progress = min(10, int((actual / goal) * 10)) if goal > 0 else 0
        bar = f"[{'#' * progress}{'.' * (10 - progress)}]"
        
        print(f"{name:<20} "
              f"{format_hours(goal):<10} "
              f"{format_hours(actual):<10} "
              f"{color}{format_hours(remaining):<10}{COLOR_RESET} "
              f"{bar}")

    print("-" * len(summary_header))
    print(f"{'Unallocated':<20} {'-':<10} {format_hours(unallocated_time):<10}")
    print(f"{'TOTAL LOGGED':<20} {'-':<10} {format_hours(total_actual + unallocated_time):<10}")

if __name__ == "__main__":
    main()