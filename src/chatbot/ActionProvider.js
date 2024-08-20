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
    // Add a loading message
    const loadingMessage = this.createChatBotMessage(
      "Please wait we are fetching your answer",
      {
        widget: "loader",
        loading: true,
        delay: 0,
      }
    );

    this.setState((prevState) => ({
      ...prevState,
      messages: [...prevState.messages, loadingMessage],
    }));

    if (!question) {
      // alert("Please enter a question");
      this.handleApiResponse("Please ask your question");
      // this.addMessageToState(message);
      return;
    }

    try {
      // "http://127.0.0.1:5000/ask",
      const response = await axios.post(
        "https://rag-app-rwei.onrender.com/ask",
        {
          question: question,
        }
      );
      // setAnswer(response.data.answer);
      if (response) {
        this.handleApiResponse(response.data.answer);
      }
      // this.addMessageToState(message);
    } catch (error) {
      this.handleApiResponse("An Error occured please try again");
      // this.addMessageToState(message);
      console.error("Error asking question:", error);
    }
  };

  handleApiResponse = (response) => {
    this.setState((prevState) => {
      const updatedMessages = prevState.messages.filter(
        (message) => !message.loading
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
