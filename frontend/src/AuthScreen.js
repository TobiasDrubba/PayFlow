import React, { useState } from "react";
import "./Auth.css";
import { loginUser, registerUser } from "./api";

export default function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login"); // "login" or "register"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await loginUser(username, password);
        onAuth && onAuth();
      } else {
        await registerUser(username, password);
        setMode("login");
        setError("Registration successful! Please log in.");
      }
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  return (
    <div className="auth-container">
      <div className="auth-title">
        {mode === "login" ? "Sign In" : "Create Account"}
      </div>
      <div className="auth-subtitle">
        {mode === "login"
          ? "Welcome back! Please enter your credentials."
          : "Create your account to start tracking your payments."}
      </div>
      {error && <div className="auth-error">{error}</div>}
      <form className="auth-form" onSubmit={handleSubmit}>
        <input
          className="auth-input"
          type="text"
          placeholder="Username"
          autoComplete="username"
          value={username}
          onChange={e => setUsername(e.target.value)}
          disabled={loading}
          required
        />
        <input
          className="auth-input"
          type="password"
          placeholder="Password"
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          value={password}
          onChange={e => setPassword(e.target.value)}
          disabled={loading}
          required
        />
        <button className="auth-btn" type="submit" disabled={loading}>
          {loading
            ? (mode === "login" ? "Signing in..." : "Registering...")
            : (mode === "login" ? "Sign In" : "Register")}
        </button>
      </form>
      <div className="auth-switch">
        {mode === "login" ? (
          <>
            Don't have an account?
            <span onClick={() => { setMode("register"); setError(""); }}>Register</span>
          </>
        ) : (
          <>
            Already have an account?
            <span onClick={() => { setMode("login"); setError(""); }}>Sign In</span>
          </>
        )}
      </div>
    </div>
  );
}

