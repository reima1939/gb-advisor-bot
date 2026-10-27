import os
import discord
from discord.ext import commands
from bs4 import BeautifulSoup
import requests

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
    # ユーザーが待っている間に「処理中」のリアクションをつける
    await ctx.message.add_reaction("⏳")

    try:
        # 1. サイトへアクセスするためのヘッダー（ブラウザになりすます設定）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # 2. ページのHTMLデータを取得
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            await ctx.send(f"❌ ページの取得に失敗しました（ステータスコード: {response.status_code}）")
            return

        # 3. BeautifulSoupでHTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')

        # [重要] ここで解説文などを除外し、編成データが含まれるエリアを狙う
        # ※GameWithの編成ページの構造に合わせてセレクタを後ほど調整します
        
        # 例として、ページのタイトルをまずは確認用に取得してみる
        page_title = soup.find('title').get_text() if soup.find('title') else "タイトルなし"

        # 簡易的なテスト結果をDiscordに返す
        await ctx.send(f"✅ **URLの読み込みに成功しました！**\n📄 ページタイトル: `{page_title}`\n🔗 対象URL: {url}")

    except Exception as e:
        await ctx.send(f"❌ エラーが発生しました: `{str(e)}`")

token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("Error: DISCORD_TOKEN is not set.")
