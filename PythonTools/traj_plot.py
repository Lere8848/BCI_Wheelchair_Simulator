import json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.transforms as transforms
import numpy as np
import math
from scipy.spatial.transform import Rotation as R

# ========== Utility Functions ==========
def quaternion_to_yaw(q):
    """Convert Unity exported Quaternion(x, y, z, w) to Euler angle around Y axis"""
    r = R.from_quat([q["x"], q["y"], q["z"], q["w"]])
    yaw = r.as_euler('xyz', degrees=True)[1]  # Around Y axis
    return yaw

# ========== File Paths ==========
trajectory_path = "Assets/Logs/trajectory_20250722_162624.json"
obstacle_path = "Assets/Logs/obstacles.json"

# ========== Load Trajectory ==========
with open(trajectory_path, 'r') as f:
    traj_data = json.load(f)["points"]

positions = np.array([[p["position"]["x"], p["position"]["z"]] for p in traj_data])

# ========== Load Obstacles ==========
with open(obstacle_path, 'r') as f:
    obs_data = json.load(f)["obstacles"]

# ========== Plot Preparation ==========
fig, ax = plt.subplots(figsize=(8, 8))
ax.set_aspect('equal')

# Draw wheelchair trajectory line
ax.plot(positions[:, 0], positions[:, 1], color='gold', linewidth=2, label="Trajectory")

# Draw wheelchair arrows (direction)
for i in range(0, len(traj_data), 10):
    p = traj_data[i]
    x, z = p["position"]["x"], p["position"]["z"]
    yaw = quaternion_to_yaw(p["rotation"])
    dx = 0.3 * math.sin(math.radians(yaw))
    dz = 0.3 * math.cos(math.radians(yaw))
    ax.arrow(x, z, dx, dz, head_width=0.15, head_length=0.15, fc='red', ec='red')

# ========== Draw Obstacles ==========
for ob in obs_data:
    pos = ob["position"]
    size = ob["size"]
    rot = ob["rotation"]
    name = ob["name"]

    # Center point & size
    cx = pos["x"]
    cz = pos["z"]
    w = size["x"]
    h = size["z"]
    angle = quaternion_to_yaw(rot)  # degrees
    
    # Print obstacle quaternion information (only walls)
    # if "Wall" in name:
    #     print(f"Wall: {name}, position=({cx:.2f}, {cz:.2f}), quaternion=({rot['x']:.3f}, {rot['y']:.3f}, {rot['z']:.3f}, {rot['w']:.3f}), angle={angle:.2f}°")

    # Bottom-left coordinate
    x0 = cx - w / 2
    z0 = cz - h / 2

    p0 = Rectangle((x0, z0), 0.1, 0.1)  # Rectangle starting point (matplotlib Rectangle uses bottom-left as anchor)
    c0 = Rectangle((cx, cz), 0.1, 0.1, edgecolor='red', facecolor='none')  # Obstacle center point (also bottom-left)

    # Default edge and fill colors
    edge_color = 'black'  # Default edge color
    face_color = 'gray'   # Default fill color
    
    # Determine starting position and color based on object type
    # This is because Unity uses left-handed coordinates while matplotlib uses right-handed coordinates, leading to different rotation directions
    if "Wall" in name:
        # Walls are drawn from center point
        start_x = cx
        start_y = cz
        edge_color = 'blue'  # Walls use blue edge
    else:
        # Other obstacles are drawn from bottom-left
        start_x = x0
        start_y = z0
        edge_color = 'black'  # Other obstacles use black edge

    # Create obstacle rectangle
    rect = Rectangle((start_x, start_y), w, h, edgecolor=edge_color, facecolor=face_color, 
                    alpha=0.5, linewidth=2)

    # test_rect = Rectangle((0, 0), 1, 1, edgecolor='blue', facecolor='green', alpha=0.3)
    # ax.add_patch(test_rect)

    # ====== Rotate obstacle around its center point =========
    # Check if it's a wall with Rotation (0,0,0,1)
    is_identity_rotation = "Wall" in name and abs(rot["x"]) < 0.01 and abs(rot["y"]) < 0.01 and abs(rot["z"]) < 0.01 and abs(rot["w"] - 1.0) < 0.01

    if is_identity_rotation:
        # For walls with quaternion (0,0,0,1), rotate an additional 180 degrees
        # This is because Unity uses left-handed coordinates while matplotlib uses right-handed coordinates, leading to different rotation directions
        adjusted_angle = angle + 180.0
        # print(f"Wall special handling: {name}, original angle={angle:.2f}°, adjusted angle={adjusted_angle:.2f}°")
        t = transforms.Affine2D().rotate_deg_around(cx, cz, adjusted_angle) + ax.transData
    else:
        # Other objects rotate normally
        t = transforms.Affine2D().rotate_deg_around(cx, cz, angle) + ax.transData

    rect.set_transform(t)
    p0.set_transform(t)
    c0.set_transform(t)

    ax.add_patch(rect)
    # ax.add_patch(p0)
    # ax.add_patch(c0)
    
    # Add angle label for walls
    # if "Wall" in name:
    #     display_angle = angle + 180.0 if is_identity_rotation else angle
    #     plt.text(cx, cz, f"{display_angle:.0f}°", fontsize=8, ha='center', va='center', 
    #             color='black', weight='bold')


# ========== Plot Settings ==========
ax.set_title("Wheelchair Topdown Trajectory and Obstacles")
ax.set_xlabel("X")
ax.set_ylabel("Z")
ax.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("Assets/Logs/trajectory_plot.png")
print("Plot saved to Assets/Logs/trajectory_plot.png")
plt.show()
