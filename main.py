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

# 2. 代表的な主要キャラの代用データベース（全属性共通で拡張可能）
SUBSTITUTE_DATABASE = {
    # 火属性
    "パーシヴァル（リミテッド）": ["アッシュ", "ウィルナス", "水着ミリン"],
    "ゼタ（リミテッド）": ["ユエル", "クビラ", "スカーサハ"],
    "ミカエル（リミテッド）": ["アトゥム", "サテュロス", "火属性レ・フィーエ"],
    "ナタク（浴衣）": ["ネモネ", "水着クビラ", "エルモート"],
    # 他属性も今後ここに追加していくことで対応可能
}

# 3. Discord Botの定義（インテントの設定）
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
    """各種属性の編成URLを解析し、全編成と代用提案を表示するコマンド"""
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

        sections_info = []
        detected_substitutes = {}

        # ページ内のすべての見出し（h2, h3）を走査して全編成をピックアップ
        for heading in soup.find_all(['h2', 'h3']):
            heading_text = heading.get_text().strip()
            # 短すぎるものや無関係そうな長文見出しを除外
            if not heading_text or len(heading_text) > 50 or "まとめ" in heading_text or "おすすめ" in heading_text:
                continue
            
            chars = []
            sub_chars = []
            extras = []

            for sibling in heading.find_next_siblings():
                if sibling.name in ['h2', 'h3']:
                    break # 次の見出しに到達したら終了
                
                # テキストや画像のalt属性からパーツを収集
                for img in sibling.find_all('img'):
                    alt = img.get('alt', '').strip()
                    skip_words = ["神ゲー", "logo", "icon", "banner", "閉じる", "arrow", "menu", "pt", "属性"]
                    if alt and not any(w.lower() in alt.lower() for w in skip_words):
                        if alt not in chars and alt not in sub_chars and alt not in extras:
                            # ミニステルやアビリティ、武器などの特殊パーツの簡易判別
                            if "ミニステル" in alt or "ウロボロス" in alt or "シークレット" in alt:
                                extras.append(alt)
                            else:
                                chars.append(alt)
                                if alt in SUBSTITUTE_DATABASE and alt not in detected_substitutes:
                                    detected_substitutes[alt] = SUBSTITUTE_DATABASE[alt]

            # 有効なパーツが検出されたセクションのみ追加
            if chars or extras:
                main_str = " ".join([f"[{c}]" for c in chars[:6]])
                extra_str = f" | 装備/ﾏﾅﾍﾞﾘ: " + ", ".join(extras) if extras else ""
                sections_info.append(f"📌 **{heading_text}**\n 編成: {main_str}{extra_str}")

        # 制限をなくし、検出されたすべての編成セクションをまとめる
        preview_content = "\n\n".join(sections_info) if sections_info else "編成セクションが見つかりませんでした"

        # 代用案のテキストを生成
        substitute_text = ""
        if detected_substitutes:
            sub_lines = []
            for target_char, subs in detected_substitutes.items():
                subs_formatted = " / ".join(subs)
                sub_lines.append(f"・**{target_char}** 未所持の場合 ➔ {subs_formatted}")
            substitute_text = "\n\n💡 **おすすめ代用キャラクター案**:\n" + "\n".join(sub_lines)

        message = (
            f"✅ **全編成データの解析＆アドバイス**\n"
            f"📄 **ページ名**: `{page_title}`\n\n"
            f"{preview_content}"
            f"{substitute_text}\n\n"
            f"🔗 {clean_url}"
        )

        # Discordのメッセージ長制限（2000文字）を超える場合の分割送信処理
        if len(message) > 1900:
            await ctx.send(message[:1900] + "\n\n*(※文字数制限のため一部省略しました)*")
        else:
            await ctx.send(message)

    except Exception as e:
        await ctx.send(f"❌ エラーが発生しました: `{str(e)}`")

# 4. メインの起動処理
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
