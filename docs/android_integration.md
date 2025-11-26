# Android integration with the SmartGlass Agent server

The lightweight HTTP server in `sdk_python.server` exposes the SmartGlass Agent
to mobile clients via two POST endpoints. Start the server locally with:

```bash
python -m sdk_python.server --host 0.0.0.0 --port 8000
```

## Endpoints

### `POST /ingest`

Creates a new session and stores the initial context supplied by the Android
client.

- **Body:**
  ```json
  {
    "text": "Describe your surroundings",
    "image_path": "/tmp/capture.jpg" // optional
  }
  ```
- **Response:**
  ```json
  { "session_id": "<uuid>" }
  ```

### `POST /answer`

Asks the SmartGlass Agent to respond within an existing session.

- **Body:**
  ```json
  {
    "session_id": "<uuid returned from /ingest>",
    "text": "What do you see?",
    "image_path": "/tmp/capture.jpg" // optional
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

Sessions are held in-memory for now to keep the API simple for early Android
prototypes. The app should reuse the `session_id` to thread follow-up questions
until more advanced streaming and persistence are added.
