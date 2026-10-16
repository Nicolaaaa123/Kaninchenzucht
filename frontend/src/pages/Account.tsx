import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { UserLimits } from "../components/UserLimits";
import { useAsync } from "../hooks/useAsync";
import { useAuth } from "../hooks/useAuth";

export function Account() {
  const { user, logout } = useAuth();
  const [mergeCode, setMergeCode] = useState("");
  const [mergeError, setMergeError] = useState<string | null>(null);
  const [mergeSuccess, setMergeSuccess] = useState(false);
  const [merging, setMerging] = useState(false);

  const users = useAsync(() => (user?.is_admin ? api.auth.listUsers() : Promise.resolve(null)), [user?.is_admin]);
  const usageOverview = useAsync(() => (user?.is_admin ? api.usage.overview() : Promise.resolve(null)), [user?.is_admin]);
  const myUsage = useAsync(() => api.usage.me(), []);

  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [newJoinMyTenant, setNewJoinMyTenant] = useState(false);
  const [newScanLimit, setNewScanLimit] = useState("10");
  const [newChatLimit, setNewChatLimit] = useState("30");
  const [createError, setCreateError] = useState<string | null>(null);
  const [createdUser, setCreatedUser] = useState<{ username: string; password: string; invite_code: string } | null>(
    null,
  );
  const [creating, setCreating] = useState(false);

  const [resettingUserId, setResettingUserId] = useState<string | null>(null);
  const [resetPasswordValue, setResetPasswordValue] = useState("");
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetSuccessUsername, setResetSuccessUsername] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);

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
        join_my_tenant: newJoinMyTenant,
        // leer = unbegrenzt, 0 = aus
        scan_limit: newScanLimit.trim() === "" ? null : Number(newScanLimit),
        chat_limit: newChatLimit.trim() === "" ? null : Number(newChatLimit),
      });
      setCreatedUser({ username: created.username, password: newPassword, invite_code: created.invite_code });
      setNewUsername("");
      setNewPassword("");
      setNewDisplayName("");
      setNewIsAdmin(false);
      users.reload();
      usageOverview.reload();
    } catch (err) {
      setCreateError((err as Error).message);
    } finally {
      setCreating(false);
    }
  }

  function startReset(userId: string) {
    setResettingUserId(userId);
    setResetPasswordValue("");
    setResetError(null);
    setResetSuccessUsername(null);
  }

  async function handleResetPassword(userId: string, username: string) {
    if (!resetPasswordValue) {
      setResetError("Neues Passwort darf nicht leer sein.");
      return;
    }
    setResetting(true);
    setResetError(null);
    try {
      await api.auth.resetPassword(userId, resetPasswordValue);
      setResettingUserId(null);
      setResetSuccessUsername(username);
    } catch (err) {
      setResetError((err as Error).message);
    } finally {
      setResetting(false);
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
        {myUsage.data && (
          <p className="hint" style={{ marginTop: 8 }}>
            KI-Kontingent diesen Monat — Scans:{" "}
            {myUsage.data.scan_limit === null
              ? "unbegrenzt"
              : myUsage.data.scan_limit === 0
                ? "nicht freigeschaltet"
                : `${myUsage.data.scan_used} von ${myUsage.data.scan_limit} genutzt`}
            {" · "}KI-Anfragen:{" "}
            {myUsage.data.chat_limit === null
              ? "unbegrenzt"
              : myUsage.data.chat_limit === 0
                ? "nicht freigeschaltet"
                : `${myUsage.data.chat_used} von ${myUsage.data.chat_limit} genutzt`}
            .
          </p>
        )}
        <div className="toolbar" style={{ marginTop: 12, marginBottom: 0 }}>
          <button className="btn secondary" onClick={logout}>
            Abmelden
          </button>
          <Link className="btn secondary" to="/datenschutz">
            Datenschutz
          </Link>
        </div>
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
            Legt ein neues Login an. Ohne Haken bekommt die Person einen eigenen, leeren Bestand (mit den
            Standard-Rassen), den nur sie sieht. Mit dem Haken "Im selben Bestand wie ich" arbeitet sie direkt
            in deinem Bestand.
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
                <label htmlFor="new-join" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <input
                    id="new-join"
                    type="checkbox"
                    checked={newJoinMyTenant}
                    onChange={(e) => setNewJoinMyTenant(e.target.checked)}
                    style={{ width: "auto" }}
                  />
                  Im selben Bestand wie ich
                </label>
              </div>
              <div className="field">
                <label htmlFor="new-scan-limit">Scans pro Monat</label>
                <input
                  id="new-scan-limit"
                  type="number"
                  min={0}
                  inputMode="numeric"
                  placeholder="unbegrenzt"
                  value={newScanLimit}
                  onChange={(e) => setNewScanLimit(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="new-chat-limit">KI-Anfragen pro Monat</label>
                <input
                  id="new-chat-limit"
                  type="number"
                  min={0}
                  inputMode="numeric"
                  placeholder="unbegrenzt"
                  value={newChatLimit}
                  onChange={(e) => setNewChatLimit(e.target.value)}
                />
                <span className="hint">Leer = unbegrenzt, 0 = nicht freigeschaltet. Jederzeit änderbar.</span>
              </div>
            </div>
            <button className="btn" type="submit" disabled={creating}>
              {creating ? "Lege an…" : "Login anlegen"}
            </button>
          </form>

          <h3 style={{ marginTop: 20 }}>Bestehende Logins</h3>
          {resetSuccessUsername && (
            <div
              className="card section"
              style={{ background: "var(--color-success-soft)", color: "var(--color-success)", marginBottom: 12 }}
            >
              Passwort für "{resetSuccessUsername}" wurde geändert. Die Person wurde automatisch überall
              abgemeldet und muss sich mit dem neuen Passwort neu anmelden.
            </div>
          )}
          <div className="list">
            {users.data?.map((u) => (
              <div key={u.id} className="card" style={{ marginBottom: 8, padding: "10px 14px" }}>
                <div className="list-item" style={{ padding: 0 }}>
                  <span>
                    {u.username} {u.display_name ? `· ${u.display_name}` : ""} {u.is_admin ? "· Admin" : ""}
                  </span>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <code>{u.invite_code}</code>
                    <button
                      type="button"
                      className="btn secondary small"
                      onClick={() => (resettingUserId === u.id ? setResettingUserId(null) : startReset(u.id))}
                    >
                      Passwort setzen
                    </button>
                  </div>
                </div>
                {usageOverview.data?.find((x) => x.user_id === u.id) && (
                  <UserLimits row={usageOverview.data.find((x) => x.user_id === u.id)!} onSaved={usageOverview.reload} />
                )}
                {resettingUserId === u.id && (
                  <div className="toolbar" style={{ marginTop: 10, marginBottom: 0 }}>
                    {resetError && <div className="error-banner">{resetError}</div>}
                    <input
                      type="text"
                      placeholder="Neues Passwort"
                      value={resetPasswordValue}
                      onChange={(e) => setResetPasswordValue(e.target.value)}
                      style={{ flex: 1 }}
                      autoFocus
                    />
                    <button
                      className="btn"
                      type="button"
                      disabled={resetting}
                      onClick={() => handleResetPassword(u.id, u.username)}
                    >
                      {resetting ? "Speichere…" : "Speichern"}
                    </button>
                    <button
                      className="btn secondary"
                      type="button"
                      onClick={() => setResettingUserId(null)}
                      disabled={resetting}
                    >
                      Abbrechen
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
