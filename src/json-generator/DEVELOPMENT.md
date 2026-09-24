# JSON Generator - Development Guide

## Quick Start

### Local Development (with Docker)

1. **Start all services including json-generator:**
   ```bash
   cd /home/roldao/Desktop/SmarTask/SmarTaskUA/infra
   docker-compose up json-generator
   ```

2. **Access the application:**
   - Via nginx (recommended): http://localhost/json-gen
   - Direct (for debugging): http://localhost:5174

### Start Everything with Nginx

```bash
cd /home/roldao/Desktop/SmarTask/SmarTaskUA/infra
docker-compose up
```

This will start:
- Main frontend at http://localhost/ (via nginx)
- JSON Generator at http://localhost/json-gen (via nginx)
- API at http://localhost/api (via nginx)
- All backend services (MongoDB, RabbitMQ, scheduler, analyzer)

### Local Development (without Docker)

If you want to develop without Docker:

```bash
cd /home/roldao/Desktop/SmarTask/SmarTaskUA/src/json-generator
npm install
npm run dev
```

**Note:** You'll need to update `vite.config.js` to change `base: '/json-gen/'` to `base: '/'` for local development without nginx.

## Project Structure

```
src/json-generator/
├── src/
│   ├── components/      # Reusable React components
│   ├── pages/          # Page components (routes)
│   ├── utils/          # Utility functions
│   ├── App.jsx         # Main app component with routing
│   ├── main.jsx        # Entry point
│   └── index.css       # Global styles (Tailwind)
├── public/             # Static assets
├── index.html          # HTML template
├── vite.config.js      # Vite configuration
├── tailwind.config.js  # Tailwind + DaisyUI configuration
└── package.json        # Dependencies

infra/
├── docker/
│   └── json-generator/
│       └── Dockerfile   # Docker configuration
└── docker-compose.yml   # Service orchestration
```

## Technology Stack

- **React 18** + **Vite 7**: UI framework and dev server
- **Material-UI (MUI) v7** + **@mui/x-date-pickers**: component library and theming
- **Tailwind CSS**: utility classes (used alongside MUI for layout/spacing)
- **React Router 6**: client-side routing (base path `/json-gen/`)
- **Axios**: HTTP client (reserved for future API integration)
- **ajv**: JSON Schema validation against the vendored v4 schema
- **PapaParse**: CSV parsing (employees import, demand, schedule input)
- **JSZip** + **file-saver**: bundle `problem.json` + CSVs, read imported ZIPs, trigger downloads
- **date-fns**: date arithmetic and formatting

## Development Workflow

### Creating New Pages

1. Create a new file in `src/pages/`:
   ```jsx
   // src/pages/MyNewPage.jsx
   import React from 'react'

   function MyNewPage() {
     return (
       <div className="container mx-auto p-8">
         <h1 className="text-2xl font-bold">My New Page</h1>
       </div>
     )
   }

   export default MyNewPage
   ```

2. Add the route in `src/App.jsx`:
   ```jsx
   import MyNewPage from './pages/MyNewPage'

   // In the Routes component:
   <Route path="/my-new-page" element={<MyNewPage />} />
   ```

3. Access it at: http://localhost/json-gen/my-new-page

### Creating Components

Place reusable components in `src/components/`:

```jsx
// src/components/MyComponent.jsx
import React from 'react'

function MyComponent({ title, children }) {
  return (
    <div className="card bg-base-100 shadow-xl">
      <div className="card-body">
        <h2 className="card-title">{title}</h2>
        {children}
      </div>
    </div>
  )
}

export default MyComponent
```

### Using DaisyUI Components

DaisyUI provides pre-built components. Examples:

```jsx
// Button
<button className="btn btn-primary">Click Me</button>

// Card
<div className="card bg-base-100 shadow-xl">
  <div className="card-body">
    <h2 className="card-title">Card Title</h2>
    <p>Card content</p>
  </div>
</div>

// Alert
<div className="alert alert-info">
  <span>Info message</span>
</div>

// Form Input
<input type="text" className="input input-bordered w-full" />
```

See more at: https://daisyui.com/components/

## Environment Variables

Create a `.env` file (based on `.env.example`):

```bash
cp .env.example .env
```

Access in code:
```javascript
const apiUrl = import.meta.env.VITE_API_URL
```

## API Integration

Example API call:

```javascript
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

async function fetchData() {
  try {
    const response = await axios.get(`${API_URL}/endpoint`)
    return response.data
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}
```

## Nginx Routing

The nginx configuration routes requests as follows:

- `http://localhost/` → Main frontend (port 5173)
- `http://localhost/json-gen/` → JSON Generator (port 5174)
- `http://localhost/api/` → API service (port 8081)

## Building for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

## Troubleshooting

### Port 5174 already in use
```bash
# Find and kill the process
lsof -ti:5174 | xargs kill -9
```

### Docker rebuild needed
```bash
docker-compose build json-generator
docker-compose up json-generator
```

### Vite HMR not working
Make sure `CHOKIDAR_USEPOLLING=1` is set in docker-compose.yml (already configured).

### Can't access via nginx
1. Check nginx is running: `docker ps | grep nginx`
2. Check nginx logs: `docker logs nginx`
3. Verify all services are healthy: `docker-compose ps`

## Schema v4.0

The wizard targets schema v4.0 only (`json_generation/schema_v4/`). All schema logic lives in
`src/v4/`; see the README for the module map. Things that are easy to get wrong:

- **Units.** Contracts state `workMinutesPerDay` in minutes; `schedule_input.csv` cells are hours
  (`8` = 480 min, a cell above 24 is rejected as unconverted minutes).
- **The grid.** Every duration and boundary must be a multiple of `timeGrid.slotMinutes`.
- **The demand triple.** No ordering is enforced between `minimum`, `ideal` and `estimated`; `0`
  means unset and `minimum` may be fractional. Do not add an ordering check.
- **Grains.** `days_demand.csv` and `periods_demand.csv` share a header but not a unit — always
  pass the grain to `core.readDemand`, never sniff it.
- **Day-off codes.** There are no implicit codes; every one must be declared with its kind.
- **Parity.** `src/v4/validate.js` mirrors the Python validator message for message. When the
  Python side changes, update the port and `src/v4/parity.test.js` together.
- **The vendored schema.** `schema_v4/schema-v4-input.json` must stay byte-identical to
  `json_generation/schema_v4/schemas/schema-v4-input.json`; copy it over, never edit it.

Verify a change end to end:

```bash
npm test
npx vite-node scripts/validate-with-python.mjs   # needs python3; runs the canonical validator
```

## Status

v4.0 migration complete: nine steps, a client-side ZIP (`problem.json` + three demand CSVs +
`schedule_input.csv` + optional `schedules.csv`), and import of existing v4 bundles. v2.x
projects and localStorage saves are deprecated and are discarded on load. There is no backend
submission yet, and the solvers still read v2.2/v2.6 — they need migrating before they can
consume this output.
