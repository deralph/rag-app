import React, { useEffect, useState } from "react";
import UploadComponent from "./components/upload";
import Chat from "./components/chat";
import axios from "axios";

function UploadPDF() {
  useEffect(() => {
    const get_user_id = () => localStorage.getItem("user_id");
    const resetSession = async () => {
      try {
        const url = "https://rag-app-rwei.onrender.com/end_session";
        // const testUrl = "http://127.0.0.1:5000/end_session";

        if (!get_user_id()) {
          const newUserId = Math.round(Date.now() * Math.random());
          localStorage.setItem("user_id", newUserId);
        }

        const result = await axios.post(url, {
          user_id: get_user_id(),
        });
        console.log(result.data.status);
        setUploadStatus(" ");
        console.log(" user_id generated:", get_user_id());
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
