# Grandpa Assistant React UI

This frontend is a React + Vite UI for Grandpa Assistant.

## Run

```powershell
cd frontend
npm install
npm run dev
```

The Python backend should also be running:

```powershell
python main.py
```

## Quick launch

From the project root you can use:

```powershell
start_react_ui.cmd
```

Or to open backend, frontend, and browser together:

```powershell
start_react_full.cmd
```

Or to open backend, frontend, and Electron desktop shell together:

```powershell
start_react_desktop.cmd
```

If the Python backend is already running, you can launch frontend only:

```powershell
start_react_frontend.cmd
start_react_electron.cmd
```

## Current bridge

- fetches assistant UI state from `http://127.0.0.1:8765/api/ui-state`
- sends text commands to `http://127.0.0.1:8765/api/command`
- starts/stops voice mode through the local API
- updates startup settings through the local API

## Packaging next

Electron starter is now included.

Files:

- `electron/main.cjs`
- `electron/preload.cjs`

Install dependencies:

```powershell
cd frontend
npm install
```

Run desktop shell in dev mode:

```powershell
npm run dev
npm run electron:dev
```

Current direction:

- React + Vite frontend
- local Python backend API
- Electron wrapper for desktop app feel
