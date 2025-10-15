import React, { useState, useRef } from "react";
import "./Auth.css";
import { loginUser, registerUser } from "./api";
import HCaptcha from "@hcaptcha/react-hcaptcha";

export default function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login"); // "login" or "register"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hcaptchaToken, setHcaptchaToken] = useState("");
  const hcaptchaRef = useRef();
  const SITE_KEY = process.env.REACT_APP_HCAPTCHA_SITE_KEY;
    if (!SITE_KEY) {
        console.error("REACT_APP_HCAPTCHA_SITE_KEY is not set in environment variables.");
    }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await loginUser(username, password);
        onAuth && onAuth();
      } else {
        if (!hcaptchaToken) {
          setError("Please complete the hCaptcha.");
          setLoading(false);
          return;
        }
        await registerUser(username, password, hcaptchaToken);
        setMode("login");
        setError("Registration successful! Please log in.");
        setHcaptchaToken("");
        if (hcaptchaRef.current) hcaptchaRef.current.resetCaptcha();
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
        {mode === "register" && (
          <div style={{ margin: "16px 0" }}>
            <HCaptcha
              sitekey={SITE_KEY}
              onVerify={token => setHcaptchaToken(token)}
              ref={hcaptchaRef}
            />
          </div>
        )}
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
