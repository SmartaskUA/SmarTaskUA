import { createContext, useContext } from "react";

// Kept apart from AuthProvider so AuthContext.jsx exports only a component,
// which is what React Fast Refresh needs to hot-reload it.
export const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);
