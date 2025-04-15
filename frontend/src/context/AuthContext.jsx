import { createContext, useContext, useState } from "react";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);

  const login = (username, password, navigate) => {
    if (username === "admin" && password === "admin") {
      setUser({ role: "admin" });
      navigate("/admin");
    } else if (username === "manager" && password === "manager") {
      setUser({ role: "manager" });
      navigate("/manager");
    } else {
      alert("Invalid username or password");
    }
  };

  const logout = (navigate) => {
    setUser(null);
    navigate("/");
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
