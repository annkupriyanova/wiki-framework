# wiki-framework

### Terminology Telegram Bot
After activating virtual environment and cloning the repository:
 1. Go to */terminology_bot* directory.
 2. Execute *install.sh* script.

    The script will:
      - create Docker container with PostgreSQL,
      - install the project dependencies from requirements.txt,
      - execute *database.py* to create DB schema and insert initial data.

 3. Get your private token from Telegram BotFather (run */newbot* command and follow BotFather's instructions).
 4. Insert the *token* into the *config.ini* file.
 5. Set *multimedia_dir* in the *config.ini* file to store multimedia files for the terms.
 6. To play with the bot run *bot.py* file.
 7. In Telegram send */start* command to your new bot.
