import React from "react";
import { createChatBotMessage } from "react-chatbot-kit";

import BotAvatar from "../components/botAvatar";
import Loader from "../components/loader";

const config = {
  initialMessages: [
    createChatBotMessage(
      `Hi. I am your pdf assistant what question do you have for me`
    ),
  ],
  widgets: [
    {
      widgetName: "loader",
      widgetFunc: (props) => <Loader {...props} />,
    },
  ],
  customComponents: {
    botAvatar: (props) => <BotAvatar {...props} />,
    userAvatar: (props) => <></>,
  },
};

export default config;
