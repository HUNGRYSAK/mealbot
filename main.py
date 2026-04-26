import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import datetime
import os

# =====================
# 한국 시간 설정
# =====================
KST = datetime.timezone(datetime.timedelta(hours=9))

# =====================
# 1. 급식 크롤링
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


# =====================
# 2. 날짜 찾기
# =====================
def find_meal(date):
    meals = get_meal()
    for m in meals:
        if date in m["date"]:
            return m
    return None


# =====================
# 3. 봇 설정
# =====================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

CHANNEL_ID = 1492468273101672588


# =====================
# 4. 명령어
# =====================
@bot.command()
async def 밥(ctx):
    now = datetime.datetime.now(KST)
    today = f"{now.month}/{now.day}"

    meal = find_meal(today)

    if not meal:
        await ctx.send("오늘 급식 없음")
        return

    await ctx.send(
        f"📅 {meal['date']}\n\n"
        f"🍳 아침\n{meal['breakfast']}\n\n"
        f"🍱 점심\n{meal['lunch']}\n\n"
        f"🍽️ 저녁\n{meal['dinner']}"
    )


@bot.command()
async def 내일밥(ctx):
    now = datetime.datetime.now(KST) + datetime.timedelta(days=1)
    tomorrow = f"{now.month}/{now.day}"

    meal = find_meal(tomorrow)

    if not meal:
        await ctx.send("내일 급식 없음")
        return

    await ctx.send(
        f"📅 {meal['date']}\n\n"
        f"🍳 아침\n{meal['breakfast']}\n\n"
        f"🍱 점심\n{meal['lunch']}\n\n"
        f"🍽️ 저녁\n{meal['dinner']}"
    )


@bot.command()
async def 급식(ctx):
    await ctx.send("!급식이 아니라 !밥을 입력해 병신아")


# =====================
# 5. 주간 UI
# =====================
class WeekView(View):
    def __init__(self, meals):
        super().__init__(timeout=60)
        self.meals = meals[:7]

        for i, meal in enumerate(self.meals):
            button = Button(label=meal["date"])

            async def callback(interaction, i=i):
                m = self.meals[i]
                await interaction.response.send_message(
                    f"📅 {m['date']}\n\n"
                    f"🍳 아침\n{m['breakfast']}\n\n"
                    f"🍱 점심\n{m['lunch']}\n\n"
                    f"🍽️ 저녁\n{m['dinner']}",
                    ephemeral=True
                )

            button.callback = callback
            self.add_item(button)


@bot.command()
async def 주간밥(ctx):
    meals = get_meal()

    if not meals:
        await ctx.send("급식 없음")
        return

    await ctx.send("📅 날짜 선택", view=WeekView(meals))


# =====================
# 6. 자동 알림
# =====================
last_morning = None
last_night = None


@tasks.loop(minutes=1)
async def scheduler():
    global last_morning, last_night

    now = datetime.datetime.now(KST)
    key = now.strftime("%Y-%m-%d")

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        try:
            channel = await bot.fetch_channel(CHANNEL_ID)
        except:
            return

    # 아침 06:30
    if now.hour == 6 and now.minute == 30 and last_morning != key:
        today = f"{now.month}/{now.day}"
        meal = find_meal(today)

        if meal:
            await channel.send(
                f"🌅 오늘 급식\n📅 {meal['date']}\n\n"
                f"🍳 아침\n{meal['breakfast']}\n\n"
                f"🍱 점심\n{meal['lunch']}\n\n"
                f"🍽️ 저녁\n{meal['dinner']}"
            )
        else:
            await channel.send("오늘 급식 없음")

        last_morning = key

    # 밤 23:00 → 내일 급식
    if now.hour == 23 and now.minute == 0 and last_night != key:
        tomorrow_dt = now + datetime.timedelta(days=1)
        tomorrow = f"{tomorrow_dt.month}/{tomorrow_dt.day}"

        meal = find_meal(tomorrow)

        if meal:
            await channel.send(
                f"🌙 내일 급식\n📅 {meal['date']}\n\n"
                f"🍳 아침\n{meal['breakfast']}\n\n"
                f"🍱 점심\n{meal['lunch']}\n\n"
                f"🍽️ 저녁\n{meal['dinner']}"
            )
        else:
            await channel.send("내일 급식 없음")

        last_night = key


# =====================
# 7. 실행
# =====================
@bot.event
async def on_ready():
    print(f"{bot.user} 로그인 완료")

    if not scheduler.is_running():
        scheduler.start()


bot.run(os.environ["DISCORD_TOKEN"])