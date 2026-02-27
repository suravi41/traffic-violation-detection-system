from ultralytics import YOLO

# Load pretrained YOLOv8 nano model
model = YOLO("yolov8n.pt")

# Start training
model.train(
    data="ml_model/data.yaml",  # path to dataset config
    epochs=20,
    imgsz=640,
    batch=8,
    name="helmet_detection_model"
)

print("✅ Training started successfully!")
