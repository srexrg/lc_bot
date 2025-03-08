import discord
from discord.ext import commands
import requests
import groq
import logging
import random
import os
from dotenv import load_dotenv
from discord.ext.commands import cooldown, BucketType
from collections import defaultdict
from datetime import datetime, timedelta,timezone

logging.basicConfig(level=logging.INFO)

class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window  
        self.requests = defaultdict(list)

    def is_rate_limited(self, key):
        now = datetime.now()
 
        self.requests[key] = [
            req_time
            for req_time in self.requests[key]
            if now - req_time < timedelta(seconds=self.time_window)
        ]


        if len(self.requests[key]) >= self.max_requests:
            return True

 
        self.requests[key].append(now)
        return False


user_limiter = RateLimiter(
    max_requests=3, time_window=60
)  # 3 requests per minute per user
global_limiter = RateLimiter(
    max_requests=30, time_window=60
)  # 30 requests per minute globally

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

permissions = discord.Permissions(
    send_messages=True,
    embed_links=True,
    read_messages=True,
    read_message_history=True,
    add_reactions=True,
)

@bot.event
async def on_ready():
    no_of_servers = len(bot.guilds)
    print(f"Bot is on {no_of_servers} servers ")
    server_names = [guild.name for guild in bot.guilds]
    print("Connected to the following servers:")
    for name in server_names:
        print(f"- {name}")

    invite_link = discord.utils.oauth_url(bot.user.id, permissions=permissions)
    logging.info(f"{bot.user} has connected to Discord!")

    logging.info(f"Invite link: {invite_link}")


@bot.event
async def on_command(ctx):
    user = ctx.author  # Get the user object
    user_name = (
        f"{user.name}#{user.discriminator}"  # Format the username and discriminator
    )
    logging.info(f"User {user.id} ({user_name}) used the command: {ctx.command}")


@bot.command(
    name="leetcode",
    help="Fetches a random LeetCode problem",
    description="Get a random LeetCode problem. Usage: !leetcode [difficulty]\nDifficulty options: easy, medium, hard",
)
async def leetcode(ctx, difficulty: str = None):
    valid_difficulties = ["easy", "medium", "hard", "random"]

    if not difficulty or difficulty.lower() not in valid_difficulties:
        await ctx.send(
            "💡 **Usage Tips:**\n"
            "• Use `!leetcode easy` for an easy problem\n"
            "• Use `!leetcode medium` for a medium problem\n"
            "• Use `!leetcode hard` for a hard problem\n"
            "• Use `!leetcode random` for a random difficulty problem\n"
            "• Use `!daily` to get today's problem\n"
            "• Use `!lcsearch <keyword>` to search problems\n"
            "• Use `!lcuser <username>` to view user stats\n"
            "• Use `!lchint <problem-no>` to view user stats\n"
            "• Use `!lccontest` to see upcoming contests\n"
        )
        return

    try:
        actual_difficulty = None if difficulty.lower == "random" else difficulty
        problem = fetch_random_leetcode(actual_difficulty)

        if isinstance(problem, str):
            await ctx.send(f"❌ {problem}")
            return

        embed = discord.Embed(
            title=f"Problem #{problem['number']}: {problem['title']}",
            url=problem["url"],
            color=discord.Color.blue(),
        )
        embed.add_field(name="Difficulty", value=problem["difficulty"], inline=True)
        embed.add_field(
            name="Acceptance Rate", value=problem["acceptance_rate"], inline=True
        )
        embed.add_field(
            name="Total Submissions",
            value=f"{problem['total_submitted']:,}",
            inline=True,
        )

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")


def fetch_random_leetcode(difficulty=None):
    url = "https://leetcode.com/api/problems/all/"
    try:
        response = requests.get(url)
        data = response.json()

        free_problems = [
            {
                "title": problem["stat"]["question__title"],
                "difficulty": problem["difficulty"]["level"],
                "slug": problem["stat"]["question__title_slug"],
                "frontend_id": problem["stat"]["frontend_question_id"],
                "total_submitted": problem["stat"]["total_submitted"],
                "total_acs": problem["stat"]["total_acs"],
            }
            for problem in data["stat_status_pairs"]
            if not problem["paid_only"]
        ]

        if difficulty:
            difficulty_map_reverse = {"easy": 1, "medium": 2, "hard": 3}
            difficulty_level = difficulty_map_reverse.get(difficulty.lower())
            if difficulty_level:
                free_problems = [
                    p for p in free_problems if p["difficulty"] == difficulty_level
                ]
            if not free_problems:
                return "No problems found with specified difficulty"

        problem = random.choice(free_problems)

        problem_url = f"https://leetcode.com/problems/{problem['slug']}"

        difficulty_map = {1: "Easy", 2: "Medium", 3: "Hard"}

        return {
            "number": problem["frontend_id"],
            "title": problem["title"],
            "difficulty": difficulty_map[problem["difficulty"]],
            "url": problem_url,
            "acceptance_rate": f"{problem['total_acs'] / problem['total_submitted'] * 100:.1f}%",
            "total_submitted": problem["total_submitted"],
        }

    except requests.RequestException as e:
        return f"Error fetching problem: {e}"



