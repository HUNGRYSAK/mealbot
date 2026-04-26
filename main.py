import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import os
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# =====================
# 급식 크롤링
# =====================
def get_meal():
    url = "https://www.mmu.ac.kr/main/contents/todayMenu2"

    try:
        res = requests.get(url, timeout=5)
        res.encoding = "utf-8"
    except:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table")

    if not table:
        return []

    rows = table.find_all("tr")
    meals = []

    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        meals.append({
            "date": cols[0].get_text(strip=True),
            "breakfast": cols[1].get_text("\n", strip=True),
            "lunch": cols[2].get_text("\n", strip=True),
            "dinner": cols[3].get_text("\n", strip=True)
        })

    return meals


def find_meal(date):
    meals = get_meal()
    for m in meals:
        if date in m["date"]:
            return m
    return None


# =====================
# 디스코드 봇 설정
# =====================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

CHANNEL_ID = 1492468273101672588


# =====================
# 명령어
# =====================
@bot.command()
async def 밥(ctx):
    now = datetime.now(KST)
    today = f"{now.month}/{now.day}"

    meal = find_meal(today)

    if not meal:
        await ctx.send("오늘 급식 없음")
        return

    await ctx.send(f"📅 {meal['date']}\n\n🍳 아침\n{meal['breakfast']}\n\n🍱 점심\n{meal['lunch']}\n\n🍽️ 저녁\n{meal['dinner']}")


@bot.command()
async def 내일밥(ctx):
    now = datetime.now(KST) + timedelta(days=1)
    tomorrow = f"{now.month}/{now.day}"

    meal = find_meal(tomorrow)

    if not meal:
        await ctx.send("내일 급식 없음")
        return

    await ctx.send(f"📅 {meal['date']}\n\n🍳 아침\n{meal['breakfast']}\n\n🍱 점심\n{meal['lunch']}\n\n🍽️ 저녁\n{meal['dinner']}")


# =====================
# 알림
# =====================
last_morning = None
last_night = None


@tasks.loop(minutes=1)
async def scheduler():
    global last_morning, last_night

    now = datetime.now(KST)
    key = now.strftime("%Y-%m-%d")

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(CHANNEL_ID)

    # 아침 06:30
    if now.hour == 6 and now.minute == 30 and last_morning != key:
        today = f"{now.month}/{now.day}"
        meal = find_meal(today)

        await channel.send("🌅 오늘 급식")
        if meal:
            await channel.send(meal["lunch"])
        else:
            await channel.send("없음")

        last_morning = key

    # 밤 23:00 → 내일
    if now.hour == 23 and now.minute == 0 and last_night != key:
        tomorrow_dt = now + timedelta(days=1)
        tomorrow = f"{tomorrow_dt.month}/{tomorrow_dt.day}"

        meal = find_meal(tomorrow)

        await channel.send("🌙 내일 급식")
        if meal:
            await channel.send(meal["lunch"])
        else:
            await channel.send("없음")

        last_night = key


@bot.event
async def on_ready():
    print(f"{bot.user} 로그인 완료")
    scheduler.start()


bot.run(os.environ["DISCORD_TOKEN"])