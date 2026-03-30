import cv2
from lane_detection import (
    detect_lane_lines,
    draw_lane_lines,
    check_all_vehicles,
    combine_violations
)

image_path = "test_image.jpg"

image = cv2.imread(image_path)

lines, edges, cropped_edges = detect_lane_lines(image)

output, valid_lines = draw_lane_lines(image, lines)

print("Detected lane lines:", valid_lines)

# -------- test vehicle boxes --------

vehicle_boxes = [
    (430, 235, 670, 445)
]

violations = check_all_vehicles(vehicle_boxes, valid_lines)

print("Violations:", violations)

no_helmet = True
lane_crossing = violations[0]["lane_crossing"]

final_violation = combine_violations(no_helmet, lane_crossing)

print("Final violation:", final_violation)

# draw boxes
for box in vehicle_boxes:
    vx1, vy1, vx2, vy2 = box
    cv2.rectangle(output, (vx1, vy1), (vx2, vy2), (0, 0, 255), 3)

# save images
cv2.imwrite("output_original.jpg", image)
cv2.imwrite("output_edges.jpg", edges)
cv2.imwrite("output_roi.jpg", cropped_edges)
cv2.imwrite("output_lane.jpg", output)

print("Lane detection test completed.")
print("Saved files:")
print("output_original.jpg")
print("output_edges.jpg")
print("output_roi.jpg")
print("output_lane.jpg")