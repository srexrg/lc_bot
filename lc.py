import discord
from discord.ext import commands
import requests
import random
import os

from dotenv import load_dotenv


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")

@bot.command(
    name="leetcode",
    help="Fetches a random LeetCode problem",
    description="Get a random LeetCode problem. Usage: !leetcode [difficulty]\nDifficulty options: easy, medium, hard"
)
async def leetcode(ctx, difficulty: str = None):

    if not difficulty:
        await ctx.send(
            "💡 **Usage Tips:**\n"
            "• Use `!leetcode easy` for an easy problem\n"
            "• Use `!leetcode medium` for a medium problem\n"
            "• Use `!leetcode hard` for a hard problem\n"
            "• Use `!daily` to get today's problem\n"
            "• Use `!lcsearch <keyword>` to search problems\n"
            "• Use `!lcuser <username>` to view user stats\n"
        )

    try:
        problem = fetch_random_leetcode(difficulty)

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

        embed.add_field(name="Ranking", value=f"#{profile['ranking']}", inline=True)
        for stat in stats:
            if stat["difficulty"] != "All":
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

if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set")
        exit(1)
    bot.run(token)
