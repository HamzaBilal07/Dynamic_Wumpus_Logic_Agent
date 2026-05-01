# Dynamic Wumpus Logic Agent

Python web app for a Wumpus World-style knowledge-based pathfinding agent.

## Run locally

```powershell
python server.py
```

Then open `http://127.0.0.1:8000` in a browser.

No external Python packages are required. The app uses only the Python standard library.

## Deploy on Vercel

This project is ready for Vercel's Python backend runtime.

### Option 1: Deploy from GitHub

1. Push the `DynamicWumpusAgent` folder to a GitHub repository.
2. In Vercel, create a new project and import that repository.
3. Set the project root to `DynamicWumpusAgent` if the repository contains other folders.
4. Keep the framework preset as `Other`.
5. Deploy.

### Option 2: Deploy from the Vercel CLI

```powershell
cd "C:\Users\mhamz\OneDrive - FAST National University\Python Files\DynamicWumpusAgent"
vercel
```

For production:

```powershell
vercel --prod
```

## Vercel files

- `api/index.py` is the Python serverless function.
- `app.py` is the Vercel Flask entrypoint.
- `vercel_app.py` renders the app and handles form actions.
- `vercel.json` is intentionally minimal so Vercel auto-detects `app.py`.
- `public/styles.css` is the deployed stylesheet.
- `.python-version` pins Python `3.12`.

## What it implements

- Dynamic grid sizing from 2x2 to 8x8.
- Random pits and one hidden Wumpus at the start of each episode.
- Breeze and stench percepts generated from adjacent hazards.
- A propositional logic knowledge base with `TELL` statements.
- CNF conversion by eliminating implications, moving negation inward, and distributing OR over AND.
- Resolution refutation for `ASK` queries before the agent moves into an unvisited cell.
- Grid visualization for safe, unknown, visited, and confirmed hazard cells.
- Dashboard metrics for total resolution inference steps, current percepts, KB clause count, and recent proof trace.
