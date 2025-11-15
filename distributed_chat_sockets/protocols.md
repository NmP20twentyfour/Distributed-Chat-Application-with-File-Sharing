# Protocol for TCP Chat + File Transfer

Framing:
- Each message is sent as:
  1. 4 bytes (big-endian unsigned int) specifying the length of the JSON header (N).
  2. N bytes of UTF-8 JSON header.
  3. Optional binary payload (exists when header['type']=='file'), length given by header['filesize'].

Header JSON fields:
- Common:
  - "type": "join" | "message" | "file" | "system"
- "join":
  - "username": sender display name
- "message":
  - "text": message string
- "file":
  - "filename": original filename (string)
  - "filesize": integer bytes length
- "system":
  - "text": system notification text

Behavior:
- On connecting client should send a "join" header with username.
- For "file", after header, exactly 'filesize' bytes of raw file data follow.
- Server broadcasts message and file frames to other clients.
