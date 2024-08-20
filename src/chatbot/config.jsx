import React from "react";
import { createChatBotMessage } from "react-chatbot-kit";

import BotAvatar from "../components/botAvatar";

const config = {
  initialMessages: [
    createChatBotMessage(
      `Hi. I am your pdf assistant what question do you have for me`
    ),
  ],

  customComponents: {
    botAvatar: (props) => <BotAvatar {...props} />,
    userAvatar: (props) => <></>,
  },
};

export default config;
