# backup.py

## Overview
This script creates a backup of a remote server directory and saves it as a .zip file. It is also used to send the .zip file created to Discord for record-keeping purposes in the event that access to the ssh server is blocked or restricted for any reason. 

## Features
- Remote Backup: Downloads a folder from a server over SSH.
- ZIP Compression: Saves the backup as a .zip file with a timestamp.
- Backup Cleanup: Keeps only the latest backups (default is 5).
- Skip Unnecessary Folders: Ignores venv and __pycache__.
- Discord Upload: Sends the .zip file to a Discord channel if under 25MB.


