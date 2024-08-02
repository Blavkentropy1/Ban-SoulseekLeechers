# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2011 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2024 BlavkEntropy1
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# Rslash Soulseek, I Love your lefty mentality. But I dont like leechers. 
#
# You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pynicotine.pluginsystem import BasePlugin
from pynicotine.config import config


class Plugin(BasePlugin):
    PLACEHOLDERS = {
        "%files%": "num_files",
        "%folders%": "num_folders"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.metasettings = {
            "num_files": {
                "description": "Require users to have a minimum number of shared files:",
                "type": "int", "minimum": 0
            },
            "num_folders": {
                "description": "Require users to have a minimum number of shared folders:",
                "type": "int", "minimum": 1
            },
            "ban_min_bytes": {
                "description": "Minimum total size of shared files to avoid a ban (MB)",
                "type": "int", "minimum": 0
            },
            "ban_block_ip": {
                "description": "When banning a user, also block their IP address (If IP Is Resolved)",
                "type": "bool"
            },
            "ignore_user": {
                "description": "Ignore users who do not meet the sharing requirements",
                "type": "bool"
            },
            "bypass_share_limit_for_buddies": {
                "description": "Allow users in the buddy list to bypass the minimum share limit",
                "type": "bool"
            },
            "suppress_all_messages": {
                "description": "Suppress all log messages",
                "type": "bool"
            },
            "open_private_chat": {
                "description": "Open chat tabs when sending private messages to leechers",
                "type": "bool"
            },
            "send_message_to_banned": {
                "description": "Send a message to users who are banned",
                "type": "bool"
            },
            "message": {
                "description": ("Private chat message to send to leechers. Each line is sent as a separate message, "
                                "too many message lines may get you temporarily banned for spam!"),
                "type": "textview"
            },

            "recheck_interval": {
                "description": "Number of files after which to re-check the user's Shared File",
                "type": "int", "minimum": 0
            },
            "recheck_enabled": {
                "description": "Enable re-checking users after a specified number of files",
                "type": "bool"
            },
            "detected_leechers": {
                "description": "Detected leechers",
                "type": "list string"
            }
        }

        self.settings = {
            "message": "Please consider sharing more files if you would like to download from me again. Until then, You are banned. Thanks :)",
            "open_private_chat": False,
            "num_files": 100,  # This is now used for both minimum shared files and ban criteria
            "num_folders": 20,
            "ban_min_bytes": 1000,
            "ban_block_ip": False,
            "ignore_user": False,
            "bypass_share_limit_for_buddies": True,
            "send_message_to_banned": False,
            "suppress_banned_user_logs": False,
            "suppress_ignored_user_logs": True,
            "suppress_ip_ban_logs": False,
            "suppress_all_messages": False,
            "detected_leechers": [],
            "recheck_interval": 10,
            "recheck_enabled": True
        }

        self.probed_users = {}
        self.resolved_users = {}
        self.uploaded_files_count = {}
        self.previous_buddies = set()

    def loaded_notification(self):
        min_num_files = self.metasettings["num_files"]["minimum"]
        min_num_folders = self.metasettings["num_folders"]["minimum"]

        if self.settings["num_files"] < min_num_files:
            self.settings["num_files"] = min_num_files

        if self.settings["num_folders"] < min_num_folders:
            self.settings["num_folders"] = min_num_folders

        if not self.settings["suppress_all_messages"]:
            self.log(
                "Require users to have a minimum of %d files in %d shared public folders.",
                (self.settings["num_files"], self.settings["num_folders"])
            )

    def update_buddy_list(self):
        """Update the list of buddies for proper checking."""
        current_buddies = set(self.core.buddies.users)
        self.previous_buddies = current_buddies

    def check_user(self, user, num_files, num_folders):
        # Ensure buddy list is up-to-date
        self.update_buddy_list()

        if user in self.previous_buddies and self.settings["bypass_share_limit_for_buddies"]:
            if not self.settings["suppress_all_messages"]:
                self.log("User %s is a buddy and bypasses the share limit.", user)
            return

        if user not in self.probed_users:
            return

        if self.probed_users[user] == "okay":
            return

        is_user_accepted = (num_files >= self.settings["num_files"] and num_folders >= self.settings["num_folders"])

        if is_user_accepted or user in self.previous_buddies:
            if user in self.settings["detected_leechers"]:
                self.settings["detected_leechers"].remove(user)

            self.probed_users[user] = "okay"

            if is_user_accepted:
                if not self.settings["suppress_ignored_user_logs"]:
                    self.log("User %s is okay, sharing %s files in %s folders.", (user, num_files, num_folders))
                self.core.network_filter.unban_user(user)
                self.core.network_filter.unignore_user(user)
            else:
                if not self.settings["suppress_ignored_user_logs"]:
                    self.log("Buddy %s is sharing %s files in %s folders. Not complaining.", (user, num_files, num_folders))
            return

        if not self.probed_users[user].startswith("requesting"):
            return

        if user in self.settings["detected_leechers"]:
            self.probed_users[user] = "processed_leecher"
            return

        if (num_files <= 0 or num_folders <= 0) and self.probed_users[user] != "requesting_shares":
            if not self.settings["suppress_all_messages"]:
                self.log("User %s has no shared files according to the server, requesting shares to verify…", user)
            self.probed_users[user] = "requesting_shares"
            self.core.userbrowse.request_user_shares(user)
            return

        if self.settings["message"]:
            self.ban_user(username=user)
            if self.settings["ban_block_ip"]:
                self.block_ip(username=user)
            log_message = "Leecher detected, %s is only sharing %s files in %s folders. Banned and Ignored"
        else:
            log_message = "User %s doesn't share enough files and banned"

        self.probed_users[user] = "pending_leecher"
        if not self.settings["suppress_all_messages"]:
            self.log(log_message, (user, num_files, num_folders))

        if self.settings["ignore_user"]:
            self.core.network_filter.ignore_user(user)

    def upload_queued_notification(self, user, virtual_path, real_path):
        if user in self.probed_users:
            # Increment file count and check if re-check is needed
            self.uploaded_files_count[user] = self.uploaded_files_count.get(user, 0) + 1

            if self.settings["recheck_enabled"] and self.uploaded_files_count[user] % self.settings["recheck_interval"] == 0:
                stats = self.core.users.watched.get(user)
                if stats is not None and stats.files is not None and stats.folders is not None:
                    self.check_user(user, num_files=stats.files, num_folders=stats.folders)
            return

        self.probed_users[user] = "requesting_stats"
        stats = self.core.users.watched.get(user)

        if stats is None:
            return

        if stats.files is not None and stats.folders is not None:
            self.check_user(user, num_files=stats.files, num_folders=stats.folders)

    def user_stats_notification(self, user, stats):
        self.check_user(user, num_files=stats["files"], num_folders=stats["dirs"])

    def upload_finished_notification(self, user, *_):
        if user not in self.probed_users:
            return

        if self.probed_users[user] != "pending_leecher":
            return

        self.probed_users[user] = "processed_leecher"

        if not self.settings["message"]:
            if not self.settings["suppress_all_messages"]:
                self.log("Leecher %s doesn't share enough files. No message is specified in plugin settings.", user)
            return

        for line in self.settings["message"].splitlines():
            for placeholder, option_key in self.PLACEHOLDERS.items():
                line = line.replace(placeholder, str(self.settings[option_key]))

            self.send_private(user, line, show_ui=self.settings["open_private_chat"], switch_page=False)

        if user not in self.settings["detected_leechers"]:
            self.settings["detected_leechers"].append(user)

        if not self.settings["suppress_all_messages"]:
            self.log("Leecher %s doesn't share enough files. Message sent.", user)
        self.ban_user(username=user)
        if self.settings["ban_block_ip"]:
            self.block_ip(username=user)
        if not self.settings["suppress_all_messages"]:
            self.log("User %s banned", user)

        if self.settings["ignore_user"]:
            self.core.network_filter.ignore_user(user)

    def ban_user(self, username=None):
        if username:
            self.core.network_filter.ban_user(username)
            if self.settings["send_message_to_banned"]:
                self.send_message(username)
            if not self.settings["suppress_banned_user_logs"]:
                self.log(f'User banned: {username}')

    def block_ip(self, username=None):
        if username and username in self.resolved_users:
            ip_address = self.resolved_users[username].get("ip_address")
            if ip_address:
                if not self.settings["suppress_ip_ban_logs"]:
                    self.log(f'Attempting to block IP: {ip_address}')
                ip_list = config.sections["server"].get("ipblocklist", {})

                if ip_list is None:
                    ip_list = {}

                if ip_address not in ip_list:
                    ip_list[ip_address] = username
                    config.sections["server"]["ipblocklist"] = ip_list
                    config.write_configuration()
                    if not self.settings["suppress_ip_ban_logs"]:
                        self.log(f'IP successfully blocked: {ip_address}')
                else:
                    if not self.settings["suppress_ip_ban_logs"]:
                        self.log(f'IP already blocked: {ip_address}')
            else:
                if not self.settings["suppress_ip_ban_logs"]:
                    self.log(f"Could not block IP; IP address not found for username: {username}")
        else:
            if not self.settings["suppress_ip_ban_logs"]:
                self.log(f"Could not block IP; username {username} not found in resolved users.")

    def user_resolve_notification(self, user, ip_address, port, country):
        if user not in self.resolved_users:
            self.resolved_users[user] = {
                'ip_address': ip_address,
                'port': port,
                'country': country
            }
        elif country and self.resolved_users[user]['country'] != country:
            self.resolved_users[user]['country'] = country

    def send_message(self, username):
        if self.settings["message"]:
            for line in self.settings["message"].splitlines():
                for placeholder, option_key in self.PLACEHOLDERS.items():
                    line = line.replace(placeholder, str(self.settings[option_key]))

                self.send_private(username, line, show_ui=self.settings["open_private_chat"], switch_page=False)
