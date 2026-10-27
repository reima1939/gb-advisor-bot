import os
import asyncio
from aiohttp import web
import discord
from discord.ext import commands
from bs4 import BeautifulSoup
import requests

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
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("GranblueAdvisor Bot is now online!")

@bot.command()
async def ping(ctx):
    """動作確認用コマンド"""
    await ctx.send("Pong! GranblueAdvisor is working correctly!")

@bot.command()
async def parse(ctx, url: str):
    """神ゲー攻略などの編成URLを解析してパーティ種類とキャラを抽出するコマンド"""
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

        # 神ゲー攻略の構造に合わせて、見出し（h2, h3）と、そこに紐づくキャラクター要素を抽出
        sections_info = []
        
        for heading in soup.find_all(['h2', 'h3']):
            heading_text = heading.get_text().strip()
            if not heading_text or len(heading_text) > 40:
                continue
            
            # 見出しの次にある要素からキャラ名やアイコンのaltを探索
            chars = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ['h2', 'h3']:
                    break # 次の見出しに到達したら終了
                
                # 画像のalt属性からキャラクター名などを取得
                for img in sibling.find_all('img'):
                    alt = img.get('alt', '').strip()
                    skip_words = ["神ゲー", "logo", "icon", "banner", "閉じる", "arrow", "menu"]
                    if alt and not any(w.lower() in alt.lower() for w in skip_words):
                        if alt not in chars:
                            chars.append(alt)

            # 有効なキャラやパーツが見つかった見出しだけをリストに追加
            if chars:
                char_list_str = " ".join([f"[{c}]" for c in chars[:6]]) # 見やすく整形
                sections_info.append(f"📌 **{heading_text}**\n キャラ等: {char_list_str}")

        preview_content = "\n\n".join(sections_info[:4]) if sections_info else "編成セクションが見つかりませんでした"

        message = (
            f"✅ **編成データの解析に成功しました！**\n"
            f"📄 **ページ名**: `{page_title}`\n\n"
            f"{preview_content}\n\n"
            f"🔗 {clean_url}"
        )
        await ctx.send(message[:2000]) # Discordの文字数制限対策

    except Exception as e:
        await ctx.send(f"❌ エラーが発生しました: `{str(e)}`")

# 3. メインの起動処理
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
