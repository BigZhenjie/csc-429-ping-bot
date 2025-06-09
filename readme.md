# backup.py

## Overview
This script creates a backup of a remote server directory and saves it as a .zip file. It is also used to send the .zip file created to Discord for record-keeping purposes in the event that access to the ssh server is blocked or restricted for any reason. 

## Features
- Remote Backup: Securely connects to a remote server over SSH and downloads a specified directory for backup.
- ZIP Compression: Compresses the downloaded files into a .zip archive, named with a timestamp for easy reference.
- Backup Cleanup: Automatically manages storage by keeping only the most recent backups (default limit is 5).
- Skip Unnecessary Folders: Excludes common non-essential directories like venv and __pycache__ to save space.
- Discord Upload: Sends the backup file to a Discord channel if its size is below 25MB for quick off-site storage.
- Lightbulb Suggestions: Enables quick-fix prompts in editors like VS Code for cleaner, more efficient code management.

## Dependencies
- Python 3.x
- paramiko
- hikari (utilized for Discord upload)

#
