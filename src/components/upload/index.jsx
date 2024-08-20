import React, { useRef, useState } from "react";
import "./UploadComponent.css";
import axios from "axios";

function UploadComponent({ setUploadStatus, uploadStatus }) {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [disabled, setDisabled] = useState(true);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
    const maxSizeInMB = 2;
    const maxSizeInBytes = maxSizeInMB * 1024 * 1024;

    if (file && file.size > maxSizeInBytes) {
      setUploadStatus(
        `The file size exceeds ${maxSizeInMB}MB. Please upload a smaller file.`
      );
      return;
    }

    setDisabled(false);
  };

  const handleFileUpload = async () => {
    setDisabled(true);
    setLoading(true);
    // console.log("in file upload");
    if (!selectedFile) {
      setUploadStatus("No file selected");
      return;
    }

    const formData = new FormData();
    formData.append("pdf", selectedFile);

    try {
      // console.log("uploading");
      // "http://127.0.0.1:5000/upload",
      const response = await axios.post(
        "https://rag-app-rwei.onrender.com/upload",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );
      // console.log("uploaded");
      // console.log(response);
      setUploadStatus("File uploaded successfully");
      setDisabled(false);
      setLoading(false);
    } catch (error) {
      setUploadStatus("Error uploading file");
      console.error("Error uploading file:", error);
      setDisabled(false);
      setLoading(false);
    }
  };
  const handleIconClick = () => {
    fileInputRef.current.click(); // Trigger the file input click
  };

  return (
    <div className="upload-container">
      <div className="upload-box">
        <p>Upload your files</p>
        <p className="file-types">PDF Only</p>
        {loading ? (
          <div className="load">
            <span className="loader"></span>
          </div>
        ) : (
          <div className="upload-icon" onClick={handleIconClick}>
            <img
              src="https://i.pinimg.com/736x/04/54/7c/04547c2b354abb70a85ed8a2d1b33e5f.jpg"
              alt="Upload Icon"
            />
          </div>
        )}
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: "none" }}
          accept="application/pdf"
          onChange={handleFileChange}
        />
        <p className="status">{uploadStatus}</p>
        <div className="">
          <button onClick={handleFileUpload} disabled={disabled}>
            {loading ? "Loading..." : "Upload PDF"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default UploadComponent;
