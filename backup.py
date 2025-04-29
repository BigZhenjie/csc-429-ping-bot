import os
import zipfile
import datetime
import discord
from discord.ext import commands
import shutil

class Backup:
    def __init__(self, backup_dir="backups", max_backups=5):
        """
        Initialize the Backup class.
        
        Args:
            backup_dir (str): Directory to store backups
            max_backups (int): Maximum number of backups to keep
        """
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self.source_dir = "/var/www/html"
        
        # Create backup directory if it doesn't exist
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
    
    def create_backup(self):
        """
        Create a backup of the /var/www/html directory excluding venv.
        
        Returns:
            str: Path to the created backup file
        """
        # Generate timestamp for backup filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"website_backup_{timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        # Create zip file
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.source_dir):
                # Skip venv directory
                if 'venv' in dirs:
                    dirs.remove('venv')
                
                for file in files:
                    file_path = os.path.join(root, file)
                    # Make the path relative to source_dir
                    arcname = os.path.relpath(file_path, self.source_dir)
                    zipf.write(file_path, arcname)
        
        # Manage backup retention
        self._cleanup_old_backups()
        
        return backup_path
    
    def _cleanup_old_backups(self):
        """Delete old backups if exceeding max_backups limit."""
        backups = []
        
        for filename in os.listdir(self.backup_dir):
            if filename.startswith("website_backup_") and filename.endswith(".zip"):
                file_path = os.path.join(self.backup_dir, filename)
                backups.append((file_path, os.path.getmtime(file_path)))
        
        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x[1], reverse=True)
        
        # Remove oldest backups if exceeding max_backups
        for file_path, _ in backups[self.max_backups:]:
            os.remove(file_path)
    
    async def send_backup_to_channel(self, bot, channel_id):
        """
        Create a backup and send it to a Discord channel.
        
        Args:
            bot: Discord bot instance
            channel_id (int): ID of the channel to send backup to
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            channel = bot.get_channel(channel_id)
            if channel is None:
                print(f"Channel with ID {channel_id} not found.")
                return False
            
            # Create backup
            backup_path = self.create_backup()
            
            # Check if file size is under Discord's limit (25MB)
            file_size = os.path.getsize(backup_path) / (1024 * 1024)  # in MB
            if file_size > 25:
                await channel.send(f"Backup file is too large ({file_size:.2f}MB) to send directly.")
                return False
            
            file = discord.File(backup_path)
            await channel.send(f"Website backup created on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:", file=file)
            return True
        except Exception as e:
            print(f"Error creating or sending backup: {e}")
            return False