@bot.command(
    name="lchint",
    help="Get a hint for a LeetCode problem",
    description="Get an AI-generated hint for a LeetCode problem. Usage: !lchint <problem_number>",
)
@commands.cooldown(3, 60, BucketType.user) 
async def get_hint(ctx, problem_number: str):
    # Check rate limits
    user_id = str(ctx.author.id)

    if user_limiter.is_rate_limited(user_id):
        remaining_time = 60  # seconds
        await ctx.send(
            f"⌛ Please wait {remaining_time} seconds before requesting another hint."
        )
        return

    if global_limiter.is_rate_limited("global"):
        await ctx.send(
            "⌛ Bot is currently rate limited. Please try again in a minute."
        )
        return

    try:
        thinking_msg = await ctx.send("🤔 Thinking...")

        url = "https://leetcode.com/api/problems/all/"
        response = requests.get(url)
        data = response.json()

        problem = None
        for p in data["stat_status_pairs"]:
            if str(p["stat"]["frontend_question_id"]) == problem_number:
                problem = p
                break

        if not problem:
            await thinking_msg.edit(
                content=f"❌ Could not find problem #{problem_number}"
            )
            return

        title = problem["stat"]["question__title"]
        slug = problem["stat"]["question__title_slug"]
        problem_url = f"https://leetcode.com/problems/{slug}"

        prompt = f"You are a helpful programming tutor. Give a helpful hint for solving the LeetCode problem '{title}' (#{problem_number}). The hint should guide the user towards the solution without giving it away completely. Keep the hint concise (max 2-3 sentences)."

        client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",  # or another Groq model of your choice
        )
        hint = chat_completion.choices[0].message.content

        embed = discord.Embed(
            title=f"Hint for Problem #{problem_number}: {title}",
            url=problem_url,
            color=discord.Color.green(),
            description=hint,
        )

        user_requests = len(user_limiter.requests[user_id])
        embed.set_footer(text=f"Requests remaining: {3 - user_requests}/3 per minute")

        await thinking_msg.edit(content="", embed=embed)

    except Exception as e:
        if "thinking_msg" in locals():
            await thinking_msg.edit(content=f"❌ An error occurred: {str(e)}")
        else:
            await ctx.send(f"❌ An error occurred: {str(e)}")


@get_hint.error
async def get_hint_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"⌛ This command is on cooldown. Try again in {error.retry_after:.1f} seconds."
        )


@bot.command(
    name="daily",
    help="Fetches today's LeetCode problem",
    description="Get the daily LeetCode challenge problem",
)
async def daily(ctx):
    try:
        url = "https://leetcode.com/graphql"
        query = """
        query questionOfToday {
            activeDailyCodingChallengeQuestion {
                date
                userStatus
                link
                question {
                    acRate
                    difficulty
                    frontendQuestionId: questionFrontendId
                    title
                }
            }
        }
        """
        response = requests.post(url, json={"query": query})
        data = response.json()["data"]["activeDailyCodingChallengeQuestion"]

        embed = discord.Embed(
            title=f"Daily Problem #{data['question']['frontendQuestionId']}: {data['question']['title']}",
            url=f"https://leetcode.com{data['link']}",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Difficulty", value=data["question"]["difficulty"], inline=True
        )
        embed.add_field(
            name="Acceptance Rate",
            value=f"{data['question']['acRate']:.1f}%",
            inline=True,
        )
        embed.add_field(name="Date", value=data["date"], inline=True)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")


@bot.command(
    name="lcsearch",
    help="Search LeetCode problems by keyword",
    description="Search for LeetCode problems containing a specific keyword. Usage: !lcsearch <keyword>",
)
async def search_problem(ctx, *, keyword: str):
    try:
        url = "https://leetcode.com/api/problems/all/"
        response = requests.get(url)
        data = response.json()

        free_problems = [
            {
                "title": problem["stat"]["question__title"],
                "difficulty": problem["difficulty"]["level"],
                "slug": problem["stat"]["question__title_slug"],
                "frontend_id": problem["stat"]["frontend_question_id"],
            }
            for problem in data["stat_status_pairs"]
            if not problem["paid_only"]
        ]

        matches = [p for p in free_problems if keyword.lower() in p["title"].lower()][
            :5
        ]

        if not matches:
            await ctx.send(f"No problems found matching '{keyword}'")
            return

        embed = discord.Embed(
            title=f"Search Results for '{keyword}'", color=discord.Color.blue()
        )

        difficulty_map = {1: "Easy", 2: "Medium", 3: "Hard"}
        for problem in matches:
            problem_url = f"https://leetcode.com/problems/{problem['slug']}"
            embed.add_field(
                name=f"#{problem['frontend_id']} {problem['title']}",
                value=f"Difficulty: {difficulty_map[problem['difficulty']]}\n[Solve]({problem_url})",
                inline=False,
            )

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")


