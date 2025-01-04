# LeetCode Discord Bot

A Discord bot that provides various LeetCode functionalities, including fetching random problems, daily challenges, user statistics,AI Hints and more.

## Bot Usage and Reach

The bot is currently active and being utilized across more than 40 servers.

## Features

- **Random LeetCode Problem**: Fetch a random LeetCode problem by difficulty.
- **Daily Challenge**: Get today's LeetCode daily challenge.
- **User Statistics**: View solving statistics for a LeetCode user.
- **Problem Search**: Search for LeetCode problems by keyword.
- **Upcoming Contests**: View upcoming LeetCode contests.
- **AI-Generated Hints**: Get AI-generated hints for LeetCode problems.

## Commands

- `!leetcode [difficulty]`: Fetch a random LeetCode problem. Difficulty options: easy, medium, hard, random.
- `!daily`: Fetch today's LeetCode problem.
- `!lcuser <username>`: Get LeetCode user statistics.
- `!lcsearch <keyword>`: Search LeetCode problems by keyword.
- `!lccontest`: View upcoming LeetCode contests.
- `!lchint <problem_number>`: Get an AI-generated hint for a LeetCode problem.

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/srexrg/lc_bot.git
   cd lc_bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**:
   - Create a `.env` file in the root directory.
   - Add your Discord bot token and OpenAI API key:
     ```
     DISCORD_TOKEN=your_discord_token
     OPENAI_API_KEY=your_openai_api_key
     ```

4. **Run the bot**:
   ```bash
   python main.py
   ```

## Requirements

- Python 3.8+
- Discord.py
- Requests
- OpenAI API
- dotenv

