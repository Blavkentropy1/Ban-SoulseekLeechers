from pynicotine.pluginsystem import BasePlugin
from pynicotine.config import config
from datetime import datetime, timedelta

class Plugin(BasePlugin):
    VERSION = "1.0"

    PLACEHOLDERS = {
        "%files%": "num_files",
        "%folders%": "num_folders"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Define metasettings with defaults for the plugin
        self.metasettings = {
            "num_files": {
                "description": "Require users to have a minimum number of shared files:",
                "type": "int", "minimum": 0,
                "default": 100
            },
            "num_folders": {
                "description": "Require users to have a minimum number of shared folders:",
                "type": "int", "minimum": 1,
                "default": 5
            },
            "ban_min_bytes": {
                "description": "Minimum total size of shared files to avoid a ban (MB)",
                "type": "int", "minimum": 0,
                "default": 100
            },
            "ban_block_ip": {
                "description": "When banning a user, also block their IP address (If IP Is Resolved)",
                "type": "bool",
                "default": False
            },
            "ignore_user": {
                "description": "Ignore users who do not meet the sharing requirements",
                "type": "bool",
                "default": False
            },
            "bypass_share_limit_for_buddies": {
                "description": "Allow users in the buddy list to bypass the minimum share limit",
                "type": "bool",
                "default": True
            },
            "open_private_chat": {
                "description": "Open chat tabs when sending private messages to leechers",
                "type": "bool",
                "default": False
            },
            "send_message_to_banned": {
                "description": "Send a message to users who are banned",
                "type": "bool",
                "default": False
            },
            "message": {
                "description": (
                    "Private chat message to send to leechers. Each line is sent as a separate message, "
                    "too many message lines may get you temporarily banned for spam!"
                ),
                "type": "textview",
                "default": "Please share more files if you wish to download from me again. You are banned until then. Thanks!"
            },
            "suppress_banned_user_logs": {
                "description": "Suppress log entries for banned users",
                "type": "bool",
                "default": False
            },
            "suppress_ignored_user_logs": {
                "description": "Suppress log entries for ignored users",
                "type": "bool",
                "default": True
            },
            "suppress_ip_ban_logs": {
                "description": "Suppress log entries for IP bans",
                "type": "bool",
                "default": True
            },
            "suppress_request_logs": {
                "description": "Suppress log entries when requesting shared file details",
                "type": "bool",
                "default": False
            },
            "suppress_all_messages": {
                "description": "Suppress all log messages",
                "type": "bool",
                "default": False
            },
            "suppress_meets_criteria_logs": {
                "description": "Suppress log entries for users who meet the criteria",
                "type": "bool",
                "default": False
            },
            "recent_ban_duration": {
                "description": "Duration in minutes to consider a ban recent",
                "type": "int",
                "default": 60
            }
        }

        self.settings = {
            "message": self.metasettings["message"]["default"],
            "open_private_chat": self.metasettings["open_private_chat"]["default"],
            "num_files": self.metasettings["num_files"]["default"],
            "num_folders": self.metasettings["num_folders"]["default"],
            "ban_min_bytes": self.metasettings["ban_min_bytes"]["default"],
            "ban_block_ip": self.metasettings["ban_block_ip"]["default"],
            "ignore_user": self.metasettings["ignore_user"]["default"],
            "bypass_share_limit_for_buddies": self.metasettings["bypass_share_limit_for_buddies"]["default"],
            "send_message_to_banned": self.metasettings["send_message_to_banned"]["default"],
            "suppress_banned_user_logs": self.metasettings["suppress_banned_user_logs"]["default"],
            "suppress_ignored_user_logs": self.metasettings["suppress_ignored_user_logs"]["default"],
            "suppress_ip_ban_logs": self.metasettings["suppress_ip_ban_logs"]["default"],
            "suppress_request_logs": self.metasettings["suppress_request_logs"]["default"],
            "suppress_all_messages": self.metasettings["suppress_all_messages"]["default"],
            "suppress_meets_criteria_logs": self.metasettings["suppress_meets_criteria_logs"]["default"],
            "detected_leechers": [],
        }

        # Initialize internal state variables
        self.probed_users = {}
        self.resolved_users = {}
        self.uploaded_files_count = {}
        self.previous_buddies = set()
        self.logged_scans = set()
        self.recent_bans = {}

    def loaded_notification(self):
        """Notification when the plugin is loaded. Sets minimum file and folder counts."""
        min_num_files = self.metasettings["num_files"]["minimum"]
        min_num_folders = self.metasettings["num_folders"]["minimum"]

        # Ensure that minimum values are respected
        self.settings["num_files"] = max(self.settings["num_files"], min_num_files)
        self.settings["num_folders"] = max(self.settings["num_folders"], min_num_folders)

        if not self.settings["suppress_all_messages"]:
            self.log("Users need at least %d files and %d folders.", (self.settings["num_files"], self.settings["num_folders"]))

    def update_buddy_list(self):
        """Update the list of buddies."""
        self.previous_buddies = set(self.core.buddies.users)

    def check_user(self, user, num_files, num_folders):
        """Check if a user meets the sharing criteria and handle accordingly."""
        self.update_buddy_list()

        if user in self.previous_buddies and not self.probed_users.get(user) == "requesting_stats":
            if not self.settings["bypass_share_limit_for_buddies"]:
                if not self.settings["suppress_all_messages"]:
                    self.log("Buddy %s is sharing %d files in %d folders. Skipping check.", (user, num_files, num_folders))
            return

        # If the user is not in probed_users, start probing for their stats
        if user not in self.probed_users:
            self.probed_users[user] = "requesting_stats"
            stats = self.core.users.watched.get(user)

            if stats is None:
                return

            if stats.files is not None and stats.folders is not None:
                self.check_user(user, num_files=stats.files, num_folders=stats.folders)
            return

        if self.probed_users[user] == "okay":
            return

        is_user_accepted = (num_files >= self.settings["num_files"] and num_folders >= self.settings["num_folders"])

        if is_user_accepted or user in self.previous_buddies:
            if user in self.settings["detected_leechers"]:
                self.settings["detected_leechers"].remove(user)

            self.probed_users[user] = "okay"

            if is_user_accepted:
                if not self.settings["suppress_all_messages"]:
                    if user not in self.logged_scans:
                        self.log("User %s is okay, sharing %d files in %d folders.", (user, num_files, num_folders))
                        self.logged_scans.add(user)
                self.core.network_filter.unban_user(user)
                self.core.network_filter.unignore_user(user)
            else:
                if not self.settings["suppress_all_messages"]:
                    if user not in self.logged_scans:
                        self.log("Buddy %s is sharing %d files in %d folders. Not complaining.", (user, num_files, num_folders))
                        self.logged_scans.add(user)
            return

        if not is_user_accepted:
            self.probed_users[user] = "pending_leecher"
            if not self.settings["suppress_all_messages"]:
                if not self.settings["suppress_ignored_user_logs"]:
                    if user not in self.logged_scans:
                        self.log(
                            "Leecher detected: %s with %d files; %d folders.", 
                            (user, num_files, num_folders)
                        )
                        self.logged_scans.add(user)

            self.ban_user(user, num_files=num_files, num_folders=num_folders)
            if self.settings["ban_block_ip"]:
                self.block_ip(user)
        else:
            if not self.settings["suppress_all_messages"]:
                if user not in self.logged_scans:
                    self.log("User %s is not a Leecher.", user)
                    self.logged_scans.add(user)

    def upload_queued_notification(self, user, virtual_path, real_path):
        """Notify the plugin of a queued file upload and update the user's file count."""
        if user in self.probed_users and self.probed_users[user] == "requesting_stats":
            # Increment the file count for users currently being probed
            self.uploaded_files_count[user] = self.uploaded_files_count.get(user, 0) + 1
            return

        # Only check if the user is not being probed yet
        if user not in self.probed_users:
            self.probed_users[user] = "requesting_stats"
            stats = self.core.users.watched.get(user)

            if stats is None:
                return

            if stats.files is not None and stats.folders is not None:
                self.check_user(user, num_files=stats.files, num_folders=stats.folders)

    def upload_started_notification(self, user, *args):
        """Handle the start of a file upload by a user."""
        self.upload_queued_notification(user, "", "")

    def upload_finished_notification(self, user, *_):
        """Handle the completion of an upload for a user, including banning if necessary."""
        if user not in self.probed_users:
            return

        if self.probed_users[user] != "pending_leecher":
            return

        if self.probed_users[user] == "processed_leecher":
            return

        self.probed_users[user] = "processed_leecher"

        now = datetime.now()
        if user in self.recent_bans:
            ban_time = self.recent_bans[user]
            if now - ban_time < timedelta(minutes=self.settings["recent_ban_duration"]):
                if not self.settings["suppress_all_messages"]:
                    if user not in self.logged_scans:
                        self.log("User %s was recently banned. Skipping message.", user)
                return

        if self.settings["send_message_to_banned"] and self.settings["message"]:
            if not self.settings["suppress_all_messages"]:
                if user not in self.logged_scans:
                    self.log("Sending message to banned user %s", user)
                    self.logged_scans.add(user)
            for line in self.settings["message"].splitlines():
                original_line = line
                for placeholder, option_key in self.PLACEHOLDERS.items():
                    line = line.replace(placeholder, str(self.settings[option_key]))
                if not self.settings["suppress_all_messages"]:
                    self.log("Processed message line: %s", line)
                self.send_private(user, line, show_ui=self.settings["open_private_chat"], switch_page=False)

        if user not in self.settings["detected_leechers"]:
            self.settings["detected_leechers"].append(user)

        self.ban_user(user, num_files=self.uploaded_files_count.get(user, 0), num_folders=0)
        if self.settings["ban_block_ip"]:
            self.block_ip(user)
        if not self.settings["suppress_all_messages"]:
            if not self.settings["suppress_banned_user_logs"]:
                self.log("User %s banned.", user)

    def ban_user(self, username=None, num_files=0, num_folders=0):
        """Ban a user and optionally ignore them based on settings."""
        if username:
            self.core.network_filter.ban_user(username)
            self.recent_bans[username] = datetime.now()
            if not self.settings["suppress_all_messages"]:
                if not self.settings["suppress_banned_user_logs"]:
                    log_message = 'Banned Leecher %s - Sharing: %d files, %d folders' % (username, num_files, num_folders)
                    self.log(log_message)

            if self.settings["ignore_user"]:
                self.core.network_filter.ignore_user(username)
                if not self.settings["suppress_all_messages"]:
                    if not self.settings["suppress_ignored_user_logs"]:
                        self.log('Ignored Leecher: %s' % username)

    def block_ip(self, username=None):
        """Block the IP address of a user if resolved."""
        if username and username in self.resolved_users:
            ip_address = self.resolved_users[username].get("ip_address")
            if ip_address:
                if not self.settings["suppress_all_messages"] and not self.settings["suppress_ip_ban_logs"]:
                    self.log('Blocking IP: %s', ip_address)
                ip_list = config.sections["server"].get("ipblocklist", {})

                if ip_list is None:
                    ip_list = {}

                if ip_address not in ip_list:
                    ip_list[ip_address] = username
                    config.sections["server"]["ipblocklist"] = ip_list
                    config.write_configuration()
                    if not self.settings["suppress_all_messages"] and not self.settings["suppress_ip_ban_logs"]:
                       self.log('Blocked IP: %s', ip_address)
                else:
                    if not self.settings["suppress_all_messages"] and not self.settings["suppress_ip_ban_logs"]:
                        self.log('IP already blocked: %s', ip_address)
            else:
                if not self.settings["suppress_all_messages"] and not self.settings["suppress_ip_ban_logs"]:
                    self.log("No IP found for username: %s", username)
        else:
            if not self.settings["suppress_all_messages"] and not self.settings["suppress_ip_ban_logs"]:
                self.log("Username %s IP address was not resolved", username)

    def user_resolve_notification(self, user, ip_address, port, country):
        """Update the resolved IP address and other details for a user."""
        if user not in self.resolved_users:
            self.resolved_users[user] = {
                'ip_address': ip_address,
                'port': port,
                'country': country
            }
        elif country and self.resolved_users[user]['country'] != country:
            self.resolved_users[user]['country'] = country

    def send_message(self, username):
        """Send a private message to a user with placeholders replaced by actual settings."""
        if self.settings["send_message_to_banned"] and self.settings["message"]:
            for line in self.settings["message"].splitlines():
                original_line = line
                for placeholder, option_key in self.PLACEHOLDERS.items():
                    line = line.replace(placeholder, str(self.settings[option_key]))
                if not self.settings["suppress_all_messages"]:
                    self.log("Processed message line: %s", line)
                self.send_private(username, line, show_ui=self.settings["open_private_chat"], switch_page=False)
