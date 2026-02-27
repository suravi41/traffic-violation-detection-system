from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import os
import json
from datetime import datetime
import cv2

# ----------------------------
# IMPORTANT: lazy load models (fast server start)
# ----------------------------
HELMET_MODEL = None
PLATE_MODEL = None
OCR_READER = None


def get_helmet_model():
    global HELMET_MODEL
    if HELMET_MODEL is None:
        from ultralytics import YOLO
        HELMET_MODEL = YOLO("runs/detect/helmet_detection_model3/weights/best.pt")
    return HELMET_MODEL


def get_plate_model():
    global PLATE_MODEL
    if PLATE_MODEL is None:
        from ultralytics import YOLO
        PLATE_MODEL = YOLO("runs/detect/train/weights/best.pt")
    return PLATE_MODEL


def get_ocr_reader():
    global OCR_READER
    if OCR_READER is None:
        import easyocr
        OCR_READER = easyocr.Reader(["en"], gpu=False)
    return OCR_READER


# ----------------------------
# Paths
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
EVIDENCE_DIR = os.path.join(BASE_DIR, "evidence")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ----------------------------
# App setup
# ----------------------------
app = FastAPI(title="Traffic Violation Detection API", version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key="super-secret-key-change-later")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Evidence files served here (NOT /evidence, because /evidence is a page route)
app.mount("/evidence-files", StaticFiles(directory=EVIDENCE_DIR), name="evidence_files")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ----------------------------
# Demo login
# ----------------------------
DEMO_USER = {"username": "officer", "password": "1234"}


def is_logged_in(request: Request) -> bool:
    return request.session.get("logged_in", False) is True


@app.get("/ping")
def ping():
    return {"ok": True}


# ----------------------------
# UI ROUTES
# ----------------------------
@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")

    if username == DEMO_USER["username"] and password == DEMO_USER["password"]:
        request.session["logged_in"] = True
        request.session["officer_name"] = "Officer Demo"
        return RedirectResponse(url="/home", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username/password"}
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/services", response_class=HTMLResponse)
def services_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")

    html = """
    <!DOCTYPE html>
    <html><head>
      <meta charset="UTF-8"/>
      <title>Services</title>
      <link rel="stylesheet" href="/static/styles.css">
    </head><body>
      <div class="navbar">
        <div class="nav-inner">
          <div class="brand"><img src="/static/LOGO.jpg"><div>Traffic Monitoring</div></div>
          <div class="navlinks">
            <a href="/home">Home</a>
            <a class="active" href="/services">Services</a>
            <a href="/upload">Upload</a>
            <a href="/evidence">Evidence</a>
            <a href="/profile">Profile</a>
          </div>
          <div class="nav-actions">
            <a class="btn btn-outline" href="/logout">Logout</a>
          </div>
        </div>
      </div>

      <div class="container">
        <div class="card card-pad">
          <h2 class="section-title">Services</h2>
          <p class="muted">Main system services provided by this platform.</p>
          <div style="margin-top:12px" class="grid">
            <div class="card card-pad">
              <div class="badge">Helmet</div>
              <h3 style="margin:10px 0 0 0;">Helmet Detection</h3>
              <p class="muted">Detect helmets in traffic images using YOLOv8 custom model.</p>
            </div>
            <div class="card card-pad">
              <div class="badge">Plate</div>
              <h3 style="margin:10px 0 0 0;">License Plate Detection</h3>
              <p class="muted">Detect plates and extract evidence crops using custom YOLOv8 model.</p>
            </div>
            <div class="card card-pad">
              <div class="badge">OCR</div>
              <h3 style="margin:10px 0 0 0;">Plate OCR</h3>
              <p class="muted">Read plate numbers with confidence using EasyOCR.</p>
            </div>
          </div>
        </div>
      </div>
    </body></html>
    """
    return HTMLResponse(html)


@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "officer_name": request.session.get("officer_name", "Officer")}
    )


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/evidence", response_class=HTMLResponse)
def evidence_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")

    # Build list with file + created_at
    items = []
    json_files = [f for f in os.listdir(EVIDENCE_DIR) if f.lower().endswith(".json")]
    json_files.sort(reverse=True)

    for f in json_files:
        path = os.path.join(EVIDENCE_DIR, f)
        created_at = ""
        try:
            with open(path, "r", encoding="utf-8") as jf:
                data = json.load(jf)
                created_at = data.get("created_at", "")
        except Exception:
            created_at = ""

        items.append({"file": f, "created_at": created_at})

    return templates.TemplateResponse("evidence.html", {"request": request, "items": items})


