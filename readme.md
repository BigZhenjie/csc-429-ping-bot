# main.py

## Overview
This script powers a multifunctional Discord bot built with Hikari and Lightbulb, designed to monitor server health, manage backups, and handle remote patch updates via secure SSH. It includes a built-in Flask web server to keep the bot alive in hosting environments that require HTTP activity (e.g., Replit). The bot checks port availability, uploads website backups, and applies remote patches to restore broken endpoints—all triggered through Discord slash commands. It also supports automated scheduled backups.

## Features
- Keep-Alive Web Server: Uses keep_alive.py and Flask to run a simple web server so the bot doesn’t go idle (like on Replit or other cloud hosts)
- Port Monitoring: monitor.py checks common ports (SSH, HTTP, etc) and alerts a Discord channel if something goes down
- Ping Command: Slash command /ping that gives you a quick status report of all monitored ports, powered by monitor.py
- Patch Update: With /patch, the bot runs patch_update.py to SSH into the server, fix broken paths, and restart stuff as needed
- Website Backup: /backup runs backup.py to grab a zipped backup of the web dir and sends it to Discord if it’s under 25MB
- Scheduled Backups: Can auto-run the backup every few hours and send it to a channel—super helpful for keeping history
- Env Config: Uses .env and dotenv to keep all the settings (tokens, IPs, etc) out of the code—makes setup cleaner and safer

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
- Remote Backup: Securely connects to a remote server over SSH and downloads a specified directory for backup
- ZIP Compression: Compresses the downloaded files into a .zip archive, named with a timestamp for easy reference
- Skip Unnecessary Folders: Excludes common non-essential directories like venv and __pycache__ to save space
- Discord Upload: Sends the backup file to a Discord channel (if its size is below 25MB) for quick off-site storage
- Lightbulb Suggestions: Enables quick-fix prompts in editors like VS Code for cleaner, more efficient code management

## Dependencies
- Python 3.x
- paramiko
- hikari (utilized for Discord upload)

# keepalive.py

## Overiew
This script creates a web server using Flask, designed to help prevent bots or long-running scripts from going idle. By responding to periodic HTTP requests, the script keeps the host process alive.

## Features
- Flask-Based Web Server: Uses Flask to serve a lightweight HTTP endpoint for status checks
- Keep-Alive Behavior: Prevents your script or bot from sleeping by allowing external ping services to keep it active
- Non-Blocking: Runs the Flask server on a separate thread, so it doesn't interfere with main code
- Debugging and Monitoring: The root '/' route returns "Bot is running!", which is useful for monitoring

## Dependencies
- Flask



