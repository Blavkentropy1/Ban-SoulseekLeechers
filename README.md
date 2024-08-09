**Ban-SoulseekLeechers** is a plugin designed to automatically ban, ignore, and IP ban users who do not meet sharing criteria. It is inspired by Autobahn and based on the SS Leech plugin.

**Compatibility**: Works with Nicotine+ V3.3.4 (potentially all V3.3.x versions; older versions are untested).

**Installation**: Place the plugin in `C:\Users\<Username>\AppData\Roaming\nicotine\plugins` or your designated plugin folder.

[![Untitled.jpg](https://i.postimg.cc/mZP2D6JH/Untitled.jpg)](https://postimg.cc/jCrr3vsx)

## Features

- **Auto-Ban and Ignore**: Automatically ban and/or ignore users who do not meet the specified sharing requirements.

- **IP Blocking**: Optionally block the IP address of banned users if their IP is resolved.

- **Minimum Share Requirements**:
  - **Files**: Require users to share a minimum number of files.
  - **Folders**: Require users to share a minimum number of folders.

- **Bypass for Buddies**: Allow users in the buddy list to bypass the minimum sharing requirements.

- **Private Chat Handling**:
  - **Open Chat Tabs**: Option to open chat tabs when sending private messages to leechers (can be turned off).
  - **Send Message to Banned Users**: Option to send a customizable message to banned users (can be turned off).

- **Logging Control**:
  - **Suppress Logs**: Options to suppress logs for banned users, ignored users, IP bans, and other actions.
  - **Suppress All Messages**: Option to suppress all log messages for a cleaner log.

- **Leech Detection**:
  - **Track Detected Leechers**: Maintain a list of users identified as leechers.
  - **Handle Detected Leechers**: Take actions such as banning and IP blocking for detected leechers.

- **Message Customization**:
  - **Customizable Ban Message**: Configure the message sent to banned users, with placeholders for dynamic content.

- **Notification Handling**:
  - **Upload and Stats Notifications**: Update user status based on file uploads and user statistics.
  - **User Resolve Notifications**: Update user information with resolved IP addresses, ports, and countries.

- **Settings Management**:
  - **Default Values**: Default settings are provided for each configurable option.
  - **Customizable Settings**: Adjust settings to fit personal preferences.

## Usage

This plugin was created for personal use, and regular updates or additional features are not planned. Users are encouraged to fork the project and make their own modifications as needed. 
Please be aware that false positives may occur, so discretion is advised.

The plugin addresses the challenge of managing numerous leechers and frequent abusive messages from them, while prioritizing users who contribute to the network.
