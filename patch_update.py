import os
import paramiko
import tempfile
from io import StringIO

class PatchUpdate:
    def __init__(self,
                 ssh_host=None, ssh_port=22, ssh_username=None,
                 ssh_key_passphrase=None,
                 remote_dir="/var/www/student_app"):
        """
        Initialize the PatchUpdate class.
        
        Args:
            ssh_host (str): SSH server hostname/IP
            ssh_port (int): SSH server port
            ssh_username (str): SSH username
            ssh_key_passphrase (str): Passphrase for the SSH key
            remote_dir (str): Remote directory
        """
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_username = ssh_username
        self.ssh_key_passphrase = ssh_key_passphrase
        self.remote_dir = remote_dir

    def _connect_ssh(self):
        """
        Establish SSH connection to the server.
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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

    def restart_service(self):
        try:
            ssh_client = self._connect_ssh()
            if not ssh_client:
                print("Failed to establish SSH connection for service restart")
                return False
            stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl restart student_app.service")
            exit_status = stdout.channel.recv_exit_status()
            stderr_output = stderr.read().decode('utf-8').strip()
            ssh_client.close()

            if exit_status == 0:
                print("Service restart completed successfully")
                return True
            else:
                print(f"Service restart failed with exit status {exit_status}")
                if stderr_output:
                    print(f"Error output: {stderr_output}")
                return False
        except Exception as e:
            print(f"Error restarting service: {e}")
            return False

    def modify_file(self):
        temp_app = None
        temp_index = None
        try:
            # Connect to SSH
            ssh_client = self._connect_ssh()
            if not ssh_client:
                print("Failed to establish SSH connection")
                return False

            # Get SFTP client
            sftp = ssh_client.open_sftp()
            try:
                sftp.chdir(self.remote_dir)
            except Exception as e:
                print(f"Failed to change to remote directory {self.remote_dir}: {e}")
                return False

            # Create temporary files
            temp_app_fd, temp_app = tempfile.mkstemp(suffix='.py', prefix='app_')
            temp_index_fd, temp_index = tempfile.mkstemp(suffix='.html', prefix='index_')
            os.close(temp_app_fd)
            os.close(temp_index_fd)

            sftp.get("app.py", temp_app)
            if self.updateEndpoint(temp_app):
                print("Uploading modified app.py...")
                sftp.put(temp_app, "app.py")
            else:
                print("No changes needed in app.py")

            try:
                sftp.get("templates/index.html", temp_index)
                if self.updateEndpoint(temp_index):
                    print("Uploading modified templates/index.html...")
                    sftp.put(temp_index, "templates/index.html")
                else:
                    print("No changes needed in templates/index.html")
            except Exception as e:
                print(f"Error processing templates/index.html: {e}")

            sftp.close()
            ssh_client.close()
            return True

        except Exception as e:
            print(f"Patch update error: {e}")
            return False
        finally:
            if temp_app and os.path.exists(temp_app):
                try:
                    os.remove(temp_app)
                except Exception as e:
                    print(f"Failed to clean up {temp_app}: {e}")

            if temp_index and os.path.exists(temp_index):
                try:
                    os.remove(temp_index)
                except Exception as e:
                    print(f"Failed to clean up {temp_index}: {e}")

    def updateEndpoint(self, local_temp):
        """
        Check if the file contains the broken path and fix it.
        Args:
            local_temp (str): Path to the local temporary file
        Returns:
            bool: True if changes were made, False otherwise
        """
        old_line = "/transaction"
        new_line = "/submit-transaction"
        changes_made = False

        try:
            with open(local_temp, 'r', encoding='utf-8') as file:
                content = file.read()
            if old_line in content:
                modified_content = content.replace(old_line, new_line)
                with open(local_temp, 'w', encoding='utf-8') as file:
                    file.write(modified_content)
                changes_made = True
        except Exception as e:
            print(f"Error processing file {local_temp}: {e}")
        return changes_made