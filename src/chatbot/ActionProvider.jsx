import axios from "axios";
import Loader from "../components/loader";

class ActionProvider {
  constructor(
    createChatBotMessage,
    setStateFunc,
    createClientMessage,
    stateRef,
    createCustomMessage,
    ...rest
  ) {
    this.createChatBotMessage = createChatBotMessage;
    this.setState = setStateFunc;
    this.createClientMessage = createClientMessage;
    this.stateRef = stateRef;
    this.createCustomMessage = createCustomMessage;
  }

  handleAskQuestion = async (question) => {
    const loadingMessage = this.createChatBotMessage(<Loader />, {
      option: { delay: 0 },
    });

    this.addMessageToState(loadingMessage);
    if (!question) {
      // alert("Please enter a question");
      this.handleApiResponse("Please ask your question");
      // this.addMessageToState(message);
      return;
    }

    try {
      const url = "https://rag-app-rwei.onrender.com/ask";
      // const testUrl = "http://127.0.0.1:5000/ask";
      const response = await axios.post(url, {
        question: question,
        user_id: localStorage.getItem("user_id"),
      });
      // setAnswer(response.data.answer);
      if (response) {
        this.handleApiResponse(response.data.answer);
      }
      console.log(this.stateRef);
      // this.addMessageToState(message);
    } catch (error) {
      this.handleApiResponse("An Error occured please try again");
      // this.addMessageToState(message);
      console.log(this.stateRef);
      console.error("Error asking question:", error);
    }
  };

  handleApiResponse = (response) => {
    this.setState((prevState) => {
      const updatedMessages = prevState.messages.filter(
        (msg) => typeof msg.message === "string"
      );

      const responseMessage = this.createChatBotMessage(response);

      return {
        ...prevState,
        messages: [...updatedMessages, responseMessage],
      };
    });
  };

  addMessageToState = (message) => {
    this.setState((prevState) => ({
      ...prevState,
      messages: [...prevState.messages, message],
    }));
  };
}

export default ActionProvider;
