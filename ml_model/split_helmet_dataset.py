import os
import random
import shutil

# --- Paths (these are inside your project) ---
BASE_DIR = os.path.dirname(__file__)  # ml_model folder

SOURCE_IMAGES = os.path.join(BASE_DIR, "archive (2)", "images")
SOURCE_LABELS = os.path.join(BASE_DIR, "archive (2)", "labels_yolo")

TARGET_TRAIN_IMAGES = os.path.join(BASE_DIR, "datasets", "train", "images")
TARGET_TRAIN_LABELS = os.path.join(BASE_DIR, "datasets", "train", "labels")

TARGET_VAL_IMAGES = os.path.join(BASE_DIR, "datasets", "val", "images")
TARGET_VAL_LABELS = os.path.join(BASE_DIR, "datasets", "val", "labels")

# --- Create folders if missing ---
os.makedirs(TARGET_TRAIN_IMAGES, exist_ok=True)
os.makedirs(TARGET_TRAIN_LABELS, exist_ok=True)
os.makedirs(TARGET_VAL_IMAGES, exist_ok=True)
os.makedirs(TARGET_VAL_LABELS, exist_ok=True)

# --- Collect all images ---
images = [f for f in os.listdir(SOURCE_IMAGES) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
images.sort()

print("Total images found:", len(images))

# --- Shuffle for random split ---
random.seed(42)  # fixed seed = same split every time (good for reports)
random.shuffle(images)

split_ratio = 0.8
train_count = int(len(images) * split_ratio)

train_images = images[:train_count]
val_images = images[train_count:]

print("Train images:", len(train_images))
print("Val images:", len(val_images))

def copy_pair(img_name, img_dst_folder, lbl_dst_folder):
    # copy image
    src_img_path = os.path.join(SOURCE_IMAGES, img_name)
    dst_img_path = os.path.join(img_dst_folder, img_name)
    shutil.copy2(src_img_path, dst_img_path)

    # copy label (same name but .txt)
    base = os.path.splitext(img_name)[0]
    label_name = base + ".txt"
    src_lbl_path = os.path.join(SOURCE_LABELS, label_name)
    dst_lbl_path = os.path.join(lbl_dst_folder, label_name)

    if os.path.exists(src_lbl_path):
        shutil.copy2(src_lbl_path, dst_lbl_path)
    else:
        # If label missing, create empty label file (YOLO allows empty labels)
        with open(dst_lbl_path, "w") as f:
            f.write("")

# --- Copy train ---
for img in train_images:
    copy_pair(img, TARGET_TRAIN_IMAGES, TARGET_TRAIN_LABELS)

# --- Copy val ---
for img in val_images:
    copy_pair(img, TARGET_VAL_IMAGES, TARGET_VAL_LABELS)

print("✅ Done! Files copied into datasets/train and datasets/val")
