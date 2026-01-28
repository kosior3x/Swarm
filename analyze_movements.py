import pandas as pd
import re
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

# Load data
import sys
import os

file_path = 'train_sim_20260127_064742.csv'
if len(sys.argv) > 1:
    file_path = sys.argv[1]

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    print("Please place the CSV file in the current directory or provide path as argument.")
    exit(1)

# Manually define names to handle variable length
col_names = [
    'timestamp', 'source', 'dist_front', 'dist_left', 'dist_right',
    'speed_left', 'speed_right', 'action', 'confidence', 'decision_source',
    'cycle', 'val1', 'val2', 'val3', 'val4'
]

try:
    # Use header=None and skiprows=1 to ignore the actual header and force our column names
    df = pd.read_csv(file_path, names=col_names, header=None, skiprows=1, engine='python', on_bad_lines='skip')
except Exception as e:
    print(f"Error reading CSV: {e}")
    exit(1)

print(f"Loaded {len(df)} rows.")

# Extract X and Y
def get_coordinates(row):
    # Try getting from val3 (notes in first part)
    note = str(row['val3'])
    x = None
    y = None

    # Check for x:..;y:.. format
    x_match = re.search(r'x:(\d+)', note)
    y_match = re.search(r'y:(\d+)', note)
    if x_match and y_match:
        return float(x_match.group(1)), float(y_match.group(1))

    # Fallback: check val1 and val2 (steps/pos in second part)
    # val1 and val2 are typically numeric
    try:
        v1 = float(row['val1'])
        v2 = float(row['val2'])
        # If val1 and val2 are large numbers, they are likely coordinates (steps)
        # Or if one is non-zero.
        if v1 != 0 or v2 != 0:
            return v1, v2
    except:
        pass

    return None, None

coords = df.apply(get_coordinates, axis=1)
df['x'] = coords.apply(lambda x: x[0] if x else None)
df['y'] = coords.apply(lambda x: x[1] if x else None)

# Forward fill missing coordinates
df['x'] = df['x'].ffill()
df['y'] = df['y'].ffill()

# Convert numerical columns
num_cols = ['dist_front', 'dist_left', 'dist_right']
for col in num_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Drop rows with missing essential data
df.dropna(subset=['dist_front', 'action', 'x', 'y'], inplace=True)
print(f"Rows after cleaning: {len(df)}")

# Define scenarios

def find_avoidance_scenarios(df):
    events = []
    in_event = False
    start_idx = 0

    # Reset index to make iteration easier
    df = df.reset_index(drop=True)

    for i in range(1, len(df)):
        row = df.iloc[i]

        # Start condition: Front obstacle detected (< 200mm) and moving FORWARD
        if not in_event:
            if row['dist_front'] < 200 and row['action'] == 'FORWARD':
                in_event = True
                start_idx = i

        # End condition: Path clear (> 250mm) and moving FORWARD
        elif in_event:
            if row['dist_front'] > 250 and row['action'] == 'FORWARD':
                # Check if we actually turned in between
                segment = df.iloc[start_idx:i]
                unique_actions = segment['action'].unique()
                if 'TURN_LEFT' in unique_actions or 'TURN_RIGHT' in unique_actions:
                    # Score the event: duration, min distance
                    duration = i - start_idx
                    min_dist = segment['dist_front'].min()
                    events.append({
                        'type': 'Avoidance',
                        'start_cycle': df.iloc[start_idx]['cycle'],
                        'end_cycle': row['cycle'],
                        'start_idx': start_idx,
                        'end_idx': i,
                        'duration': duration,
                        'min_dist': min_dist
                    })
                in_event = False
            elif i - start_idx > 200: # Timeout (too long stuck)
                in_event = False

    return events

def find_narrow_passage(df):
    events = []
    in_event = False
    start_idx = 0

    # Reset index
    df = df.reset_index(drop=True)

    for i in range(len(df)):
        row = df.iloc[i]

        condition = row['dist_left'] < 150 and row['dist_right'] < 150

        if not in_event and condition:
            in_event = True
            start_idx = i
        elif in_event and not condition:
            if i - start_idx > 20: # At least 20 cycles
                events.append({
                    'type': 'Narrow Passage',
                    'start_cycle': df.iloc[start_idx]['cycle'],
                    'end_cycle': row['cycle'],
                    'start_idx': start_idx,
                    'end_idx': i,
                    'duration': i - start_idx
                })
            in_event = False

    return events

scenarios = []
scenarios.extend(find_avoidance_scenarios(df))
scenarios.extend(find_narrow_passage(df))

print(f"Found {len(scenarios)} scenarios.")

