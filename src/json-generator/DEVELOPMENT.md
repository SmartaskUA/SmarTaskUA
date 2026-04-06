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

- **React 18**: UI framework
- **Vite 5**: Build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **DaisyUI**: Component library for Tailwind
- **React Router**: Client-side routing
- **Axios**: HTTP client for API calls

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

## Schema v2.2 Features

The JSON Generator now supports schema v2.2, which includes:

### Time Window Constraints (Allen Interval Algebra)
New constraint types in `schedule_input.csv`:
- `EQUALS:HH:MM-HH:MM` - Employee must work exactly this time range
- `INCLUDE:HH:MM-HH:MM` - Employee must cover this entire range minimum (can extend)
- `EXCEPT:HH:MM-HH:MM` - Employee unavailable during this time window

### Standard vs Custom Constraints
- **Standard** (always valid): `VAC` (vacation), `NOT` (unavailable)
- **Custom** (must be defined in `scheduleInput.markingTypes`): DL, DLF, DLV, etc.

### Constraints Configuration
- **Hard Constraints**: max_consecutive_days, min_rest_hours, vacation_block, etc.
- **Soft Constraints**: min_coverage, balance_workload, with penalty weights
- **Advanced**: Day-off swapping, break rules (requires `useAdvancedConstraints` feature flag)

See `schema_v2.2/FORMAT.md` and `schema_v2.2/README.md` for complete details.

## Next Steps

Now that the infrastructure is ready, you can:

1. **Design the UI** - Sketch out the pages and components you need
2. **Create page components** - Build the forms and interfaces
3. **Implement JSON generation** - Add logic to create schema v2.2 files
4. **Add CSV generation** - Create schedule_input.csv and demand.csv
5. **Integrate with API** - Connect to backend services if needed
6. **Add validation** - Use the schema validator for generated files

Happy coding! 🚀
