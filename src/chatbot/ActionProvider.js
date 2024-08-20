import axios from "axios";

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
    if (!question) {
      // alert("Please enter a question");
      const message = this.createChatBotMessage("Please ask your question");
      this.addMessageToState(message);
      return;
    }

    try {
      const response = await axios.post("http://127.0.0.1:5000/ask", {
        question: question,
      });
      // setAnswer(response.data.answer);
      const message = this.createChatBotMessage(response.data.answer);
      this.addMessageToState(message);
    } catch (error) {
      const message = this.createChatBotMessage(
        "An Error occured please try again"
      );
      this.addMessageToState(message);
      console.error("Error asking question:", error);
    }
  };

  addMessageToState = (message) => {
    this.setState((prevState) => ({
      ...prevState,
      messages: [...prevState.messages, message],
    }));
  };
}

export default ActionProvider;
