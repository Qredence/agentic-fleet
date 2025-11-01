# AgenticFleet Frontend

React-based frontend for AgenticFleet multi-agent system with real-time SSE streaming and Human-in-the-Loop approval workflow.

## 🚀 Quick Start

### With Backend

From the project root, run both services at once:

```bash
./scripts/start-with-frontend.sh
```

This starts:

- Backend on `http://localhost:8000`
- Frontend on `http://localhost:8080`

### Frontend Only

```bash
cd src/frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:8080`

> **Note:** The frontend expects the backend to be running on `http://localhost:8000`. Vite proxy is configured to forward API requests.

## 📚 Documentation

- **[Frontend-Backend Integration Guide](../../docs/guides/frontend-backend-integration.md)** - Complete integration documentation
- **[Integration Summary](../../docs/FRONTEND-INTEGRATION.md)** - Quick overview of changes

## ✨ Features

- **Real-time SSE Streaming** - Character-by-character message streaming from backend
- **Multi-Agent Chat** - Interactive conversation with multiple specialized agents
- **HITL Approval Flow** - Human approval prompts for sensitive operations
- **Model Selection** - Switch between Magentic Fleet and Reflection & Retry workflows
- **Type-Safe API** - Full TypeScript integration with backend APIs
- **Modern UI** - Built with shadcn/ui components and Tailwind CSS

## 🛠️ Project Info

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the development server with auto-reloading and an instant preview.
npm run dev
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS
