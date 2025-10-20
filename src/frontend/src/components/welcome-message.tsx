import { memo } from "react";

const WelcomeMessage = memo(() => (
  <div className="mx-auto flex max-w-3xl flex-col items-center justify-center gap-4 px-4 py-12 text-center">
    <h2 className="text-2xl font-bold">Welcome to AgenticFleet</h2>
    <p className="text-muted-foreground">
      Multi-agent orchestration powered by Microsoft Agent Framework.
      Ask me anything!
    </p>
  </div>
));

WelcomeMessage.displayName = "WelcomeMessage";

export default WelcomeMessage;
