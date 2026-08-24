import { useState } from "react";
import { useAuth } from "../hooks/useAuth";

export function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="card login-card" onSubmit={handleSubmit}>
        <div className="login-logo">
          <span className="logo-mark">K</span>
          Kaninchenzucht
        </div>
        {error && <div className="error-banner">{error}</div>}
        <div className="field">
          <label htmlFor="login-username">Benutzername</label>
          <input
            id="login-username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            required
          />
        </div>
        <div className="field">
          <label htmlFor="login-password">Passwort</label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button className="btn" type="submit" disabled={submitting} style={{ width: "100%" }}>
          {submitting ? "Anmelden…" : "Anmelden"}
        </button>
        <p className="hint" style={{ marginTop: 12, textAlign: "center" }}>
          Logins werden vom Administrator vergeben.
        </p>
      </form>
    </div>
  );
}
