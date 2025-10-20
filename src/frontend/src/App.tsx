import AgenticFleetChatbot from "./components/agenticfleet-chatbot";

function App() {
  return (
    <div className="min-h-screen bg-background">
      <AgenticFleetChatbot
        model="workflow_as_agent"
        placeholder="Ask me anything (with Worker ↔ Reviewer reflection)..."
      />
    </div>
  );
}

export default App;
