# /fk — Log this session to the RiRi dev log

When this command is invoked, write a session entry for the work done in this conversation.
Do NOT ask the user anything. Decide everything yourself from the conversation history.

## Steps

1. **Determine what was done** — scan this conversation for tools called, files changed,
   decisions made, problems solved. Group into one feature/task if focused, or the dominant
   theme if multiple things happened.

2. **Generate the entry metadata:**
   - `date`: today's date (YYYY-MM-DD)
   - `slug`: kebab-case short name, max 4 words (e.g. `nim-model-catalog`, `api-key-rotation`)
   - `title`: human-readable title, max 8 words
   - `tags`: 2-4 tags from: infra, model, nim, hermes, memory, design, tool, config, video,
     image, linkedin, discord, whatsapp, code, fix, feature
   - `summary`: ONE line, max 100 chars — what changed and the key outcome
   - `files_changed`: list every file touched with a parenthetical (created/updated/deleted)
   - Decisions prose: 2-5 paragraphs on WHY things were done this way, what was wrong before,
     what was rejected, what future sessions should know

3. **Create the session folder and CONTEXT.md:**
   ```
   sessions/<date>-<slug>/CONTEXT.md
   ```
   Use this exact format:
   ```
   ---
   date: YYYY-MM-DD
   title: <title>
   tags: [tag1, tag2]
   files_changed:
     - path/to/file    (created/updated/deleted — one-line note)
   ---

   ## What happened
   <1-2 paragraph narrative>

   ## Key decisions
   <decisions and reasoning, one paragraph per decision>

   ## Context for next session
   <what a future Claude needs to know to continue this work>
   ```

4. **Append a row to `sessions/INDEX.md`** — add to the bottom of the table:
   ```
   | YYYY-MM-DD | [<slug>](<date>-<slug>/) | tag1,tag2 | <summary> |
   ```

5. **Confirm** — tell the user: "Logged: `<slug>` — <summary>"

Do not git commit. That is /fkgit's job.
