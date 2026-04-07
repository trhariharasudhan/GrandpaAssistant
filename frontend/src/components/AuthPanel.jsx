export default function AuthPanel({
  authState,
  authForm,
  setAuthForm,
  authBusy,
  authError,
  onSubmit,
}) {
  const mode = authForm.mode || (authState?.bootstrap?.has_users ? "login" : "register");
  const hasUsers = Boolean(authState?.bootstrap?.has_users);
  const title = hasUsers ? "Sign in to Grandpa Assistant" : "Create the first admin account";
  const subtitle = hasUsers
    ? "Use your assistant account to unlock chat, commands, and dashboard controls."
    : "The first account becomes the admin account for this desktop assistant.";

  return (
    <div className="auth-shell">
      <div className="auth-panel">
        <div className="auth-hero">
          <span className="auth-kicker">Grandpa Assistant</span>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>

        <div className="auth-mode-switch">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => setAuthForm((current) => ({ ...current, mode: "login" }))}
          >
            Login
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => setAuthForm((current) => ({ ...current, mode: "register" }))}
          >
            Register
          </button>
        </div>

        <form className="auth-form" onSubmit={onSubmit}>
          <label>
            <span>Username</span>
            <input
              type="text"
              value={authForm.username || ""}
              onChange={(event) => setAuthForm((current) => ({ ...current, username: event.target.value }))}
              placeholder="grandchild"
              autoComplete="username"
            />
          </label>

          {mode === "register" ? (
            <label>
              <span>Display Name</span>
              <input
                type="text"
                value={authForm.displayName || ""}
                onChange={(event) => setAuthForm((current) => ({ ...current, displayName: event.target.value }))}
                placeholder="Hari"
                autoComplete="name"
              />
            </label>
          ) : null}

          <label>
            <span>Password</span>
            <input
              type="password"
              value={authForm.password || ""}
              onChange={(event) => setAuthForm((current) => ({ ...current, password: event.target.value }))}
              placeholder="At least 8 characters"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </label>

          {authError ? <div className="auth-error">{authError}</div> : null}

          <button type="submit" className="auth-submit" disabled={authBusy}>
            {authBusy ? "Please wait..." : mode === "login" ? "Login" : "Create account"}
          </button>
        </form>

        <div className="auth-hints">
          <strong>What this unlocks</strong>
          <span>Saved chat archive, audit history, role-aware access, and production-style session handling.</span>
        </div>
      </div>
    </div>
  );
}
