import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import api from "../services/api";

export default function Upload() {
  const [imageFile, setImageFile] = useState(null);
  const [videoFile, setVideoFile] = useState(null);
  const navigate = useNavigate();

  const handleUpload = async (e) => {
    e.preventDefault();

    if (!imageFile && !videoFile) {
      alert("Please select an image or a video.");
      return;
    }

    if (imageFile && videoFile) {
      alert("Please upload only one file at a time: either image or video.");
      return;
    }

    const formData = new FormData();
    let endpoint = "";

    if (imageFile) {
      formData.append("file", imageFile);
      endpoint = "/detect/all";
    }

    if (videoFile) {
      formData.append("file", videoFile);
      endpoint = "/detect/video";
    }

    try {
  const response = await api.post(endpoint, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  console.log("BACKEND RESPONSE:", response.data);

  navigate("/result", { state: response.data });

} catch (error) {
  console.error("FULL ERROR:", error);
  console.error("BACKEND ERROR:", error.response?.data);
  alert("Detection failed");
}
  };

  return (
    <div className="page">
      <Navbar />

      <div className="container">
        <div className="card">
          <h1 className="section-title">Upload Media</h1>
          <p className="muted">
            Upload an image or video to detect helmet violations, license plates,
            and traffic evidence.
          </p>

          <form onSubmit={handleUpload}>
            <label className="upload-box">
              <input
                type="file"
                accept="image/*"
                onChange={(e) => {
                  setImageFile(e.target.files[0]);
                  setVideoFile(null);
                }}
                style={{ display: "none" }}
              />

              <div className="upload-content">
                <h3>Upload Image</h3>
                <p className="muted">Supported: JPG, PNG, JPEG</p>
                {imageFile && (
                  <p className="file-name">Selected: {imageFile.name}</p>
                )}
              </div>
            </label>

            <label className="upload-box upload-box-second">
              <input
                type="file"
                accept="video/*"
                onChange={(e) => {
                  setVideoFile(e.target.files[0]);
                  setImageFile(null);
                }}
                style={{ display: "none" }}
              />

              <div className="upload-content">
                <h3>Upload Video</h3>
                <p className="muted">Recommended format: MP4</p>
                {videoFile && (
                  <p className="file-name">Selected: {videoFile.name}</p>
                )}
              </div>
            </label>

            <div className="center-btn">
              <button className="btn" type="submit">
                Run Detection
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}