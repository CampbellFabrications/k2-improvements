import numpy as np
from itertools import product
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches


# Input unmodified mesh as a NumPy array
mesh = np.array([
    [0.272, 0.097, 0.075, 0.195, 0.257, 0.182, 0.15, 0.107, 0.14],
    [0.215, -0.005, -0.061, -0.006, 0.049, 0.048, 0.019, 0.02, 0.044],
    [0.205, 0.03, -0.068, -0.095, -0.107, -0.055, 0.002, 0.02, 0.042],
    [0.184, -0.048, -0.165, -0.163, -0.17, -0.088, 0.012, 0.057, 0.112],
    [0.057, -0.128, -0.135, -0.152, -0.153, -0.138, -0.078, 0.032, 0.002],
    [0.03, -0.083, -0.1, -0.128, -0.143, -0.103, -0.065, -0.05, -0.08],
    [0.042, 0.005, -0.028, -0.038, -0.08, -0.031, 0.022, -0.025, -0.053],
    [0.035, 0.023, 0.037, 0.055, 0.03, 0.052, 0.057, 0.022, 0.004],
    [0.11, 0.147, 0.202, 0.2, 0.19, 0.19, 0.182, 0.147, 0.097],
])

# Available tape thicknesses
tape_thicknesses = [0.1, 0.06]

# Generate all combinations of up to 4 tape pieces
max_pieces = 4
tape_combinations = []
for num_pieces in range(0, max_pieces + 1):  # Include the option for no tape
    tape_combinations.extend(product(tape_thicknesses, repeat=num_pieces))

# Precompute the total thickness for each combination
combination_sums = [sum(comb) for comb in tape_combinations]

# Identify the highest point in the mesh
highest_point = np.max(mesh)

# Calculate and print the starting range
starting_range = np.max(mesh) - np.min(mesh)
print(f"Starting Range: {starting_range:.5f}")

# Initialize variables to track the best solution
best_tape_plan = None
best_adjusted_mesh = None
smallest_range = float('inf')

# Iterate over all possible increments for the highest point
for increment in combination_sums:
    target_height = highest_point + increment

    # Create a temporary tape plan
    tape_plan = np.empty(mesh.shape, dtype=object)
    for i in range(mesh.shape[0]):
        for j in range(mesh.shape[1]):
            tape_plan[i, j] = []

    # Adjust all points to minimize the range
    for i in range(mesh.shape[0]):
        for j in range(mesh.shape[1]):
            required_height = target_height - mesh[i, j]
            if required_height <= 0:
                # If the point is already at or above the target, no tape needed
                continue

            # Find the tape combination that gets closest to the required height
            best_combination = None
            best_difference = float('inf')

            for comb, total in zip(tape_combinations, combination_sums):
                difference = abs(required_height - total)
                if difference < best_difference:
                    best_difference = difference
                    best_combination = comb

            # Store the best combination for the current point
            tape_plan[i, j] = best_combination

    # Calculate the adjusted mesh
    adjusted_mesh = np.empty(mesh.shape)
    for i in range(mesh.shape[0]):
        for j in range(mesh.shape[1]):
            adjustment = sum(tape_plan[i, j]) if tape_plan[i, j] else 0
            adjusted_mesh[i, j] = mesh[i, j] + adjustment

    # Calculate the range of the adjusted mesh
    current_range = np.max(adjusted_mesh) - np.min(adjusted_mesh)

    # Update the best solution if the current range is smaller
    if current_range < smallest_range:
        smallest_range = current_range
        best_tape_plan = tape_plan
        best_adjusted_mesh = adjusted_mesh

# Layer-by-layer plan
layered_plan = defaultdict(lambda: defaultdict(list))
layer_dims = mesh.shape  # Define layer dimensions

for i in range(best_tape_plan.shape[0]):
    for j in range(best_tape_plan.shape[1]):
        layers = best_tape_plan[i, j]
        for layer_num, thickness in enumerate(layers, start=1):
            layered_plan[layer_num][thickness].append((j, i))  # Using (x, y)

# Print the plan layer by layer
print("\nLayered Tape Plan:")
for layer_num, layer_details in layered_plan.items():
    print(f"\nLayer {layer_num}:")
    for thickness, points in layer_details.items():
        print(f"  {thickness}mm tape at points: {points}")


import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from collections import defaultdict

# Dimensions of a single tape piece
tape_size = 42.5

# Generate the actual bed coordinates
x_coords = np.arange(5, 346, 42.5)  # X-axis bed points
y_coords = np.arange(5, 346, 42.5)  # Y-axis bed points

# Function to visualize a single layer with centered tape pieces
def visualize_layer(layer_num, layer_details):
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(-20, 370)
    ax.set_ylim(-20, 370)
    ax.set_title(f"Layer {layer_num}", fontsize=16)
    ax.set_xlabel("X (mm)", fontsize=12)
    ax.set_ylabel("Y (mm)", fontsize=12)

    # Draw each tape piece as a centered square
    for thickness, points in layer_details.items():
        for x_idx, y_idx in points:
            # Convert indices to coordinates
            x = x_coords[x_idx]
            y = y_coords[y_idx]
            rect = patches.Rectangle(
                (x - tape_size / 2, y - tape_size / 2),  # Bottom-left corner
                tape_size,
                tape_size,
                linewidth=1,
                edgecolor="black",
                facecolor=plt.cm.viridis(thickness / max(tape_thicknesses)),
                label=f"{thickness}mm tape" if f"{thickness}mm tape" not in ax.get_legend_handles_labels()[1] else "",
            )
            ax.add_patch(rect)

    # Add grid and set ticks
    ax.set_xticks(x_coords)
    ax.set_yticks(y_coords)
    ax.set_xticklabels([f"{int(x)}" for x in x_coords], fontsize=10)
    ax.set_yticklabels([f"{int(y)}" for y in y_coords], fontsize=10)
    ax.grid(visible=True, linestyle="--", linewidth=0.5, alpha=0.7)

    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    unique_labels = dict(zip(labels, handles))  # Remove duplicates
    ax.legend(unique_labels.values(), unique_labels.keys(), fontsize=10)

    plt.gca().set_aspect('equal', adjustable='box')
    plt.show()


# Visualize each layer
for layer_num, layer_details in layered_plan.items():
    visualize_layer(layer_num, layer_details)
