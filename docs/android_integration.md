# Android integration with the SmartGlass Agent server

This guide shows how an Android client can talk to the lightweight HTTP server
exposed by `sdk_python.server`. It covers the two endpoints, request/response
payloads, and how to manage sessions from the app.

## Quickstart: run the server locally

Start the FastAPI app on all interfaces so your Android device or emulator can
reach it:

```bash
python -m sdk_python.server --host 0.0.0.0 --port 8000
```

For lightweight testing without initializing the full agent stack, set the
`SDK_PYTHON_DUMMY_AGENT=1` environment variable. The server will return echo
responses while keeping the API surface identical:

```bash
SDK_PYTHON_DUMMY_AGENT=1 python -m sdk_python.server --host 0.0.0.0 --port 8000
```

Base URL: `http://<your-host>:8000`

## Endpoints

### `POST /ingest`

Create a new session and store the initial context supplied by the Android
client. Call this once per conversation thread.

- **Body:**
  ```json
  {
    "text": "Describe your surroundings",
    "image_path": "/tmp/capture.jpg" // optional absolute or accessible path
  }
  ```
- **Response:**
  ```json
  { "session_id": "<uuid>" }
  ```

### `POST /answer`

Generate a response within an existing session. Reuse the `session_id` returned
from `/ingest` so follow-up questions stay threaded.

- **Body:**
  ```json
  {
    "session_id": "<uuid returned from /ingest>",
    "text": "What do you see?",
    "image_path": "/tmp/capture.jpg" // optional absolute or accessible path
  }
  ```
- **Response:**
  ```json
  {
    "response": "Echo: What do you see?",
    "actions": [],
    "raw": {
      "query": "What do you see?",
      "visual_context": "",
      "metadata": { "cloud_offload": false }
    }
  }
  ```
- **Errors:**
  - `404` if the provided `session_id` is unknown or expired.

## Session handling notes

- Sessions are stored in-memory; restarting the server clears all
  `session_id` values.
- Call `/ingest` to start a conversation, then reuse the returned `session_id`
  for all `/answer` calls until you intentionally start a new session.
- If the app loses the session (e.g., after a server restart), call `/ingest`
  again to obtain a new `session_id` before sending more questions.
- When the dummy agent is enabled, responses are deterministic echo strings; no
  vision or speech models are loaded. This is useful for instrumenting Android
  networking without heavy dependencies.
