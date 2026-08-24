import { useState } from "react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { useAuth } from "../hooks/useAuth";

export function Account() {
  const { user, logout } = useAuth();
  const [mergeCode, setMergeCode] = useState("");
  const [mergeError, setMergeError] = useState<string | null>(null);
  const [mergeSuccess, setMergeSuccess] = useState(false);
  const [merging, setMerging] = useState(false);

  const users = useAsync(() => (user?.is_admin ? api.auth.listUsers() : Promise.resolve(null)), [user?.is_admin]);

  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createdUser, setCreatedUser] = useState<{ username: string; password: string; invite_code: string } | null>(
    null,
  );
  const [creating, setCreating] = useState(false);

  if (!user) return null;

  async function handleMerge(e: React.FormEvent) {
    e.preventDefault();
    if (!mergeCode.trim()) return;
    setMerging(true);
    setMergeError(null);
    setMergeSuccess(false);
    try {
      await api.auth.merge(mergeCode.trim());
      setMergeSuccess(true);
      setMergeCode("");
    } catch (err) {
      setMergeError((err as Error).message);
    } finally {
      setMerging(false);
    }
  }

  async function handleCreateUser(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);
    setCreatedUser(null);
    try {
      const created = await api.auth.createUser({
        username: newUsername.trim(),
        password: newPassword,
        display_name: newDisplayName.trim() || null,
        is_admin: newIsAdmin,
      });
      setCreatedUser({ username: created.username, password: newPassword, invite_code: created.invite_code });
      setNewUsername("");
      setNewPassword("");
      setNewDisplayName("");
      setNewIsAdmin(false);
      users.reload();
    } catch (err) {
      setCreateError((err as Error).message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <h1>Konto</h1>

      <div className="card section">
        <h2>Angemeldet als</h2>
        <table>
          <tbody>
            <tr>
              <th>Benutzername</th>
              <td>{user.username}</td>
            </tr>
            {user.display_name && (
              <tr>
                <th>Name</th>
                <td>{user.display_name}</td>
              </tr>
            )}
            <tr>
              <th>Rolle</th>
              <td>{user.is_admin ? "Administrator" : "Mitglied"}</td>
            </tr>
            <tr>
              <th>Dein Einlade-Code</th>
              <td>
                <code style={{ fontSize: "1.05rem", fontWeight: 700 }}>{user.invite_code}</code>
              </td>
            </tr>
          </tbody>
        </table>
        <p className="hint" style={{ marginTop: 8 }}>
          Gib diesen Code an eine andere Person weiter, damit sie euren Zuchtbestand mit ihrem
          eigenen zusammenschliessen kann (unten bei ihr/über "Bestand zusammenschliessen").
        </p>
        <button className="btn secondary" style={{ marginTop: 12 }} onClick={logout}>
          Abmelden
        </button>
      </div>

      <div className="card section">
        <h2>Bestand zusammenschliessen</h2>
        <p className="hint" style={{ marginBottom: 12 }}>
          Gib den Einlade-Code eines anderen Logins ein, um dessen Tiere, Ställe, Rassen, Futter
          und Würfe dauerhaft mit deinem Bestand zusammenzuführen. Ab dann sehen und bearbeiten
          beide Logins dieselben Daten. Das lässt sich nicht rückgängig machen.
        </p>
        {mergeError && <div className="error-banner">{mergeError}</div>}
        {mergeSuccess && (
          <div className="card section" style={{ background: "var(--color-success-soft)", color: "var(--color-success)" }}>
            Zusammengeschlossen — ihr teilt euch jetzt denselben Bestand.
          </div>
        )}
        <form className="toolbar" onSubmit={handleMerge} style={{ marginBottom: 0 }}>
          <input
            type="text"
            placeholder="Einlade-Code, z.B. A1B2C3D4"
            value={mergeCode}
            onChange={(e) => setMergeCode(e.target.value.toUpperCase())}
            style={{ flex: 1 }}
          />
          <button className="btn" type="submit" disabled={merging}>
            {merging ? "Führe zusammen…" : "Zusammenschliessen"}
          </button>
        </form>
      </div>

      {user.is_admin && (
        <div className="card section">
          <h2>Neues Login anlegen</h2>
          <p className="hint" style={{ marginBottom: 12 }}>
            Legt ein neues Login mit einem eigenen, leeren Bestand an — die Person kann sich danach
            über den Einlade-Code mit eurem Bestand zusammenschliessen.
          </p>
          {createError && <div className="error-banner">{createError}</div>}
          {createdUser && (
            <div
              className="card section"
              style={{ background: "var(--color-success-soft)", color: "var(--color-success)" }}
            >
              Login "{createdUser.username}" angelegt. Passwort: <strong>{createdUser.password}</strong> — bitte
              jetzt sicher weitergeben (wird nicht nochmal angezeigt).
            </div>
          )}
          <form onSubmit={handleCreateUser}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="new-username">Benutzername</label>
                <input
                  id="new-username"
                  type="text"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="new-password">Passwort</label>
                <input
                  id="new-password"
                  type="text"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="new-display-name">Name (optional)</label>
                <input
                  id="new-display-name"
                  type="text"
                  value={newDisplayName}
                  onChange={(e) => setNewDisplayName(e.target.value)}
                />
              </div>
              <div className="field" style={{ justifyContent: "flex-end" }}>
                <label htmlFor="new-is-admin" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <input
                    id="new-is-admin"
                    type="checkbox"
                    checked={newIsAdmin}
                    onChange={(e) => setNewIsAdmin(e.target.checked)}
                    style={{ width: "auto" }}
                  />
                  Administrator
                </label>
              </div>
            </div>
            <button className="btn" type="submit" disabled={creating}>
              {creating ? "Lege an…" : "Login anlegen"}
            </button>
          </form>

          <h3 style={{ marginTop: 20 }}>Bestehende Logins</h3>
          <div className="list">
            {users.data?.map((u) => (
              <div className="list-item" key={u.id}>
                <span>
                  {u.username} {u.display_name ? `· ${u.display_name}` : ""} {u.is_admin ? "· Admin" : ""}
                </span>
                <code>{u.invite_code}</code>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
