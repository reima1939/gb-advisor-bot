import os
import asyncio
from aiohttp import web
import discord
from discord.ext import commands
from bs4 import BeautifulSoup
import requests

# 1. Renderのポート要件を満たすためのダミーWebサーバー（無料枠用）
async def handle(request):
    return web.Response(text="GranblueAdvisor Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server started on port {port}")

# 2. Discord Botの設定
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("GranblueAdvisor Bot is now online!")

@bot.command()
async def ping(ctx):
    """動作確認用コマンド"""
    await ctx.send("Pong! GranblueAdvisor is working correctly!")

@bot.command()
async def parse(ctx, url: str):
    """GameWithなどの編成URLを解析してデータを抽出するコマンド"""
    await ctx.message.add_reaction("⏳")

    try:
        clean_url = url.strip("<>").strip()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(clean_url, headers=headers, timeout=10)
        if response.status_code != 200:
            await ctx.send(f"❌ ページの取得に失敗しました（ステータスコード: {response.status_code}）")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        page_title = soup.find('title').get_text() if soup.find('title') else "タイトルなし"

        # GameWithの編成ページ内にある画像から、まずはすべてのalt属性を柔軟に収集
        items = []
        for img in soup.find_all('img'):
            alt_text = img.get('alt', '').strip()
            if not alt_text:
                continue

            # 明らかなサイト共通メニューや広告ワードのみピンポイントで除外
            skip_keywords = ["GameWith", "banner", "大バナー", "icon", "App Store", "Google Play"]
            
            if not any(kw.lower() in alt_text.lower() for kw in skip_keywords):
                if alt_text not in items:
                    items.append(alt_text)

        # 抽出されたアイテムリスト（最大20件）
        preview_list = "\n".join([f"・{item}" for item in items[:20]]) if items else "有効なアイテムが見つかりませんでした"

        message = (
            f"✅ **編成データの抽出に成功しました！**\n"
            f"📄 **編成名**: `{page_title}`\n\n"
            f"🎯 **検出された候補（確認用）**:\n"
            f"{preview_list}\n\n"
            f"🔗 {clean_url}"
        )
        await ctx.send(message)

    except Exception as e:
        await ctx.send(f"❌ エラーが発生しました: `{str(e)}`")
        
async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN is not set.")
        return

    await start_web_server()
    
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
