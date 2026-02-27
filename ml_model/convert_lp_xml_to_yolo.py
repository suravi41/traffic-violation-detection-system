import os
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(__file__)

DATASET_FOLDER = os.path.join(BASE_DIR, "license_plate_dataset")
IMAGES_FOLDER = os.path.join(DATASET_FOLDER, "images")
ANNOTATIONS_FOLDER = os.path.join(DATASET_FOLDER, "annotations")

OUTPUT_LABELS_FOLDER = os.path.join(DATASET_FOLDER, "labels_yolo")
os.makedirs(OUTPUT_LABELS_FOLDER, exist_ok=True)

# Most Kaggle car plate datasets use class name like: "plate"
# We will map any plate-like name to class 0
CLASS_MAP = {
    "plate": 0,
    "license plate": 0,
    "licence plate": 0,
    "licence": 0,
    "license": 0,
    "lp": 0,
    "number_plate": 0,
    "number plate": 0,
    "carplate": 0,
    "car plate": 0,
}

def convert_bbox(size, box):
    dw = 1.0 / size[0]
    dh = 1.0 / size[1]
    x_center = (box[0] + box[1]) / 2.0
    y_center = (box[2] + box[3]) / 2.0
    w = box[1] - box[0]
    h = box[3] - box[2]
    return (x_center * dw, y_center * dh, w * dw, h * dh)

xml_files = [f for f in os.listdir(ANNOTATIONS_FOLDER) if f.endswith(".xml")]
print("Total XML files found:", len(xml_files))

converted = 0

for xml_file in xml_files:
    xml_path = os.path.join(ANNOTATIONS_FOLDER, xml_file)
    tree = ET.parse(xml_path)
    root = tree.getroot()

    size = root.find("size")
    img_w = int(size.find("width").text)
    img_h = int(size.find("height").text)

    yolo_lines = []

    for obj in root.findall("object"):
        class_name = obj.find("name").text.lower().strip()

        # Try matching class names
        if class_name not in CLASS_MAP:
            # Sometimes "plate" is part of the name, like "licenseplate"
            if "plate" in class_name:
                class_id = 0
            else:
                continue
        else:
            class_id = CLASS_MAP[class_name]

        bbox = obj.find("bndbox")
        xmin = float(bbox.find("xmin").text)
        xmax = float(bbox.find("xmax").text)
        ymin = float(bbox.find("ymin").text)
        ymax = float(bbox.find("ymax").text)

        x, y, w, h = convert_bbox((img_w, img_h), (xmin, xmax, ymin, ymax))
        yolo_lines.append(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")

    txt_file = xml_file.replace(".xml", ".txt")
    txt_path = os.path.join(OUTPUT_LABELS_FOLDER, txt_file)

    with open(txt_path, "w") as f:
        f.write("\n".join(yolo_lines))

    if len(yolo_lines) > 0:
        converted += 1

print("✅ Conversion complete!")
print("Label files created:", len(xml_files))
print("Files with at least 1 plate box:", converted)
print("YOLO labels saved in:", OUTPUT_LABELS_FOLDER)
