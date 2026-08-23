# Replit setup

This project runs from `.replit` and serves Django on Replit's `$PORT`. Node.js and ffmpeg are provided by `replit.nix` for yt-dlp and audio conversion.

For videos that require YouTube authentication, use your own signed-in YouTube session:

1. Sign in to YouTube in your local browser.
2. Export cookies in Netscape format with a reputable cookies.txt browser extension. Export only the YouTube cookies needed by this app.
3. In Replit, open Tools > Secrets and add `YT_DLP_COOKIE_CONTENTS`. Paste the exported file contents into the Secret value. Do not send the contents in chat, commit them, or put them in a public file.
4. Restart the Repl. The application writes the Secret to a private temporary file at runtime.

Cookies expire and should be replaced by repeating these steps. Use this only for videos you are authorized to access and download. Public videos can still be downloaded without this Secret when YouTube permits it.

The YouTube IFrame Player API is used only for browser playback. It does not transfer browser cookies to the server or bypass YouTube access controls.
