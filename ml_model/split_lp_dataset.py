import os
import random
import shutil

BASE_DIR = os.path.dirname(__file__)

SOURCE_IMAGES = os.path.join(BASE_DIR, "license_plate_dataset", "images")
SOURCE_LABELS = os.path.join(BASE_DIR, "license_plate_dataset", "labels_yolo")

TARGET_TRAIN_IMAGES = os.path.join(BASE_DIR, "lp_yolo", "datasets", "train", "images")
TARGET_TRAIN_LABELS = os.path.join(BASE_DIR, "lp_yolo", "datasets", "train", "labels")

TARGET_VAL_IMAGES = os.path.join(BASE_DIR, "lp_yolo", "datasets", "val", "images")
TARGET_VAL_LABELS = os.path.join(BASE_DIR, "lp_yolo", "datasets", "val", "labels")

os.makedirs(TARGET_TRAIN_IMAGES, exist_ok=True)
os.makedirs(TARGET_TRAIN_LABELS, exist_ok=True)
os.makedirs(TARGET_VAL_IMAGES, exist_ok=True)
os.makedirs(TARGET_VAL_LABELS, exist_ok=True)

images = [f for f in os.listdir(SOURCE_IMAGES) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
images.sort()

print("Total images found:", len(images))

random.seed(42)
random.shuffle(images)

split_ratio = 0.8
train_count = int(len(images) * split_ratio)

train_images = images[:train_count]
val_images = images[train_count:]

print("Train images:", len(train_images))
print("Val images:", len(val_images))

def copy_pair(img_name, img_dst_folder, lbl_dst_folder):
    src_img = os.path.join(SOURCE_IMAGES, img_name)
    dst_img = os.path.join(img_dst_folder, img_name)
    shutil.copy2(src_img, dst_img)

    base = os.path.splitext(img_name)[0]
    label_name = base + ".txt"
    src_lbl = os.path.join(SOURCE_LABELS, label_name)
    dst_lbl = os.path.join(lbl_dst_folder, label_name)

    if os.path.exists(src_lbl):
        shutil.copy2(src_lbl, dst_lbl)
    else:
        with open(dst_lbl, "w") as f:
            f.write("")

for img in train_images:
    copy_pair(img, TARGET_TRAIN_IMAGES, TARGET_TRAIN_LABELS)

for img in val_images:
    copy_pair(img, TARGET_VAL_IMAGES, TARGET_VAL_LABELS)

print("✅ Done! License plate dataset copied into ml_model/lp_yolo/datasets")
