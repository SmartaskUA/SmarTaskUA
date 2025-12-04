# Frontend Service

## Overview

React-based web application that provides the user interface for the SmarTask scheduling system. Allows managers and administrators to create schedules, manage employees, configure constraints, and visualize schedule comparisons.

## Technology Stack

- **React 18** with hooks
- **Vite** for fast development and building
- **TailwindCSS** for styling
- **ESLint** for code quality

## Project Structure

```
src/
├── Admin/                       # Administrator pages and components
├── Manager/                     # Manager pages and components
├── components/                  # Reusable UI components
├── context/                     # React Context (e.g., AuthContext)
├── login/                       # Login pages
├── assets/                      # Images, icons, static files
├── styles/                      # CSS files
├── App.jsx                      # Main application component
└── main.jsx                     # Application entry point

public/                          # Static assets served directly
```

## Key Features

- **Schedule Generation:** Configure and trigger schedule creation
- **Schedule Visualization:** View and compare generated schedules
- **Employee Management:** Add, edit, and manage employee profiles
- **Vacation Management:** Import and manage vacation templates
- **Rules Configuration:** Define and modify scheduling constraints
- **Real-time Updates:** WebSocket notifications for task status
- **Authentication:** Login system with role-based access

## Development

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
# Access at http://localhost:5173
```

### Build for Production

```bash
npm run build
# Output in dist/ directory
```

### Lint Code

```bash
npm run lint
```

### Run with Docker

```bash
# From project root
make build-frontend
```

## Configuration

- **API Endpoint:** Configure in source code (usually points to `http://localhost:8081`)
- **Vite Config:** `vite.config.js`
- **Tailwind Config:** `tailwind.config.js`
- **ESLint Config:** `eslint.config.js`

## Access

- **URL:** http://localhost:5173/
- **Default Credentials:** manager/manager
