# main.py

## Overview
This script powers a multifunctional Discord bot built with Hikari and Lightbulb, designed to monitor server health, manage backups, and handle remote patch updates via secure SSH. It includes a built-in Flask web server to keep the bot alive in hosting environments that require HTTP activity (e.g., Replit). The bot checks port availability, uploads website backups, and applies remote patches to restore broken endpoints—all triggered through Discord slash commands. It also supports automated scheduled backups.

## Features
- Keep-Alive Web Server: Uses keep_alive.py and Flask to run a simple web server so the bot doesn’t go idle (like on Replit or other cloud hosts)
- Port monitoring: monitor.py checks common ports (SSH, HTTP, etc) and alerts a Discord channel if something goes down
- Ping command: Slash command /ping that gives you a quick status report of all monitored ports, powered by monitor.py (utilized in Discord server by users)
- Patch update: With /patch, the bot runs patch_update.py to SSH into the server, fix broken paths, and restart stuff as needed
- Website backup: /backup runs backup.py to grab a zipped backup of the web dir and sends it to Discord if it’s under 25MB
- Scheduled backups: Can auto-run the backup every few hours and send it to a channel—super helpful for keeping history
- Env config: Uses .env and dotenv to keep all the settings (tokens, IPs, etc) out of the code—makes setup cleaner and safer

# Dependencies
- Flask: lightweight server used to keep the bot alive via HTTP pinging
- hikari: asynchronous Discord bot framework
- lightbulb: command handler extension for Hikari, used to manage slash commands
- aiohttp: for asynchronous HTTP requests (used for API endpoint monitoring)
- paramiko: used for SSH connections to perform backups and remote patches
- python-dotenv: loads environment variables from a .env file


# backup.py

## Overview
This script creates a backup of a remote server directory and saves it as a .zip file. It is also used to send the .zip file created to Discord for record-keeping purposes in the event that access to the ssh server is blocked or restricted for any reason. 

## Features
- Remote backup: Securely connects to a remote server over SSH and downloads a specified directory for backup
- ZIP compression: Compresses the downloaded files into a .zip archive, named with a timestamp for easy reference
- Skip unnecessary Folders: Excludes common non-essential directories like venv and __pycache__ to save space
- Discord upload: Sends the backup file to a Discord channel (if its size is below 25MB) for quick off-site storage
- Lightbulb suggestions: Enables quick-fix prompts in editors like VS Code for cleaner, more efficient code management

## Dependencies
- Python 3.x
- paramiko
- hikari (utilized for Discord upload)

# keepalive.py

## Overiew
This script creates a web server using Flask, designed to help prevent bots or long-running scripts from going idle. By responding to periodic HTTP requests, the script keeps the host process alive.

## Features
- Flask-based web server: Uses Flask to serve a lightweight HTTP endpoint for status checks
- Keep-alive behavior: Prevents your script or bot from sleeping by allowing external ping services to keep it active
- Non-blocking: Runs the Flask server on a separate thread, so it doesn't interfere with main code
- Debugging and monitoring: The root '/' route returns "Bot is running!", which is useful for monitoring

## Dependencies
- Flask

# monitor.py

## Overview
This script monitors specific ports on a web server to ensure they're functioning correctly. If a port or an API endpoint becomes unreachable, it sends alerts (e.g., to a Discord channel) and can trigger automatic recovery actions. It's used to help detect outages or possible external tampering and restore functionality by patching affected files or restarting services.

## Features
- Live status alerts: Sends alerts to Discord whenever the web server becomes unaccessable or comes back online
- Automatic recovery: If the API endpoint fails, can automatically trigger a patch update and restart the service using patch_update.py
- State tracking: Remembers previous port/API states to avoid duplicate alerts and tracks recovery status

## Dependencies
- Python 3.x
- asyncio – For running checks asynchronously
- socket – Used for low-level port status checks
- aiohttp – Sends HTTP requests to check the API endpoint
- hikari – Sends alert messages through the Discord bot
- time and json – Used for logging and response parsing (standard library)

# patchupdate.py

## Overview
this script connects to a server using SSH, grabs a couple key website files, and looks for broken paths (like old /transaction routes). If it finds any, it fixes them and sends the updated files back to the server. It can also restart the web service so the changes take effect. It’s mainly used to quickly fix stuff if something breaks—like after a bad update or if the site gets messed with.

## Features
- Remote SSH connection: Securely connects to the server using paramiko and an SSH key loaded from the environment
- Auto- patch files: Detects and replaces outdated endpoint paths (e.g., /transaction → /submit-transaction) in app.py and index.html
- Service restart: After patching, it can automatically restart the web app service (student_app.service) using systemctl
- Safe file-editing: Edits files locally in a temporary directory before uploading changes back to the server
- Error handling and logging: Catches and prints errors throughout the process for easier debugging and recovery

## Dependencies
- Python 3.x
- paramiko – for SSH and SFTP operations
- os, tempfile, io – standard library modules used for environment handling and file operations







