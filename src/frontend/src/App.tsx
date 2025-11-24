/**
 * Main App Component
 * Entry point for the AgenticFleet chat application
 */

import { ConversationSidebar } from "./components/chat/ConversationSidebar";
import { ChatContainer } from "./components/chat/ChatContainer";

function App() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* Sidebar */}
      <ConversationSidebar />

      {/* Main Chat Area */}
      <div className="flex-1">
        <ChatContainer />
      </div>
    </div>
  );
}

export default App;
