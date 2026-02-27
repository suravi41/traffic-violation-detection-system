import os
import xml.etree.ElementTree as ET

# ✅ Change this if your folder name is slightly different
DATASET_FOLDER = os.path.join(os.path.dirname(__file__), "archive (2)")
IMAGES_FOLDER = os.path.join(DATASET_FOLDER, "images")
ANNOTATIONS_FOLDER = os.path.join(DATASET_FOLDER, "annotations")

# Output labels will go here (inside the dataset folder)
OUTPUT_LABELS_FOLDER = os.path.join(DATASET_FOLDER, "labels_yolo")
os.makedirs(OUTPUT_LABELS_FOLDER, exist_ok=True)

# We will map class names to numbers
# In this dataset, usually there are: helmet, person, head
# We will detect HELMET only for now (you can expand later)
CLASS_MAP = {
    "with helmet": 0,
    "without helmet": 1
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

        # Only convert helmet objects for now
        if class_name not in CLASS_MAP:
            continue

        class_id = CLASS_MAP[class_name]

        bbox = obj.find("bndbox")
        xmin = float(bbox.find("xmin").text)
        xmax = float(bbox.find("xmax").text)
        ymin = float(bbox.find("ymin").text)
        ymax = float(bbox.find("ymax").text)

        x, y, w, h = convert_bbox((img_w, img_h), (xmin, xmax, ymin, ymax))
        yolo_lines.append(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")

    # Save YOLO label file with same name as image/xml
    txt_file = xml_file.replace(".xml", ".txt")
    txt_path = os.path.join(OUTPUT_LABELS_FOLDER, txt_file)

    with open(txt_path, "w") as f:
        f.write("\n".join(yolo_lines))

print("✅ Conversion complete!")
print("YOLO labels saved in:", OUTPUT_LABELS_FOLDER)
