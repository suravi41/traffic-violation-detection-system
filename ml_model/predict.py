from ultralytics import YOLO
import os
import json
from datetime import datetime

# Load your trained model
model = YOLO("runs/detect/helmet_detection_model3/weights/best.pt")

# Image to test
img_path = "ml_model/datasets/val/images/BikesHelmets30.png"

# Where to save evidence
EVIDENCE_DIR = "ml_model/evidence"
os.makedirs(EVIDENCE_DIR, exist_ok=True)

# Run prediction (save annotated image)
results = model.predict(source=img_path, save=True, conf=0.25)

# Collect detections
detections = []
helmet_count = 0

for r in results:
    if r.boxes is None:
        continue
    for b in r.boxes:
        cls_id = int(b.cls[0])
        conf = float(b.conf[0])
        xyxy = [float(x) for x in b.xyxy[0].tolist()]
        detections.append({
            "class_id": cls_id,
            "class_name": model.names.get(cls_id, str(cls_id)),
            "confidence": round(conf, 4),
            "box_xyxy": [round(x, 2) for x in xyxy]
        })
        if model.names.get(cls_id, "").lower() == "helmet":
            helmet_count += 1

# Save JSON evidence
base_name = os.path.splitext(os.path.basename(img_path))[0]
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
json_name = f"evidence_{base_name}_{timestamp}.json"
json_path = os.path.join(EVIDENCE_DIR, json_name)

evidence_data = {
    "source_image": img_path,
    "helmet_count": helmet_count,
    "detections": detections
}

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(evidence_data, f, indent=2)

print("✅ Prediction complete!")
print("✅ JSON saved to:", json_path)
print("Check annotated image in: runs/detect/predict/")
