import React, { useState } from "react";
import axios from "axios";
import UploadComponent from "./components/upload";
import Chat from "./components/chat";

function UploadPDF() {
  const [uploadStatus, setUploadStatus] = useState("");

  return (
    <div>
      {uploadStatus === "File uploaded successfully" ? (
        <Chat />
      ) : (
        <UploadComponent
          setUploadStatus={setUploadStatus}
          uploadStatus={uploadStatus}
        />
      )}
    </div>
  );
}

export default UploadPDF;
