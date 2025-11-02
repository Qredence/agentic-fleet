import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ChatPage } from "@/pages/ChatPage";
import "./App.css";

// Create a query client for React Query (available for future use)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ChatPage />
    </QueryClientProvider>
  );
}

export default App;