@app.get("/result", response_class=HTMLResponse)
def result_page(request: Request, file: str = ""):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")

    if not file:
        return templates.TemplateResponse("result.html", {"request": request, "data": None, "file": ""})

    json_path = os.path.join(EVIDENCE_DIR, file)
    if not os.path.exists(json_path):
        return templates.TemplateResponse("result.html", {"request": request, "data": None, "file": file})

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return templates.TemplateResponse("result.html", {"request": request, "data": data, "file": file})


# ----------------------------
# Detection helpers
# ----------------------------
def save_upload(file: UploadFile) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename.replace(" ", "_")
    out_name = f"{ts}_{safe_name}"
    out_path = os.path.join(UPLOADS_DIR, out_name)
    with open(out_path, "wb") as f:
        f.write(file.file.read())
    return out_path


def run_yolo(model, image_path, conf=0.25, imgsz=640, iou=0.5):
    results = model.predict(image_path, conf=conf, imgsz=imgsz, iou=iou, verbose=False)
    r = results[0]

    dets = []
    if r.boxes is None:
        return dets

    names = model.names
    for box in r.boxes:
        cls_id = int(box.cls[0].item())
        confv = float(box.conf[0].item())
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        dets.append({
            "class_id": cls_id,
            "class_name": names.get(cls_id, str(cls_id)),
            "confidence": round(confv, 4),
            "box_xyxy": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]
        })
    return dets


def draw_boxes(image_bgr, detections, color=(255, 0, 0)):
    for d in detections:
        x1, y1, x2, y2 = map(int, d["box_xyxy"])
        label = f'{d["class_name"]} {d["confidence"]:.2f}'
        cv2.rectangle(image_bgr, (x1, y1), (x2, y2), color, 2)
        cv2.putText(image_bgr, label, (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    return image_bgr


# ----------------------------
# API ROUTES
# ----------------------------
@app.post("/detect/all")
async def detect_all(file: UploadFile = File(...)):
    # Save upload
    image_path = save_upload(file)

    # Create detection run time
    created_at = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    helmet_model = get_helmet_model()
    plate_model = get_plate_model()
    ocr = get_ocr_reader()

    # Helmet: better for far helmets
    helmet_dets = run_yolo(helmet_model, image_path, conf=0.15, imgsz=1280, iou=0.5)

    # Plate
    plate_dets = run_yolo(plate_model, image_path, conf=0.25, imgsz=960, iou=0.5)

    img = cv2.imread(image_path)
    plates_ocr = []

    for i, p in enumerate(plate_dets, start=1):
        x1, y1, x2, y2 = map(int, p["box_xyxy"])
        crop = img[y1:y2, x1:x2]

        crop_name = os.path.basename(image_path).replace(".", "_") + f"_all_plate_crop_{i}.jpg"
        crop_path = os.path.join(EVIDENCE_DIR, crop_name)
        cv2.imwrite(crop_path, crop)

        ocr_texts = []
        try:
            out = ocr.readtext(crop)
            for (_bbox, text, confv) in out:
                ocr_texts.append({"text": "".join(text.split()), "confidence": round(float(confv), 4)})
        except Exception:
            pass

        plates_ocr.append({
            "plate_index": i,
            "detection_confidence": p["confidence"],
            "box_xyxy": p["box_xyxy"],
            "crop_image": crop_name,
            "crop_image_url": f"/evidence-files/{crop_name}",
            "ocr_candidates": ocr_texts
        })

    # Annotated combined image
    img2 = cv2.imread(image_path)
    img2 = draw_boxes(img2, helmet_dets, color=(255, 0, 0))
    img2 = draw_boxes(img2, plate_dets, color=(0, 255, 0))

    base = os.path.basename(image_path).replace(".", "_")
    annotated_name = f"{base}_ALL_annotated.jpg"
    annotated_path = os.path.join(EVIDENCE_DIR, annotated_name)
    cv2.imwrite(annotated_path, img2)

    evidence_data = {
        "created_at": created_at,  # ✅ saved date/time
        "uploaded_file": os.path.basename(image_path),
        "helmet_count": len(helmet_dets),
        "plate_count": len(plate_dets),
        "helmet_detections": helmet_dets,
        "plate_detections": plate_dets,
        "plates_ocr": plates_ocr,
        "annotated_image": annotated_name,
        "annotated_image_url": f"/evidence-files/{annotated_name}"
    }

    json_name = f"{base}_ALL.json"
    json_path = os.path.join(EVIDENCE_DIR, json_name)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(evidence_data, f, indent=2)

    evidence_data["evidence_json_saved_as"] = json_name
    return JSONResponse(evidence_data)