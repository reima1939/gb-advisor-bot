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

# 2. 主要キャラの代用データベース（火属性メイン）
SUBSTITUTE_DATABASE = {
    "パーシヴァル（リミテッド）": [
        "アッシュ (奥義・与ダメ補助)",
        "ウィルナス (高火力アタッカー)",
        "水着ミリン (奥義軸のゲージ/火力をカバー)"
    ],
    "ゼタ（リミテッド）": [
        "ユエル (追撃・連続攻撃サポート)",
        "クビラ (アビダメージ・高火力和枠)",
        "スカーサハ (バリア・属性バフサポート)"
    ],
    "ミカエル（リミテッド）": [
        "アトゥム (奥義・上限引き上げ補助)",
        "サテュロス (防御・デバフ短縮・回復)",
        "火属性レ・フィーエ (連撃・耐久サポート)"
    ],
    "ナタク（浴衣）": [
        "ネモネ (奥義・アビ軸の耐久＆火力)",
        "水着クビラ (アビ軸アタッカー)",
        "エルモート (ディスペル・アビダメージ)"
    ]
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
    """神ゲー攻略などの編成URLを解析し、代用キャラ提案付きで表示するコマンド"""
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

        for heading in soup.find_all(['h2', 'h3']):
            heading_text = heading.get_text().strip()
            if not heading_text or len(heading_text) > 40:
                continue
            
            chars = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ['h2', 'h3']:
                    break
                
                for img in sibling.find_all('img'):
                    alt = img.get('alt', '').strip()
                    skip_words = ["神ゲー", "logo", "icon", "banner", "閉じる", "arrow", "menu"]
                    if alt and not any(w.lower() in alt.lower() for w in skip_words):
                        if alt not in chars:
                            chars.append(alt)
                            # 代用データベースに一致するキャラがいるかチェック
                            if alt in SUBSTITUTE_DATABASE and alt not in detected_substitutes:
                                detected_substitutes[alt] = SUBSTITUTE_DATABASE[alt]

            if chars:
                char_list_str = " ".join([f"[{c}]" for c in chars[:6]])
                sections_info.append(f"📌 **{heading_text}**\n 構成: {char_list_str}")

        preview_content = "\n\n".join(sections_info[:4]) if sections_info else "編成セクションが見つかりませんでした"

        # 代用案のテキストを生成
        substitute_text = ""
        if detected_substitutes:
            sub_lines = []
            for target_char, subs in detected_substitutes.items():
                subs_formatted = " / ".join(subs)
                sub_lines.append(f"・**{target_char}** 未所持の場合 ➔ {subs_formatted}")
            substitute_text = "\n\n💡 **おすすめ代用キャラクター案**:\n" + "\n".join(sub_lines)

        message = (
            f"✅ **編成データの解析＆アドバイス**\n"
            f"📄 **ページ名**: `{page_title}`\n\n"
            f"{preview_content}"
            f"{substitute_text}\n\n"
            f"🔗 {clean_url}"
        )
        await ctx.send(message[:2000])

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
