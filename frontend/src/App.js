import React, { useState, useEffect } from "react";
import PaymentsTable from "./PaymentsTable";
import AuthScreen from "./AuthScreen";
import { Container } from "@mui/material";

// Helper to decode JWT and check expiration
function isTokenValid(token) {
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (!payload.exp) return false;
    // exp is in seconds since epoch
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

function isAuthenticated() {
  const token = localStorage.getItem("token");
  return !!token && isTokenValid(token);
}

function App() {
  const [authed, setAuthed] = useState(isAuthenticated());

  useEffect(() => {
    const check = () => {
      const token = localStorage.getItem("token");
      if (!token || !isTokenValid(token)) {
        localStorage.removeItem("token");
        setAuthed(false);
      } else {
        setAuthed(true);
      }
    };
    check();
    // Listen for storage changes (e.g. logout in another tab)
    window.addEventListener("storage", check);
    return () => window.removeEventListener("storage", check);
  }, []);

  return (
    <Container>
      {authed ? (
        <PaymentsTable />
      ) : (
        <AuthScreen onAuth={() => setAuthed(true)} />
      )}
    </Container>
  );
}

export default App;
