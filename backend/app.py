from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from lane_detection import (
    detect_lane_lines,
    draw_lane_lines,
    check_all_vehicles,
    combine_violations
)

from database import engine, SessionLocal
from models import Base, Detection, Plate, Evidence

import os
import json
import cv2
import subprocess
from datetime import datetime


HELMET_MODEL = None
PLATE_MODEL = None
OCR_READER = None

FFMPEG_PATH =  r"C:\Users\Legion\Downloads\ffmpeg-8.1-essentials_build\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe"


def get_helmet_model():
    global HELMET_MODEL
    if HELMET_MODEL is None:
        from ultralytics import YOLO
        HELMET_MODEL = YOLO("../ml_model/weights/trained/helmet_final_best.pt")
    return HELMET_MODEL


def get_plate_model():
    global PLATE_MODEL
    if PLATE_MODEL is None:
        from ultralytics import YOLO
        PLATE_MODEL = YOLO("../ml_model/weights/trained/license_plate_final_best.pt")
    return PLATE_MODEL


def get_ocr_reader():
    global OCR_READER
    if OCR_READER is None:
        import easyocr
        OCR_READER = easyocr.Reader(["en"], gpu=False)
    return OCR_READER


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
VIDEO_UPLOADS_DIR = os.path.join(BASE_DIR, "video_uploads")
EVIDENCE_DIR = os.path.join(BASE_DIR, "evidence")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(VIDEO_UPLOADS_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(title="Traffic Violation Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.add_middleware(SessionMiddleware, secret_key="super-secret-key-change-later")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/evidence-files", StaticFiles(directory=EVIDENCE_DIR), name="evidence_files")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

DEMO_USER = {"username": "officer", "password": "1234"}


def is_logged_in(request: Request) -> bool:
    return request.session.get("logged_in", False) is True


def convert_to_browser_mp4(input_path, output_path):
    command = [
        FFMPEG_PATH,
        "-y",
        "-i", input_path,
        "-vcodec", "libx264",
        "-acodec", "aac",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    return subprocess.run(command, capture_output=True, text=True)


@app.get("/ping")
def ping():
    return {"ok": True}


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

    db = SessionLocal()
    try:
        records = (
            db.query(Detection, Evidence)
            .outerjoin(Evidence, Detection.id == Evidence.detection_id)
            .order_by(Detection.created_at.desc())
            .all()
        )

        items = []
        for detection, evidence in records:
            created_at = ""
            if detection.created_at:
                created_at = detection.created_at.strftime("%Y-%m-%d %I:%M:%S %p")

            json_file = ""
            if evidence and evidence.json_path:
                json_file = os.path.basename(evidence.json_path)

            items.append({
                "file": json_file,
                "created_at": created_at,
                "image_name": detection.image_name,
                "helmet_count": detection.helmet_count,
                "plate_count": detection.plate_count,
                "violation": detection.violation,
                "detection_id": detection.id
            })

        return templates.TemplateResponse(
            "evidence.html",
            {"request": request, "items": items}
        )
    finally:
        db.close()


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


def save_upload(file: UploadFile) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename.replace(" ", "_")
    out_name = f"{ts}_{safe_name}"
    out_path = os.path.join(UPLOADS_DIR, out_name)
    with open(out_path, "wb") as f:
        f.write(file.file.read())
    return out_path


def save_video_upload(file: UploadFile) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename.replace(" ", "_")
    out_name = f"{ts}_{safe_name}"
    out_path = os.path.join(VIDEO_UPLOADS_DIR, out_name)
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
        cv2.putText(
            image_bgr,
            label,
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )
    return image_bgr


def get_vehicle_boxes_from_detections(detections):
    boxes = []
    for d in detections:
        x1, y1, x2, y2 = map(int, d["box_xyxy"])
        boxes.append((x1, y1, x2, y2))
    return boxes


def has_no_helmet_detection(detections):
    keywords = [
        "no_helmet",
        "no helmet",
        "without_helmet",
        "without helmet",
        "lack-of-helmet",
        "lack_of_helmet",
        "lack of helmet"
    ]

    for d in detections:
        class_name = d.get("class_name", "").lower()
        for keyword in keywords:
            if keyword in class_name:
                return True
    return False


@app.post("/detect/all")
async def detect_all(file: UploadFile = File(...)):
    db = SessionLocal()
    try:
        image_path = save_upload(file)
        created_at = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        helmet_model = get_helmet_model()
        plate_model = get_plate_model()
        ocr = get_ocr_reader()

        helmet_dets = run_yolo(helmet_model, image_path, conf=0.15, imgsz=1280, iou=0.5)
        plate_dets = run_yolo(plate_model, image_path, conf=0.25, imgsz=960, iou=0.5)

        img = cv2.imread(image_path)
        if img is None:
            return JSONResponse({"error": "Could not read uploaded image"}, status_code=400)

        plates_ocr = []
        for i, p in enumerate(plate_dets, start=1):
            x1, y1, x2, y2 = map(int, p["box_xyxy"])
            crop = img[y1:y2, x1:x2]

            if crop.size == 0:
                continue

            crop_name = os.path.basename(image_path).replace(".", "_") + f"_all_plate_crop_{i}.jpg"
            crop_path = os.path.join(EVIDENCE_DIR, crop_name)
            cv2.imwrite(crop_path, crop)

            ocr_texts = []
            try:
                out = ocr.readtext(crop)
                for (_bbox, text, confv) in out:
                    ocr_texts.append({
                        "text": "".join(text.split()),
                        "confidence": round(float(confv), 4)
                    })
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

        lane_lines, edges, cropped_edges = detect_lane_lines(img)
        lane_img, valid_lines = draw_lane_lines(img.copy(), lane_lines)

        vehicle_boxes = get_vehicle_boxes_from_detections(helmet_dets)
        lane_results = check_all_vehicles(vehicle_boxes, valid_lines)

        lane_crossing_detected = any(item["lane_crossing"] for item in lane_results)
        no_helmet_detected = has_no_helmet_detection(helmet_dets)
        final_violation = combine_violations(no_helmet_detected, lane_crossing_detected)

        annotated_img = lane_img.copy()
        annotated_img = draw_boxes(annotated_img, helmet_dets, color=(255, 0, 0))
        annotated_img = draw_boxes(annotated_img, plate_dets, color=(0, 255, 0))

        for item in lane_results:
            if item["lane_crossing"]:
                x1, y1, x2, y2 = item["box"]
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 0, 255), 3)
                cv2.putText(
                    annotated_img,
                    "Lane Crossing",
                    (x1, max(20, y1 - 15)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

        base = os.path.basename(image_path).replace(".", "_")
        annotated_name = f"{base}_ALL_annotated.jpg"
        annotated_path = os.path.join(EVIDENCE_DIR, annotated_name)
        cv2.imwrite(annotated_path, annotated_img)

        edges_name = f"{base}_lane_edges.jpg"
        roi_name = f"{base}_lane_roi.jpg"
        cv2.imwrite(os.path.join(EVIDENCE_DIR, edges_name), edges)
        cv2.imwrite(os.path.join(EVIDENCE_DIR, roi_name), cropped_edges)

        evidence_data = {
            "created_at": created_at,
            "uploaded_file": os.path.basename(image_path),
            "helmet_count": len(helmet_dets),
            "plate_count": len(plate_dets),
            "no_helmet_detected": no_helmet_detected,
            "lane_crossing_detected": lane_crossing_detected,
            "violation": final_violation,
            "helmet_detections": helmet_dets,
            "plate_detections": plate_dets,
            "plates_ocr": plates_ocr,
            "lane_results": lane_results,
            "annotated_image": annotated_name,
            "annotated_image_url": f"/evidence-files/{annotated_name}",
            "lane_edges_url": f"/evidence-files/{edges_name}",
            "lane_roi_url": f"/evidence-files/{roi_name}"
        }

        json_name = f"{base}_ALL.json"
        json_path = os.path.join(EVIDENCE_DIR, json_name)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(evidence_data, f, indent=2)

        new_detection = Detection(
            image_name=os.path.basename(image_path),
            helmet_count=len(helmet_dets),
            plate_count=len(plate_dets),
            violation=final_violation
        )
        db.add(new_detection)
        db.commit()
        db.refresh(new_detection)

        for plate_item in plates_ocr:
            ocr_candidates = plate_item.get("ocr_candidates", [])
            if ocr_candidates:
                first_candidate = ocr_candidates[0]
                plate_text = first_candidate.get("text", "")
                confidence = str(first_candidate.get("confidence", ""))
            else:
                plate_text = ""
                confidence = ""

            new_plate = Plate(
                detection_id=new_detection.id,
                plate_text=plate_text,
                confidence=confidence
            )
            db.add(new_plate)

        new_evidence = Evidence(
            detection_id=new_detection.id,
            json_path=json_path,
            annotated_image_path=annotated_path
        )
        db.add(new_evidence)
        db.commit()

        evidence_data["evidence_json_saved_as"] = json_name
        evidence_data["database_saved"] = True
        evidence_data["detection_id"] = new_detection.id

        return JSONResponse(evidence_data)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    finally:
        db.close()


@app.post("/detect/video")
async def detect_video(file: UploadFile = File(...)):
    db = SessionLocal()
    try:
        video_path = save_video_upload(file)
        video_name = os.path.basename(video_path)

        helmet_model = get_helmet_model()
        plate_model = get_plate_model()
        ocr = get_ocr_reader()

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return JSONResponse({"error": "Could not open video file"}, status_code=400)

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 20.0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        temp_output_name = f"{os.path.splitext(video_name)[0]}_processed_temp.mp4"
        temp_output_path = os.path.join(EVIDENCE_DIR, temp_output_name)

        output_video_name = f"{os.path.splitext(video_name)[0]}_processed.mp4"
        output_video_path = os.path.join(EVIDENCE_DIR, output_video_name)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height))

        if not writer.isOpened():
            return JSONResponse({"error": "Could not create processed video writer"}, status_code=500)

        frame_count = 0
        processed_frames = 0
        max_helmet_dets_in_frame = 0
        max_plate_dets_in_frame = 0
        total_lane_crossing_frames = 0
        total_no_helmet_frames = 0
        saved_frames = []

        last_helmet_dets = []
        last_plate_dets = []
        last_lane_results = []
        last_final_violation = "No Violation"
        last_no_helmet_detected = False
        last_lane_crossing_detected = False

        frame_skip = 3

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            annotated_frame = frame.copy()

            lane_lines, _, _ = detect_lane_lines(frame)
            annotated_frame, valid_lines = draw_lane_lines(annotated_frame, lane_lines)

            plates_ocr = []

            if frame_count % frame_skip == 0:
                processed_frames += 1

                temp_frame_path = os.path.join(EVIDENCE_DIR, f"temp_frame_{frame_count}.jpg")
                cv2.imwrite(temp_frame_path, frame)

                helmet_dets = run_yolo(helmet_model, temp_frame_path, conf=0.15, imgsz=1280, iou=0.5)
                plate_dets = run_yolo(plate_model, temp_frame_path, conf=0.25, imgsz=960, iou=0.5)

                max_helmet_dets_in_frame = max(max_helmet_dets_in_frame, len(helmet_dets))
                max_plate_dets_in_frame = max(max_plate_dets_in_frame, len(plate_dets))

                vehicle_boxes = get_vehicle_boxes_from_detections(helmet_dets)
                lane_results = check_all_vehicles(vehicle_boxes, valid_lines)

                lane_crossing_detected = any(item["lane_crossing"] for item in lane_results)
                no_helmet_detected = has_no_helmet_detection(helmet_dets)
                final_violation = combine_violations(no_helmet_detected, lane_crossing_detected)

                last_helmet_dets = helmet_dets
                last_plate_dets = plate_dets
                last_lane_results = lane_results
                last_final_violation = final_violation
                last_no_helmet_detected = no_helmet_detected
                last_lane_crossing_detected = lane_crossing_detected

                if lane_crossing_detected:
                    total_lane_crossing_frames += 1

                if no_helmet_detected:
                    total_no_helmet_frames += 1

                for i, p in enumerate(plate_dets, start=1):
                    x1, y1, x2, y2 = map(int, p["box_xyxy"])
                    crop = frame[y1:y2, x1:x2]

                    if crop.size == 0:
                        continue

                    crop_name = f"{os.path.splitext(video_name)[0]}_frame_{frame_count}_plate_{i}.jpg"
                    crop_path = os.path.join(EVIDENCE_DIR, crop_name)
                    cv2.imwrite(crop_path, crop)

                    ocr_texts = []
                    try:
                        out = ocr.readtext(crop)
                        for (_bbox, text, confv) in out:
                            ocr_texts.append({
                                "text": "".join(text.split()),
                                "confidence": round(float(confv), 4)
                            })
                    except Exception:
                        pass

                    plates_ocr.append({
                        "plate_index": i,
                        "crop_image": crop_name,
                        "crop_image_url": f"/evidence-files/{crop_name}",
                        "ocr_candidates": ocr_texts
                    })

                if final_violation != "No Violation":
                    frame_file = f"{os.path.splitext(video_name)[0]}_frame_{frame_count}.jpg"
                    frame_save_path = os.path.join(EVIDENCE_DIR, frame_file)

                    temp_annotated = annotated_frame.copy()
                    temp_annotated = draw_boxes(temp_annotated, last_helmet_dets, color=(255, 0, 0))
                    temp_annotated = draw_boxes(temp_annotated, last_plate_dets, color=(0, 255, 0))

                    for item in last_lane_results:
                        if item["lane_crossing"]:
                            x1, y1, x2, y2 = item["box"]
                            cv2.rectangle(temp_annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)
                            cv2.putText(
                                temp_annotated,
                                "Lane Crossing",
                                (x1, max(20, y1 - 15)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (0, 0, 255),
                                2
                            )

                    cv2.putText(
                        temp_annotated,
                        f"Violation: {last_final_violation}",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 0, 255) if last_final_violation != "No Violation" else (0, 255, 0),
                        3
                    )

                    cv2.imwrite(frame_save_path, temp_annotated)

                    saved_frames.append({
                        "frame_number": frame_count,
                        "helmet_count": len(helmet_dets),
                        "plate_count": len(plate_dets),
                        "lane_crossing_detected": lane_crossing_detected,
                        "no_helmet_detected": no_helmet_detected,
                        "violation": final_violation,
                        "annotated_frame": frame_file,
                        "annotated_frame_url": f"/evidence-files/{frame_file}",
                        "plates_ocr": plates_ocr
                    })

                if os.path.exists(temp_frame_path):
                    os.remove(temp_frame_path)

            annotated_frame = draw_boxes(annotated_frame, last_helmet_dets, color=(255, 0, 0))
            annotated_frame = draw_boxes(annotated_frame, last_plate_dets, color=(0, 255, 0))

            for item in last_lane_results:
                if item["lane_crossing"]:
                    x1, y1, x2, y2 = item["box"]
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    cv2.putText(
                        annotated_frame,
                        "Lane Crossing",
                        (x1, max(20, y1 - 15)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2
                    )

            cv2.putText(
                annotated_frame,
                f"Violation: {last_final_violation}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255) if last_final_violation != "No Violation" else (0, 255, 0),
                3
            )

            writer.write(annotated_frame)

        cap.release()
        writer.release()

        conversion_result = convert_to_browser_mp4(temp_output_path, output_video_path)

        if conversion_result.returncode != 0:
            return JSONResponse({
                "error": "FFmpeg conversion failed",
                "details": conversion_result.stderr
            }, status_code=500)

        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)

        overall_violation = combine_violations(
            total_no_helmet_frames > 0,
            total_lane_crossing_frames > 0
        )

        summary_data = {
            "video_file": video_name,
            "processed_frames": processed_frames,
            "total_helmet_detections": max_helmet_dets_in_frame,
            "total_plate_detections": max_plate_dets_in_frame,
            "total_lane_crossing_frames": total_lane_crossing_frames,
            "total_no_helmet_frames": total_no_helmet_frames,
            "violation": overall_violation,
            "output_video": output_video_name,
            "output_video_url": f"/evidence-files/{output_video_name}",
            "saved_frames": saved_frames
        }

        json_name = f"{os.path.splitext(video_name)[0]}_VIDEO.json"
        json_path = os.path.join(EVIDENCE_DIR, json_name)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        new_detection = Detection(
            image_name=video_name,
            helmet_count=max_helmet_dets_in_frame,
            plate_count=max_plate_dets_in_frame,
            violation=overall_violation
        )
        db.add(new_detection)
        db.commit()
        db.refresh(new_detection)

        for frame_item in saved_frames:
            for plate_item in frame_item.get("plates_ocr", []):
                ocr_candidates = plate_item.get("ocr_candidates", [])
                if ocr_candidates:
                    first_candidate = ocr_candidates[0]
                    plate_text = first_candidate.get("text", "")
                    confidence = str(first_candidate.get("confidence", ""))
                else:
                    plate_text = ""
                    confidence = ""

                new_plate = Plate(
                    detection_id=new_detection.id,
                    plate_text=plate_text,
                    confidence=confidence
                )
                db.add(new_plate)

        new_evidence = Evidence(
            detection_id=new_detection.id,
            json_path=json_path,
            annotated_image_path=os.path.join(EVIDENCE_DIR, saved_frames[0]["annotated_frame"]) if saved_frames else output_video_path
        )
        db.add(new_evidence)
        db.commit()

        summary_data["database_saved"] = True
        summary_data["detection_id"] = new_detection.id

        return JSONResponse(summary_data)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    finally:
        db.close()