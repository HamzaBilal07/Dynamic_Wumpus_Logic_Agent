# Dynamic Wumpus Logic Agent

A web-based Knowledge-Based Agent for a dynamic Wumpus World grid. The agent receives percepts as it moves, updates a propositional logic knowledge base, converts formulas to CNF, and uses resolution refutation to decide whether neighboring cells are safe.

## Live Demo

You can try the deployed project here:

```text
PASTE_YOUR_VERCEL_LINK_HERE
```

Replace the placeholder above with the Vercel deployment link.

## Features

- Dynamic grid sizing from 2x2 to 8x8.
- Random pit and Wumpus placement for every new episode.
- Breeze percepts near pits and stench percepts near the Wumpus.
- Propositional logic knowledge base with `TELL` updates.
- CNF conversion for logical formulas.
- Automated resolution refutation for `ASK` queries.
- Agent moves only into cells that are proven safe.
- Visual grid showing safe, unknown, visited, and confirmed hazard cells.
- Dashboard for current percepts, inference steps, KB clause count, recent `TELL` statements, and resolution trace.

## Run Locally

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/Dynamic_Wumpus_Logic_Agent.git
cd Dynamic_Wumpus_Logic_Agent
```

Run the local Python server:

```bash
python server.py
```

Open this URL in your browser:

```text
http://127.0.0.1:8000
```

If port `8000` is already in use, the app will automatically choose the next available local port and print it in the terminal.

## Run the Vercel/Flask Version Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Flask app:

```bash
flask --app app run
```

Open:

```text
http://127.0.0.1:5000
```

## How to Use

1. Choose the number of rows and columns.
2. Set the pit density.
3. Click `New episode` to generate a new Wumpus World.
4. Click `Step agent` to let the agent make one logic-based move.
5. Click `Auto run` to let the agent continue until it is blocked, wins, or reaches a hazard.
6. Watch the dashboard to see the percepts, inference steps, KB updates, and resolution trace.

## Project Structure

```text
DynamicWumpusAgent/
|-- app.py              # Flask entrypoint used by Vercel
|-- server.py           # Local Python HTTP server
|-- vercel_app.py       # Shared HTML rendering and request handling
|-- wumpus_logic.py     # Wumpus world, KB, CNF, and resolution logic
|-- vercel.json         # Vercel configuration
|-- requirements.txt    # Flask dependency for Vercel/local Flask run
|-- public/
|   `-- styles.css      # CSS served on Vercel
|-- styles.css          # CSS used by the local server
`-- api/
    `-- index.py        # Compatibility handler for Vercel-style Python functions
```

## Logic Overview

When the agent visits a cell, it receives percepts and updates the KB. For example, a breeze rule can be represented as:

```text
B(2,1) <=> P(2,2) OR P(3,1) OR P(1,1)
```

Before moving, the agent asks whether a neighboring cell is safe by proving:

```text
~Pit(cell) AND ~Wumpus(cell)
```

The inference engine converts formulas into CNF and applies resolution refutation. If the negation of the query causes a contradiction, the query is considered proven.

## Deploy on Vercel

This project is ready for Vercel's Python backend runtime.

1. Push this repository to GitHub.
2. Import the repository in Vercel.
3. Use framework preset `Other`.
4. Leave the root directory as `./` if these files are in the repository root.
5. If these files are inside a folder, set the root directory to that folder.
6. Deploy.

The deployed app uses `app.py` as the Flask entrypoint and serves the visual interface through Vercel.

## Requirements

- Python 3.12 recommended.
- No database is required.
- For the local `server.py` version, only the Python standard library is needed.
- For the Flask/Vercel version, install dependencies from `requirements.txt`.

## License

This project is intended for educational use.
