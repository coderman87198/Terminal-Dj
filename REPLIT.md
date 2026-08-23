# Deployment setup

The project can run on Replit using `.replit` and `replit.nix`, or on Render using the Docker configuration in `django_backend/Dockerfile`. Both environments provide Node.js and ffmpeg for yt-dlp and audio conversion.

## Render Secret File

Render Secret Files are mounted only under `/etc/secrets/`. To configure one:

1. Sign in to YouTube in your local browser.
2. Export your own cookies in Netscape `cookies.txt` format with a reputable exporter.
3. In Render, open Environment > Secret Files and create a file named `www.youtube.com_cookies.txt`.
4. Add the environment variable `YT_DLP_COOKIEFILE` with this exact value: `/etc/secrets/www.youtube.com_cookies.txt`.
5. Restart or redeploy the service. Secret Files are mounted after restart.
6. In the Render Shell, verify only the file metadata with `ls -l /etc/secrets/`; never print the file contents.

If the file is missing, recreate it under Render > Environment > Secret Files. Cookies expire and should be replaced by repeating these steps. Use this only for videos you are authorized to access and download. Public videos can still be downloaded without cookies when YouTube permits it.

## Replit Secret

For Replit, add the complete Netscape cookie export as a Secret named `YT_DLP_COOKIE_CONTENTS`. The application writes it to a private temporary file at runtime. Never commit a cookie file, paste cookies into source code, or send them in chat.

The YouTube IFrame Player API is used only for browser playback. It does not transfer browser cookies to the server or bypass YouTube access controls.
