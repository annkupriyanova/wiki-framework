# wiki-framework

### Terminology Telegram Bot
1. After cloning the repository execute install.sh script. 

The script will:
  - create Docker container with PostgreSQL,
  - install the project dependencies from requirements.txt,
  - execute terminology_bot/database.py to create DB schema and insert initial data.

2. Get your private token from Telegram BotFather (run /newbot command and follow BotFather's instructions).
3. Insert the token into the terminology_bot/config.ini file.
4. Set multimedia_dir in the terminology_bot/config.ini file to store multimedia files for the terms. 
4. To play with the bot run terminology_bot/bot.py file and in Telegram send /start command to your new bot.
