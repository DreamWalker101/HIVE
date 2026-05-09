# /fkgit — Log this session and push to GitHub

Runs /fk first (write the session log entry), then commits and pushes.

## Steps

1. Run everything in /fk exactly as described there.

2. Then run these git commands:
   ```bash
   cd /home/ahmed/projects/riri
   git add sessions/
   git commit -m "log: <slug> — <summary>"
   git push
   ```
   Use the same slug and summary generated in step 1.

3. Confirm: "Logged + pushed: `<slug>` — <summary>"

If git push fails (no remote, auth issue, etc.) — report the error clearly, don't retry silently.
