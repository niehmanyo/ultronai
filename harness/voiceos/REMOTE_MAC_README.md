# Ultron Remote — Mac Host V0.1

A private, Mac-hosted web control surface for the existing DeepSeek Harness SDK runtime. The iPhone-friendly UI is served by the Mac; prompts are sent to the local DSH workspace.

## Included

- Persistent DSH SDK runtime on macOS.
- Responsive chat at http://127.0.0.1:8766.
- Streaming status, sanitized tool lifecycle events and final response.
- Random bearer token stored at ~/.ultron/remote-access-token with owner-only permissions.
- Loopback-only listener. Use Tailscale Serve for private iPhone access; never expose the agent directly to the public Internet.
- Optional per-user macOS LaunchAgent for background operation.

This version is remote text chat only. Phone microphone streaming, remote TTS, uploads, approval UI, notifications and multi-user access are not included.

## Requirements

- macOS 14+ / Apple Silicon.
- Existing harness/ultron-workspace.
- Python environment .venv-voiceos312 with voiceos/requirements.txt installed.
- OpenAI API key from environment (foreground) or macOS Keychain (background).

## 1. Save the API key for background operation

Run this on the Mac; security prompts for the password interactively:

    security add-generic-password -U -s com.ultron.remote.server -a OPENAI_API_KEY

Enter the OpenAI API key when prompted. The server retrieves it from Keychain and never prints it.

For a foreground test only:

    export OPENAI_API_KEY='your-key'

Never put a real key in a script, plist, GitHub, screenshot or chat.

## 2. Start in foreground first

    cd harness
    source .venv-voiceos312/bin/activate
    python voiceos/remote_server.py

On first start, copy the generated access token into the Ultron Remote login screen. The token is saved at ~/.ultron/remote-access-token and persists between restarts.

Open http://127.0.0.1:8766 on the Mac. Enter sends; Shift+Enter inserts a newline.

To use another port:

    python voiceos/remote_server.py --port 8767

## 3. Install as a background Mac service

Stop the foreground process with Ctrl+C, then:

    cd harness
    source .venv-voiceos312/bin/activate
    python voiceos/launch_agent.py install

The user LaunchAgent starts at login and restarts after unexpected exits. It listens only on 127.0.0.1:8766.

Management:

    python voiceos/launch_agent.py status
    python voiceos/launch_agent.py uninstall

Logs:
- ~/.ultron/logs/remote-server.log
- ~/.ultron/logs/remote-server-error.log

After changing code, uninstall and install again to reload the LaunchAgent.

## 4. Optional iPhone access over Tailscale

Install and sign in to Tailscale on both Mac and iPhone using the same tailnet. Keep Ultron bound to localhost. On the Mac:

    tailscale serve --bg http://127.0.0.1:8766
    tailscale serve status

Open the HTTPS URL shown by the status command on the iPhone and authenticate with the Ultron token.

Stop publishing:

    tailscale serve reset

Tailscale Serve is the recommended tailnet-only HTTPS path. Do not use Funnel, public router port forwarding, or bind Ultron to 0.0.0.0.

## Security model and limitations

- Chat and health API routes require a high-entropy bearer token.
- Token file is owner-only. Browser token is kept in tab session storage, not local storage.
- Request size and prompt length are bounded. No CORS access is enabled.
- HTTP request logging omits URLs, prompt bodies and credentials.
- Tool visualization exports only bounded tool names, generated per-turn IDs and lifecycle state. Tool arguments, results and hidden reasoning are not exposed.
- DSH calls are serialized because a single SDK runtime is shared.
- Not designed for multiple users or untrusted devices. Protect the Mac account and tailnet.
- Revoke access by deleting ~/.ultron/remote-access-token and restarting the server.
- PWA caches only the app shell, never API/chat data. Transcript display is held in the current browser tab session.
- No remote voice input/output or desktop UI control yet.

## Troubleshooting

401 / token rejected:

    cat ~/.ultron/remote-access-token

API key missing under LaunchAgent:

    security find-generic-password -s com.ultron.remote.server -a OPENAI_API_KEY

Recreate the Keychain item using section 1, then restart the service.

Server not responding:

    python voiceos/launch_agent.py status
    tail -n 80 ~/.ultron/logs/remote-server-error.log

Tailscale address unavailable: verify both devices are online in the same tailnet, then run tailscale serve status on the Mac.

## Files

- remote_server.py — authenticated local HTTP/SSE server and DSH SDK lifecycle.
- remote.html — responsive chat/PWA front end.
- remote_sw.js — app-shell cache only.
- launch_agent.py — install/status/uninstall LaunchAgent.
- tests/test_remote_server.py — offline auth and input-boundary tests.