@bot.command(
    name="lcuser",
    help="Get LeetCode user statistics",
    description="View solving statistics for a LeetCode user. Usage: !lcuser <username>",
)
async def user_stats(ctx, username: str):
    try:
        url = "https://leetcode.com/graphql"
        query = """
        query getUserProfile($username: String!) {
            matchedUser(username: $username) {
                submitStats {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                }
                profile {
                    ranking
                    realName
                    userAvatar
                    aboutMe
                    skillTags
                    reputation
                    postViewCount
                    postViewCountDiff
                    solutionCount
                    solutionCountDiff
                    categoryDiscussCount
                    company
                    school
                    websites
                    countryName
                    starRating
                }
            }
        }
        """
        response = requests.post(
            url, json={"query": query, "variables": {"username": username}}
        )
        data = response.json()["data"]["matchedUser"]

        if not data:
            await ctx.send(f"User '{username}' not found")
            return

        stats = data["submitStats"]["acSubmissionNum"]
        profile = data["profile"]

        embed = discord.Embed(
            title=f"LeetCode Stats for {username}",
            url=f"https://leetcode.com/{username}",
            color=discord.Color.gold(),
            description=profile.get("aboutMe", "No bio provided"),
        )

        if profile.get("userAvatar"):
            embed.set_thumbnail(url=profile["userAvatar"])

        if profile.get("realName"):
            embed.add_field(name="Name", value=profile["realName"], inline=True)
        if profile.get("countryName"):
            embed.add_field(name="Country", value=profile["countryName"], inline=True)
        if profile.get("company"):
            embed.add_field(name="Company", value=profile["company"], inline=True)
        if profile.get("school"):
            embed.add_field(name="School", value=profile["school"], inline=True)
        if profile.get("websites"):
            embed.add_field(name="Website", value=profile["websites"][0], inline=True)

        embed.add_field(name="Ranking", value=f"#{profile['ranking']}", inline=True)
        
        total_solved = 0
        for stat in stats:
            if stat["difficulty"] == "All":
                total_solved = stat["count"]
                embed.add_field(
                    name="Total Problems",
                    value=f"**{total_solved} solved**",
                    inline=True
                )
            elif stat["difficulty"] in ["Easy", "Medium", "Hard"]:
                embed.add_field(
                    name=f"{stat['difficulty']} Problems",
                    value=f"{stat['count']} solved",
                    inline=True,
                )

        if profile.get("reputation"):
            embed.add_field(name="Reputation", value=profile["reputation"], inline=True)
        if profile.get("solutionCount"):
            embed.add_field(
                name="Solutions", value=profile["solutionCount"], inline=True
            )

        if profile.get("skillTags"):
            embed.add_field(
                name="Skills",
                value=", ".join(profile["skillTags"][:5]),
                inline=False,
            )

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")


@bot.command(name="lccontest")
async def upcoming_contests(ctx):
    try:
        url = "https://leetcode.com/graphql"
        query = """
        query {
            brightTitle
            currentTimestamp
            allContests {
                title
                startTime
                duration
                titleSlug
            }
        }
        """

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0", 
        }

        response = requests.post(url, json={"query": query}, headers=headers)

        data = response.json()
        contests = data.get("data", {}).get("allContests", [])

        if not contests:
            await ctx.send("No contests found!")
            return

        # Filter future contests
        current_time = int(datetime.now().timestamp())
        future_contests = [
            contest for contest in contests if int(contest["startTime"]) > current_time
        ]

        embed = discord.Embed(
            title="📅 Upcoming LeetCode Contests",
            color=discord.Color.blue(),
            url="https://leetcode.com/contest/",
        )

        for contest in future_contests[:5]:
            contest_info = (
                f"🕒 Starts: <t:{int(contest['startTime'])}:R>\n"
                f"⏱️ Duration: {contest['duration'] // 60} min\n"
                f"🔗 [Contest Link](https://leetcode.com/contest/{contest['titleSlug']})"
            )

            embed.add_field(name=contest["title"], value=contest_info, inline=False)

        embed.set_footer(text="All times are in your local timezone")

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

        print(f"Error details: {str(e)}")


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set")
        exit(1)
    bot.run(token)
