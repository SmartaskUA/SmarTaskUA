# JSON Generator Frontend

A React + Vite frontend application for generating JSON + CSV pairs for schema v2.2.

## Features

- Generate problem.json files with contract definitions
- Create schedule_input.csv with work requirements and constraints
- Generate demand.csv with coverage requirements
- Interactive UI for schema v2.2 format

## Tech Stack

- React 18
- Vite 5
- Tailwind CSS
- DaisyUI
- React Router

## Development

```bash
npm install
npm run dev
```

The app will be available at `http://localhost:5174` (or via nginx at `http://localhost/json-gen`)

## Docker

The application is containerized and runs as part of the SmarTask infrastructure.

```bash
# From the project root
docker-compose up json-generator
```

## Integration

This frontend is designed to be:
- Standalone for now (separate Docker service)
- Prepared for future integration into the main frontend
- Accessible via nginx reverse proxy at `/json-gen`
