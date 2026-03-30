import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";

export default function Home() {
  return (
    <>
      <Navbar />

      <div className="container">
        <div className="home-hero">
          <div>
            <h1>Traffic Monitoring</h1>
            <p>
              Smart traffic monitoring with AI &amp; Computer Vision. Upload an
              image to detect helmet usage, detect license plates, extract
              evidence, and generate results for traffic violation reporting.
            </p>

            <div className="hero-actions">
              <Link className="btn btn-primary" to="/upload">
                Get Started
              </Link>
              <Link className="btn btn-outline" to="/result">
                View Results
              </Link>
            </div>

            <div className="mini-grid">
              <div className="mini-card">
                <span className="tag">YOLOv8</span>
                <div className="mini-title">Helmet Detection</div>
                <div className="mini-text">
                  Detect helmets and highlight evidence in annotated output.
                </div>
              </div>

              <div className="mini-card">
                <span className="tag">YOLOv8</span>
                <div className="mini-title">Plate Detection</div>
                <div className="mini-text">
                  Detect license plates and save plate crops for evidence.
                </div>
              </div>

              <div className="mini-card">
                <span className="tag">OCR</span>
                <div className="mini-title">Plate Reading</div>
                <div className="mini-text">
                  Extract plate text with confidence score (EasyOCR).
                </div>
              </div>
            </div>
          </div>

          <div className="hero-image">
            <img src="/home_banner.jpg" alt="Traffic Monitoring Banner" />
          </div>
        </div>
      </div>
    </>
  );
}