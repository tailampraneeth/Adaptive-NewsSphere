# Frontend Operations Manual

This guide describes how to configure, run, and test the React 19 + Vite frontend of the Adaptive NewsSphere platform.

## Features

- **Personalized News Feed:** Renders story clusters ranked by recommendation scoring weights and freshness decay.
- **Fact-Checking Consensus:** Visualizes claims agreement scores, disputed facts, and supporting source attributions.
- **Hallucination-Free Chat:** Grounded conversational assistant utilizing streaming SSE tokens.
- **Offline Analytics:** Tracks local dwell time, active sessions, and usage metrics privately in browser storage.
- **Tranquil Aesthetics:** Custom calming theme using HSL color variables with CSS glassmorphism features.

## Getting Started

### Prerequisites

- Node.js (version 18 or higher recommended)
- npm or yarn

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

### Running Locally (Development Mode)

Vite is preconfigured with an API and WebSockets proxy to delegate requests to the local FastAPI backend automatically.

Start the local Vite dev server:
```bash
npm run dev
```
The application will boot at `http://localhost:3000`.

### Production Build

Compile optimized production bundle assets:
```bash
npm run build
```
The compiled output is saved to the `frontend/dist` directory.

### Running Tests

Execute Vitest test suites deterministically:
```bash
npm run test
```

For watch mode:
```bash
npm run test:watch
```
