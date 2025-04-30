import os
import zipfile
import datetime
import io
import paramiko
import tempfile
import shutil
import stat
import posixpath 
from io import StringIO

class Backup:
    def __init__(self, backup_dir="backups", max_backups=5, 
                 ssh_host=None, ssh_port=22, ssh_username=None, 
                 ssh_key_passphrase=None, 
                 remote_dir="/var/www/student_app"):
        """
        Initialize the Backup class.
        
        Args:
            backup_dir (str): Local directory to store backups
            max_backups (int): Maximum number of backups to keep
            ssh_host (str): SSH server hostname/IP
            ssh_port (int): SSH server port
            ssh_username (str): SSH username
            ssh_key_passphrase (str): Passphrase for the SSH key
            remote_dir (str): Remote directory to backup
        """
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_username = ssh_username
        self.ssh_key_passphrase = ssh_key_passphrase
        self.remote_dir = remote_dir
        
        # Create backup directory if it doesn't exist
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
    
    def _connect_ssh(self):
        """
        Establish SSH connection to the server.
        
        Returns:
            paramiko.SSHClient: Connected SSH client
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Load private key from environment variable
            ssh_key_data = os.getenv("SSH_KEY")
            if not ssh_key_data:
                raise ValueError("SSH_KEY environment variable is not set or empty.")
            
            # Replace literal \n with actual newlines
            ssh_key_data = ssh_key_data.replace("\\n", "\n")
            
            # Load the private key
            private_key = paramiko.Ed25519Key.from_private_key(StringIO(ssh_key_data), password=self.ssh_key_passphrase)
            
            # Connect to the server
            client.connect(
                hostname=self.ssh_host,
                port=self.ssh_port,
                username=self.ssh_username,
                pkey=private_key
            )
            
            return client
        except Exception as e:
            print(f"SSH connection error: {e}")
            return None
    
    def create_backup(self):
        """
        Create a backup of the remote directory excluding venv.
        
        Returns:
            str: Path to the created backup file
        """
        # Generate timestamp for backup filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"website_backup_{timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        # Create temporary directory for files
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Connect to SSH
            ssh_client = self._connect_ssh()
            if not ssh_client:
                print("Failed to establish SSH connection")
                return None
            
            # Get SFTP client
            sftp = ssh_client.open_sftp()
            
            # Recursively download files (excluding venv)
            self._download_dir(sftp, self.remote_dir, temp_dir)
            
            # Close connections
            sftp.close()
            ssh_client.close()
            
            # Create zip file from downloaded content
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Make the path relative to temp_dir
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            # Manage backup retention
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            print(f"Backup creation error: {e}")
            return None
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _download_dir(self, sftp, remote_dir, local_dir):
        os.makedirs(local_dir, exist_ok=True)

        for item in sftp.listdir_attr(remote_dir):
            if item.filename in ('venv', '__pycache__'):
                continue

            remote_path = posixpath.join(remote_dir, item.filename)  # ✅ always forward slashes
            local_path = os.path.join(local_dir, item.filename)      # ✅ local filesystem

            if stat.S_ISDIR(item.st_mode):
                self._download_dir(sftp, remote_path, local_path)
            else:
                print(f"Downloading: {remote_path} -> {local_path}")  # helpful log
                sftp.get(remote_path, local_path)
    
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
        bot: Hikari bot instance
        channel_id (int): ID of the channel to send backup to
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create backup
        backup_path = self.create_backup()
        if not backup_path:
            await bot.rest.create_message(
                channel_id,
                "Failed to create backup. Check server logs for details."
            )
            return False
        
        # Check if file size is under Discord's limit (25MB)
        file_size = os.path.getsize(backup_path) / (1024 * 1024)  # in MB
        if file_size > 25:
            await bot.rest.create_message(
                channel_id,
                f"Backup file is too large ({file_size:.2f}MB) to send directly."
            )
            return False
        
        # Send the backup file
        with open(backup_path, "rb") as f:
            await bot.rest.create_message(
                channel_id,
                f"Website backup created on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:",
                attachment=f
            )
        return True
    except Exception as e:
        print(f"Error creating or sending backup: {e}")
        await bot.rest.create_message(
            channel_id,
            f"Error during backup process: {str(e)}"
        )
        return False