# Select "Best" scenarios
# For avoidance: clean execution (short but effective duration, safe min distance)
avoidance = [s for s in scenarios if s['type'] == 'Avoidance']
avoidance.sort(key=lambda x: x['min_dist'], reverse=True) # Safest first (closest approach was not too close?)
# Actually best avoidance handles close calls well.
# Maybe sort by successful outcome? All here are successful by definition.
# Let's pick a few distinct ones.

if avoidance:
    print("Top Avoidance Scenarios:")
    for s in avoidance[:3]:
        print(s)

passage = [s for s in scenarios if s['type'] == 'Narrow Passage']
passage.sort(key=lambda x: x['duration'], reverse=True) # Longest successful navigation

if passage:
    print("Top Narrow Passage Scenarios:")
    for s in passage[:3]:
        print(s)

# Reset index for plotting using global df
df = df.reset_index(drop=True)

# Visualize the best one of each
def plot_scenario(scenario, index):
    start = max(0, scenario['start_idx'] - 10)
    end = min(len(df)-1, scenario['end_idx'] + 10)
    segment = df.iloc[start:end]

    plt.figure(figsize=(10, 6))

    # Plot Path
    plt.plot(segment['x'], segment['y'], 'b.-', label='Path', linewidth=1)

    # Highlight Turns
    turns = segment[segment['action'].str.contains('TURN', na=False)]
    if not turns.empty:
        plt.plot(turns['x'], turns['y'], 'rx', label='Turns')

    # Start/End
    plt.plot(segment.iloc[0]['x'], segment.iloc[0]['y'], 'go', label='Start')
    plt.plot(segment.iloc[-1]['x'], segment.iloc[-1]['y'], 'ko', label='End')

    plt.title(f"{scenario['type']} - Cycles {scenario['start_cycle']} to {scenario['end_cycle']}")
    plt.xlabel('X (mm)')
    plt.ylabel('Y (mm)')
    plt.legend()
    plt.grid(True)
    plt.axis('equal')

    filename = f"scenario_{index}_{scenario['type'].replace(' ', '_')}.png"
    plt.savefig(filename)
    print(f"Saved {filename}")
    plt.close()

    # Also plot sensor readings
    plt.figure(figsize=(10, 4))
    x_axis = range(len(segment))
    plt.plot(x_axis, segment['dist_left'], 'g--', label='Left', alpha=0.6)
    plt.plot(x_axis, segment['dist_front'], 'r-', label='Front', linewidth=2)
    plt.plot(x_axis, segment['dist_right'], 'b--', label='Right', alpha=0.6)
    plt.title(f"Sensor Readings - {scenario['type']}")
    plt.ylabel('Distance (mm)')
    plt.xlabel('Steps')
    plt.legend()
    plt.grid(True)

    filename_sensors = f"scenario_{index}_{scenario['type'].replace(' ', '_')}_sensors.png"
    plt.savefig(filename_sensors)
    print(f"Saved {filename_sensors}")
    plt.close()

def animate_scenario(scenario, index):
    start = max(0, scenario['start_idx'] - 5)
    end = min(len(df)-1, scenario['end_idx'] + 5)
    segment = df.iloc[start:end].reset_index(drop=True)

    # Downsample if too long (aim for ~100 frames max)
    step = max(1, len(segment) // 100)
    indices = range(0, len(segment), step)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title(f"{scenario['type']} Animation")
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.grid(True)
    ax.axis('equal')

    # Static context (start position)
    ax.plot(segment['x'].iloc[0], segment['y'].iloc[0], 'go', label='Start')

    line, = ax.plot([], [], 'b.-', label='Path')
    robot_marker, = ax.plot([], [], 'ro', markersize=10, label='Robot')

    # Set limits based on full path
    ax.set_xlim(segment['x'].min() - 100, segment['x'].max() + 100)
    ax.set_ylim(segment['y'].min() - 100, segment['y'].max() + 100)
    ax.legend()

    def update(frame_idx):
        # frame_idx is index in 'indices'
        data_idx = indices[frame_idx]
        current_data = segment.iloc[:data_idx+1]
        line.set_data(current_data['x'], current_data['y'])

        if not current_data.empty:
            robot_marker.set_data([current_data['x'].iloc[-1]], [current_data['y'].iloc[-1]])

        return line, robot_marker

    ani = animation.FuncAnimation(fig, update, frames=len(indices), interval=50, blit=True)

    filename_gif = f"scenario_{index}_{scenario['type'].replace(' ', '_')}.gif"
    try:
        ani.save(filename_gif, writer='pillow', fps=15)
        print(f"Saved {filename_gif}")
    except Exception as e:
        print(f"Could not save GIF {filename_gif}: {e}")

    plt.close()

# Plot top 2 avoidance and top 1 passage
count = 0
for s in avoidance[:2]:
    plot_scenario(s, count)
    animate_scenario(s, count)
    count += 1

for s in passage[:1]:
    plot_scenario(s, count)
    animate_scenario(s, count)
    count += 1
