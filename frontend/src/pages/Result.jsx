import { useLocation } from "react-router-dom";
import Navbar from "../components/Navbar";

export default function Result() {
  const location = useLocation();
  const data = location.state;

  if (!data) {
    return (
      <div className="page">
        <Navbar />
        <div className="container">
          <div className="card">
            <h1 className="section-title">Detection Result</h1>
            <p className="muted">No result found.</p>
          </div>
        </div>
      </div>
    );
  }

  const isVideoResult =
    data.video_file !== undefined || data.output_video_url !== undefined;

  const violationText = data.violation || "No Violation";
  const hasViolation = violationText !== "No Violation";

  return (
    <div className="page">
      <Navbar />

      <div className="container">
        <div className="card">
          <h1 className="section-title">Detection Result</h1>

          <div className={`violation-banner ${hasViolation ? "danger" : "safe"}`}>
            <div className="violation-status">
              {hasViolation ? "Violation Detected" : "No Violation Detected"}
            </div>
            <div className="violation-type">
              Type: <strong>{violationText}</strong>
            </div>
          </div>

          <div className="result-grid">
            <div className="result-box">
              <h3>Uploaded File</h3>
              <p className="file-break">
                {data.uploaded_file || data.video_file || "N/A"}
              </p>
            </div>

            <div className="result-box">
              <h3>Helmet Detections</h3>
              <p>{data.helmet_count ?? data.total_helmet_detections ?? 0}</p>
            </div>

            <div className="result-box">
              <h3>Plate Detections</h3>
              <p>{data.plate_count ?? data.total_plate_detections ?? 0}</p>
            </div>

            <div className="result-box">
              <h3>Lane Crossing Frames</h3>
              <p>{data.total_lane_crossing_frames ?? (data.lane_crossing_detected ? 1 : 0)}</p>
            </div>
          </div>

          {!isVideoResult && data.annotated_image_url && (
            <div className="result-section">
              <h2 className="result-subtitle">Annotated Image</h2>
              <img
                src={`http://127.0.0.1:8000${data.annotated_image_url}`}
                alt="annotated"
                className="result-image"
              />
            </div>
          )}

          {isVideoResult && data.output_video_url && (
            <div className="result-section">
              <h2 className="result-subtitle">Processed Video</h2>
              <div className="video-wrapper">
                <video className="result-video" controls preload="metadata">
                  <source
                    src={`http://127.0.0.1:8000${data.output_video_url}`}
                    type="video/mp4"
                  />
                  Your browser does not support video playback.
                </video>
              </div>
            </div>
          )}

          {isVideoResult && (
            <div className="result-section">
              <h2 className="result-subtitle">Video Detection Summary</h2>

              <div className="result-grid">
                <div className="result-box">
                  <h3>Frames Processed</h3>
                  <p>{data.processed_frames ?? 0}</p>
                </div>

                <div className="result-box">
                  <h3>No Helmet Frames</h3>
                  <p>{data.total_no_helmet_frames ?? 0}</p>
                </div>

                <div className="result-box">
                  <h3>Lane Crossing Frames</h3>
                  <p>{data.total_lane_crossing_frames ?? 0}</p>
                </div>

                <div className="result-box">
                  <h3>Final Violation</h3>
                  <p>{violationText}</p>
                </div>
              </div>
            </div>
          )}

          {!isVideoResult && (
            <div className="result-section">
              <h2 className="result-subtitle">OCR Results</h2>

              {data.plates_ocr && data.plates_ocr.length > 0 ? (
                <div className="simple-ocr-list">
                  {data.plates_ocr.map((plate) => (
                    <div key={plate.plate_index} className="simple-ocr-item">
                      <p>
                        <strong>Plate #{plate.plate_index}:</strong>{" "}
                        {plate.ocr_candidates && plate.ocr_candidates.length > 0
                          ? plate.ocr_candidates[0].text
                          : "not available"}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">No OCR results available.</p>
              )}
            </div>
          )}

          {isVideoResult && data.saved_frames && data.saved_frames.length > 0 && (
            <div className="result-section">
              <h2 className="result-subtitle">Top Violation Evidence Frames</h2>

              <div className="video-note">
                Showing the first 6 important frames where a violation was detected.
              </div>

              <div className="evidence-grid">
                {data.saved_frames.slice(0, 6).map((frame, index) => (
                  <div key={index} className="evidence-card">
                    <div className="evidence-head">
                      <p className="evidence-title">Frame #{frame.frame_number}</p>
                      <span className="evidence-badge">{frame.violation}</span>
                    </div>

                    <div className="evidence-meta">
                      <p>
                        <strong>No Helmet:</strong>{" "}
                        {frame.no_helmet_detected ? "Yes" : "No"}
                      </p>
                      <p>
                        <strong>Lane Crossing:</strong>{" "}
                        {frame.lane_crossing_detected ? "Yes" : "No"}
                      </p>
                      <p>
                        <strong>Helmet Detections:</strong> {frame.helmet_count}
                      </p>
                      <p>
                        <strong>Plate Detections:</strong> {frame.plate_count}
                      </p>
                    </div>

                    {frame.annotated_frame_url && (
                      <img
                        src={`http://127.0.0.1:8000${frame.annotated_frame_url}`}
                        alt="evidence frame"
                        className="evidence-image"
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}