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

# 2. キャラクターごとの代用データベース（完全一致のみ提案）
CHARACTER_SUBSTITUTES = {
    "パーシヴァル（リミテッド）": ["アッシュ", "ウィルナス", "水着ミリン"],
    "ゼタ（リミテッド）": ["ユエル", "クビラ", "スカーサハ"],
    "ミカエル（リミテッド）": ["アトゥム", "サテュロス", "火属性レ・フィーエ"],
    "ナタク（浴衣）": ["ネモネ", "水着クビラ", "エルモート"],
    "ウィルナス（リミテッド）": ["アシュラ", "スカーサハ", "ラインハルザ"],
}

# 3. Discord Botの定義
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("GranblueAdvisor Bot is now online!")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! GranblueAdvisor is working correctly!")

@bot.command()
async def parse(ctx, url: str):
    """編成ページを解析し、分割送信＆厳密な代用アドバイスを表示するコマンド"""
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

        # 除外する見出しキーワード
        exclude_heading_keywords = [
            "最強", "古戦場", "関連記事", "パーティ編成", "おすすめキャラ", 
            "マグナ", "アグニス", "シヴァ", "肉集め", "TOP", "まとめ"
        ]

        for heading in soup.find_all(['h2', 'h3']):
            heading_text = heading.get_text().strip()
            if not heading_text or len(heading_text) > 40:
                continue
            
            if any(kw in heading_text for kw in exclude_heading_keywords):
                continue

            chars = []
            extras = []
            section_subs = []

            for sibling in heading.find_next_siblings():
                if sibling.name in ['h2', 'h3']:
                    break
                
                # 画像altからキャラクター抽出
                for img in sibling.find_all('img'):
                    alt = img.get('alt', '').strip()
                    skip_words = ["神ゲー", "logo", "icon", "banner", "閉じる", "arrow", "menu", "pt", "属性", "武器", "召喚石"]
                    if alt and not any(w.lower() in alt.lower() for w in skip_words):
                        if alt not in chars and alt not in extras:
                            if "ミニステル" in alt or "ウロボロス" in alt or "シークレット" in alt:
                                extras.append(alt)
                            else:
                                chars.append(alt)

                # テキスト（EXアビリティなど）の収集
                for text_elem in sibling.find_all(['span', 'a', 'p', 'div']):
                    txt = text_elem.get_text().strip()
                    if txt in ["ミゼラブルミスト", "クリアオール", "無明斬", "羅喉阿修羅陣", "薪割り", "薫風とさえずり", "ワイルドマギカ"]:
                        if txt not in chars and txt not in extras:
                            chars.append(txt)

            # その編成に含まれるキャラに対してのみ代用案を生成（厳密化）
            for target_char in chars:
                if target_char in CHARACTER_SUBSTITUTES:
                    subs_str = " / ".join(CHARACTER_SUBSTITUTES[target_char])
                    section_subs.append(f"└ 💡 {target_char}の代用: {subs_str}")

            if chars:
                main_str = " ".join([f"[{c}]" for c in chars[:8]])
                extra_str = f" | ﾏﾅﾍﾞﾘ/装備: " + ", ".join(extras) if extras else ""
                sub_advice_str = "\n" + "\n".join(section_subs) if section_subs else ""
                
                sections_info.append(f"📌 **{heading_text}**\n 編成: {main_str}{extra_str}{sub_advice_str}")

        if not sections_info:
            await ctx.send("❌ 有効な編成セクションが見つかりませんでした。")
            return

        # ヘッダーメッセージ
        await ctx.send(f"✅ **全編成データの解析結果**\n📄 **ページ名**: `{page_title}`\n🔗 {clean_url}\n---")

        # 2,000文字制限対策：メッセージを安全な長さ（約1,500文字単位）で分割送信
        current_chunk = ""
        for sec in sections_info:
            if len(current_chunk) + len(sec) + 2 > 1700:
                await ctx.send(current_chunk)
                current_chunk = sec
            else:
                if current_chunk:
                    current_chunk += "\n\n" + sec
                else:
                    current_chunk = sec
        
        if current_chunk:
            await ctx.send(current_chunk)

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
