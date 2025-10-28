# Examples Directory

This directory contains example implementations and demonstrations of various features and patterns used in the AgenticFleet frontend.

## 📁 Directory Structure

### `api/primitives/chatbot/`

A standalone chatbot implementation using Vercel AI SDK that demonstrates:

- **Basic streaming responses** using `streamText`
- **Tool integration** with date/time utilities
- **Simple API route** structure
- **Different model usage** (`gpt-4.1-nano`)

#### Features

- **Date & Time Tools**:
  - `getCurrentDate()` - Get current date with timezone info
  - `getTime(timezone)` - Get time in specific timezone

- **Streaming Responses**: Real-time text streaming

- **Model Integration**: Uses OpenAI's `gpt-4.1-nano` model

#### Usage

This is a **demonstration API route** that shows how to implement basic chatbot functionality with tool integration. It's **not** connected to the main AgenticFleet application.

#### API Endpoint

```
POST /api/primitives/chatbot
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "What time is it in Tokyo?"
    }
  ]
}
```

#### Response

Streams back text responses in real-time with tool execution results.

## 🔧 Integration Notes

This example uses a **different architecture** than the main AgenticFleet application:

- **Main App**: FastAPI backend + SSE streaming + custom hooks
- **Example**: Vercel AI SDK + tool integration

Both approaches are valid, but the main application uses the more sophisticated FastAPI + SSE pattern for complex multi-agent workflows.

## 🚀 How to Use

1. **Development**: The route is already configured in Vite proxy
2. **Testing**: Use tools like Postman or curl to test the endpoint
3. **Learning**: Study the implementation pattern for tool integration
4. **Adaptation**: Use as a reference for similar chatbot implementations

## 📚 Related Documentation

- [Vercel AI SDK](https://sdk.vercel.ai/docs/ai-sdk-core/overview)
- [Tool Calling Guide](https://sdk.vercel.ai/docs/ai-sdk-core/tools-and-tool-calling)
- [Streaming Responses](https://sdk.vercel.ai/docs/ai-sdk-core/streaming)

---

**Note**: This is a demonstration/example directory. The main AgenticFleet application is located in the parent directories and uses a different, more complex architecture.