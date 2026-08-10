# Tortoise WoW launcher dashboard

The launcher is a Windows desktop dashboard for the organized server runtime.
It manages MariaDB, `realmd`, the AI sidecar, and `mangosd` without placing
executables, DLLs, PID files, or logs in the server root.

## Launch

After preparing the sidecar environment once:

```powershell
cd E:\Games\TurtleWoW\Server\dev\sidecar
uv sync
```

Double-click `dev\launcher\run-dashboard.cmd`, or run:

```powershell
dev\sidecar\.venv\Scripts\python.exe dev\launcher\main.py
```

The normal cloud-provider setup is an ignored `dev\sidecar\.env` copied from
`.env.example`. The sidecar reads that file itself, so the dashboard and other
server processes never receive its provider key.

Operators using a service manager, container secret, or another environment
injection mechanism can instead put provider variables in the dashboard process
environment:

```powershell
$env:TORTOISE_SIDECAR_PROVIDER = "openrouter"
$env:TORTOISE_LLM_API_KEY = "<provider key>"
dev\sidecar\.venv\Scripts\python.exe dev\launcher\main.py
```

When environment injection is used, the launcher removes known provider
credential variables from MariaDB, `realmd`, `mangosd`, and
database-administration child environments.

Validate paths and inspect current status without opening a window:

```powershell
dev\sidecar\.venv\Scripts\python.exe dev\launcher\main.py --check
```

With the complete stack stopped, an integration smoke test can start every
service, verify its listener/readiness, and then stop everything cleanly:

```powershell
dev\sidecar\.venv\Scripts\python.exe dev\launcher\main.py --smoke
```

## Behavior

`Start All` uses dependency order:

1. MariaDB on port 3306
2. Realm server on port 3724
3. AI sidecar on port 8100
4. World server on port 8090

The world readiness budget is 35 minutes because a first playerbot cache build
has previously taken almost 30 minutes. A normal cached boot does not wait for
that budget; it advances immediately when port 8090 begins listening.

`Stop All` reverses that order. The dashboard sends `server shutdown 1` to a
world process it started and uses `mariadb-admin shutdown` for the database.
The database password is read only into the child process environment and is
not placed on a command line or written to a launcher log.

Before stopping a process discovered through a port, the launcher verifies
that its executable matches the configured path. It refuses to terminate a
foreign process occupying a server port.

The world server's console input pipe is owned by the dashboard. Closing the
dashboard while it owns running services prompts to stop them cleanly. Services
that were already running before the dashboard opened are only observed until
the operator explicitly presses Stop.

Service output is written under `Server\logs` using `launcher-*.log` names and
can be tailed inside the dashboard. Runtime paths, ports, order, and timeouts
are defined in `config.json`; secrets are not.
