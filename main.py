import os
import asyncio
from aiohttp import web
import discord
from discord.ext import commands

# 1. Renderのポート要件を満たすための軽量Webサーバー
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

# 2. Discord Botの定義（インテントの設定）
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # このログがRenderのログに「1回だけ」表示されているかも重要な確認ポイントです
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("GranblueAdvisor Bot is now online!")

@bot.command()
async def ping(ctx):
    """動作確認用コマンド"""
    await ctx.send("Pong! GranblueAdvisor is working correctly!")

@bot.command()
async def parse(ctx, url: str):
    """シンプルなテスト用コマンド（2重送信チェック用）"""
    await ctx.send(f"✅ 受付しました: {url}")

# 3. メインの起動処理（WebサーバーとBotを安全に同時起動）
async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN is not set.")
        return

    # Webサーバー起動
    await start_web_server()

    # Discord Bot起動（startを使うことで二重接続を防ぐ）
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
