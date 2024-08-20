// import "./App.css";
import Chatbot from "react-chatbot-kit";
import config from "../../chatbot/config";
import ActionProvider from "../../chatbot/ActionProvider";
import MessageParser from "../../chatbot/MessageParser";

function Chat() {
  return (
    <div className="App">
      <Chatbot
        config={config}
        actionProvider={ActionProvider}
        messageParser={MessageParser}
      />
    </div>
  );
}

export default Chat;
