# Replit setup

This project runs from `.replit` and serves Django on Replit's `$PORT`. Node.js and ffmpeg are provided by `replit.nix` for yt-dlp and audio conversion.

For videos that require YouTube authentication, add a Replit Secret named `YT_DLP_COOKIE_CONTENTS` containing a current Netscape-format cookie export. The application writes it to a private temporary file at runtime. Never commit a cookie file or paste cookies into source code. Public videos can still be downloaded without this Secret when YouTube permits it.

The YouTube IFrame Player API is used only for browser playback. It does not transfer browser cookies to the server or bypass YouTube access controls.
