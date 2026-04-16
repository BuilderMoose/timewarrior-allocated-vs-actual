#!/usr/bin/env python3
import json
import sys
import argparse
import re
from datetime import datetime, timedelta, timezone
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

def calculate_monthly_capacity(start_dt, end_dt, exclusions, holidays):
    """Calculates total possible work hours based strictly on Timewarrior exclusions."""
    total_hours = 0.0
    curr = start_dt.date()
    while curr < end_dt.date():
        day_name = curr.strftime('%A').lower()
        date_str = curr.strftime('%Y-%m-%d')
        
        if date_str in holidays:
            day_goal = 0.0
        else:
            # Default to 0 if the day isn't defined in the exclusions
            day_goal = exclusions.get(day_name, 0.0) 
            
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

    ignored_tags_raw = get_config_val(config_lines, "projected.ignore_tags")
    ignored_tags = set(ignored_tags_raw.split()) if ignored_tags_raw else set()

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
    holidays = {line.split('.')[2].split(':')[0] for line in config_lines if "holidays." in line}
    
    exclusions = {}
    # Matches standard window: exclusions.monday: <19:00 >21:00
    pattern_window = re.compile(r'exclusions\.(\w+):\s*<\s*(\d+:\d+)\s*>\s*(\d+:\d+)')
    # Matches full day exclusion: exclusions.sunday: >0:00
    pattern_zero = re.compile(r'exclusions\.(\w+):\s*>\s*0:00')
    
    for line in config_lines:
        match_window = pattern_window.match(line)
        if match_window:
            day = match_window.group(1).lower()
            start_parts = match_window.group(2).split(':')
            end_parts = match_window.group(3).split(':')
            start_m = int(start_parts[0]) * 60 + int(start_parts[1])
            end_m = int(end_parts[0]) * 60 + int(end_parts[1])
            exclusions[day] = (end_m - start_m) / 60.0
        else:
            match_zero = pattern_zero.match(line)
            if match_zero:
                day = match_zero.group(1).lower()
                exclusions[day] = 0.0

    monthly_capacity = calculate_monthly_capacity(report_start, report_end, exclusions, holidays)

    # 6. Process Intervals
    try:
        intervals = json.loads(json_text)
    except ValueError:
        intervals = []
        
    projects = alloc_data.get("projects", [])
    project_stats = {p['name']: {'goal': 0.0, 'actual': 0.0, 'tags': set(p['tags']), 'type': p['allocation_type'], 'val': p['value']} for p in projects}
    unallocated_time = 0.0

    daily_data = defaultdict(lambda: defaultdict(float))
    excluded_summary = defaultdict(float)

    for entry in intervals:
        start = datetime.strptime(entry['start'], '%Y%m%dT%H%M%SZ')
        end = datetime.strptime(entry['end'], '%Y%m%dT%H%M%SZ') if 'end' in entry else datetime.now(timezone.utc).replace(tzinfo=None)
        duration = (end - start).total_seconds() / 3600.0
        
        # Group by local date
        local_start = start + local_offset
        local_date = local_start.date()

        entry_tags = set(entry.get('tags', []))
        
        intersecting = entry_tags & ignored_tags
        if intersecting:
            for tag in intersecting:
                excluded_summary[tag] += duration
            continue

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
    if ignored_tags:
        colored_tags = [f"{COLOR_HEADER}{tag}{COLOR_RESET}" for tag in sorted(ignored_tags)]
        print(f"Excluded tags: {', '.join(colored_tags)}")

    print(f"\n{COLOR_HEADER}Allocation Report: {report_start.strftime('%B %Y')}{COLOR_RESET}")
    print(f"Monthly Capacity: {format_hours(monthly_capacity)} hrs\n")
    
    # --- DAILY BREAKDOWN ---
    if daily_data:
        daily_header = f"{'Date':<16} {'Project':<20} {'Worked':<10} {'% of Day':<10} {'Day Total':<10}"
        print(daily_header)
        print("-" * len(daily_header))

        alt_day = False 
        COLOR_DAY_ALT = "\033[36m" # Cyan color for alternating days

        for d_obj in sorted(daily_data.keys()):
            date_str = d_obj.strftime('%b %a %d')
            day_total = sum(daily_data[d_obj].values())
            
            projects_worked = [(p, h) for p, h in daily_data[d_obj].items() if h > 0]
            projects_worked.sort(key=lambda x: (x[0] == 'Unallocated', x[0]))

            # Determine the color for the entire day's block
            row_color = COLOR_DAY_ALT if alt_day else ""

            for i, (proj, hrs) in enumerate(projects_worked):
                d_label = date_str if i == 0 else ""
                t_label = format_hours(day_total) if i == len(projects_worked) - 1 else ""
                
                pct = (hrs / day_total * 100) if day_total > 0 else 0.0
                pct_str = f"{pct:.1f}%"
                
                # Apply the row color and reset it at the end of the line
                print(f"{row_color}{d_label:<16} {proj:<20} {format_hours(hrs):<10} {pct_str:<10} {t_label:<10}{COLOR_RESET}")
            
            # Flip the toggle for the next day
            alt_day = not alt_day
            
        print()

    # --- MONTHLY SUMMARY ---
    # Pre-calculate total logged time so we can figure out the percentages
    total_logged = sum(p['actual'] for p in project_stats.values()) + unallocated_time

    # Added '% Capacity' and renamed '% of Mth' to '% Logged' for clarity
    summary_header = f"{'Project Summary':<20} {'Goal':<10} {'Actual':<10} {'% Logged':<10} {'% Capacity':<12} {'Remaining':<10} {'Status'}"
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

        # Calculate percentage of total time logged so far
        pct_logged = (actual / total_logged * 100) if total_logged > 0 else 0.0
        pct_logged_str = f"{pct_logged:.1f}%"

        # Calculate percentage of the total monthly schedule capacity
        pct_cap = (actual / monthly_capacity * 100) if monthly_capacity > 0 else 0.0
        pct_cap_str = f"{pct_cap:.1f}%"

        print(f"{name:<20} "
              f"{format_hours(goal):<10} "
              f"{format_hours(actual):<10} "
              f"{pct_logged_str:<10} "
              f"{pct_cap_str:<12} "
              f"{color}{format_hours(remaining):<10}{COLOR_RESET} "
              f"{bar}")

    print("-" * len(summary_header))

    # Align the footer rows with both new columns
    unalloc_pct_logged = (unallocated_time / total_logged * 100) if total_logged > 0 else 0.0
    unalloc_pct_cap = (unallocated_time / monthly_capacity * 100) if monthly_capacity > 0 else 0.0
    print(f"{'Unallocated':<20} {'-':<10} {format_hours(unallocated_time):<10} {f'{unalloc_pct_logged:.1f}%':<10} {f'{unalloc_pct_cap:.1f}%':<12}")

    total_cap_pct = (total_logged / monthly_capacity * 100) if monthly_capacity > 0 else 0.0
    print(f"{'TOTAL LOGGED':<20} {'-':<10} {format_hours(total_logged):<10} {'100.0%':<10} {f'{total_cap_pct:.1f}%':<12}")

    if excluded_summary:
        print("\nExcluded Time Summary:")
        print("-" * 30)
        for tag in sorted(excluded_summary.keys()):
            # Using COLOR_HEADER to mimic the colored output from your other script
            col_tag = f"{COLOR_HEADER}{tag}{COLOR_RESET}"
            print(f"{col_tag:<27} {format_hours(excluded_summary[tag])}")

if __name__ == "__main__":
    main()