import React, { useEffect, useState } from "react";
import UploadComponent from "./components/upload";
import Chat from "./components/chat";
import axios from "axios";

function UploadPDF() {
  useEffect(() => {
    const resetSession = async () => {
      const user_id = localStorage.getItem("user_id");
      try {
        const result = await axios.post("http://127.0.0.1:5000/end_session", {
          user_id: user_id,
        });
        console.log(result.data.status);
        if (!user_id) {
          const newUserId = Math.round(Date.now() * Math.random());
          localStorage.setItem("user_id", newUserId);
        }
        setUploadStatus(" ");
        console.log(" user_id generated:", user_id);
      } catch (error) {
        console.error("Error resetting session:", error);
        // setResponse("Failed to reset session");
      }
    };

    resetSession();
  }, []);

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
