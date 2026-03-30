import cv2
import numpy as np


def region_of_interest(image):
    height, width = image.shape[:2]

    polygon = np.array([
        [
            (0, height),
            (width, height),
            (width, int(height * 0.6)),
            (0, int(height * 0.6))
        ]
    ], np.int32)

    mask = np.zeros_like(image)
    cv2.fillPoly(mask, polygon, 255)
    masked_image = cv2.bitwise_and(image, mask)

    return masked_image


def detect_lane_lines(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    cropped_edges = region_of_interest(edges)

    lines = cv2.HoughLinesP(
    cropped_edges,
    rho=1,
    theta=np.pi / 180,
    threshold=100,
    minLineLength=120,
    maxLineGap=50
)

    return lines, edges, cropped_edges


def draw_lane_lines(image, lines):
    line_image = image.copy()
    valid_lines = []

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]

            if x2 - x1 == 0:
                continue

            slope = (y2 - y1) / (x2 - x1)

            if abs(slope) < 0.3:
                continue

            valid_lines.append((x1, y1, x2, y2))

            cv2.line(line_image, (x1, y1), (x2, y2), (0, 255, 0), 3)

    return line_image, valid_lines

def check_lane_crossing(vehicle_box, lines):
    """
    vehicle_box = (x1, y1, x2, y2)
    basic logic:
    if any detected lane line lies inside vehicle horizontal range
    and vertically overlaps lower vehicle area, mark as crossing
    """
    if lines is None or vehicle_box is None:
        return False

    vx1, vy1, vx2, vy2 = vehicle_box

    for line in lines:
        x1, y1, x2, y2 = line[0]

        line_min_x = min(x1, x2)
        line_max_x = max(x1, x2)
        line_min_y = min(y1, y2)
        line_max_y = max(y1, y2)

        horizontal_overlap = not (line_max_x < vx1 or line_min_x > vx2)
        vertical_overlap = not (line_max_y < vy1 or line_min_y > vy2)

        if horizontal_overlap and vertical_overlap:
            return True

    return False

def check_lane_crossing(vehicle_box, valid_lines):
    vx1, vy1, vx2, vy2 = vehicle_box

    for x1, y1, x2, y2 in valid_lines:
        line_min_x = min(x1, x2)
        line_max_x = max(x1, x2)
        line_min_y = min(y1, y2)
        line_max_y = max(y1, y2)

        horizontal_overlap = not (line_max_x < vx1 or line_min_x > vx2)
        vertical_overlap = not (line_max_y < vy1 or line_min_y > vy2)

        if horizontal_overlap and vertical_overlap:
            return True

    return False

def check_all_vehicles(vehicle_boxes, valid_lines):
    violations = []

    for box in vehicle_boxes:
        crossed = check_lane_crossing(box, valid_lines)

        violation_type = "Lane Crossing" if crossed else "No Violation"

        violations.append({
            "box": box,
            "lane_crossing": crossed,
            "violation_type": violation_type
        })

    return violations

def combine_violations(no_helmet, lane_crossing):
    if no_helmet and lane_crossing:
        return "No Helmet + Lane Crossing"
    elif no_helmet:
        return "No Helmet"
    elif lane_crossing:
        return "Lane Crossing"
    else:
        return "No Violation"