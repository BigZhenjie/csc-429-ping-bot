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

