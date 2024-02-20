# Pleepbot

![pleep](https://cdn.7tv.app/emote/63f4346b0fd141cefb085cae/4x.gif)

## About

Pleepbot is a simple twitch bot primarily meant for offline chats. Some of its commands were inspired by [Supibot](https://github.com/Supinic/supibot) and [Melonbot](https://github.com/melon095/Melonbot).

## Getting Started

### Prerequisites
Python 3.11

### Installation (Linux)

1. Clone the repo
   ```sh
   git clone https://github.com/Kazzuun/pleepbot.git
   ```
2. Install requirements
   ```sh
   pip install -r requirements.txt
   ```
3. Run the bot
   ```sh
   python3 twitchbot.py
   ```
   or to keep it running in the background
   ```sh
   nohup python3 twitchbot.py > logs/twitch/output.log &
   ```

Before running, copy or rename .env.example to .env and fill it with all needed info.
Running the bot for the first time creates the database and joins the bot's channel.


## TODO: 
- documentation
- discord bot

