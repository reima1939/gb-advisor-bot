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

# 2. キャラクターごとの代用データベース（個別紐付け用）
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
    """編成ページを解析し、ノイズを除外して編成ごとの詳細と個別代用案を表示するコマンド"""
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

        # 除外すべき見出しのキーワード（最強キャラ、古戦場、関連記事、メニューなどを弾く）
        exclude_heading_keywords = [
            "最強", "古戦場", "関連記事", "パーティ編成", "おすすめキャラ", 
            "マグナ", "アグニス", "シヴァ", "肉集め", "TOP", "まとめ"
        ]

        for heading in soup.find_all(['h2', 'h3']):
            heading_text = heading.get_text().strip()
            if not heading_text or len(heading_text) > 40:
                continue
            
            # ノイズとなる見出しをスキップ
            if any(kw in heading_text for kw in exclude_heading_keywords):
                continue

            chars = []
            extras = []
            section_subs = []

            for sibling in heading.find_next_siblings():
                if sibling.name in ['h2', 'h3']:
                    break
                
                # 画像やテキスト要素から情報を広く収集
                for img in sibling.find_all('img'):
                    alt = img.get('alt', '').strip()
                    skip_words = ["神ゲー", "logo", "icon", "banner", "閉じる", "arrow", "menu", "pt", "属性", "武器", "召喚石"]
                    if alt and not any(w.lower() in alt.lower() for w in skip_words):
                        if alt not in chars and alt not in extras:
                            if "ミニステル" in alt or "ウロボロス" in alt or "シークレット" in alt:
                                extras.append(alt)
                            else:
                                chars.append(alt)
                                # この編成に含まれているキャラに対する代用案をチェック
                                if alt in CHARACTER_SUBSTITUTES and alt not in section_subs:
                                    section_subs.append((alt, CHARACTER_SUBSTITUTES[alt]))

                # テキストベース（EXアビリティや細かいパーツ名など）も逃さず拾う
                # ※HTMLの構造でテキストとして入っているアビリティ名などもここでキャッチ
                for text_elem in sibling.find_all(['span', 'a', 'p', 'div']):
                    txt = text_elem.get_text().strip()
                    # アビリティや特定名称っぽいものを簡易判定して追加（長すぎる文章は弾く）
                    if txt in ["ミゼラブルミスト", "クリアオール", "無明斬", "羅喉阿修羅陣", "薪割り", "薫風とさえずり", "ワイルドマギカ"]:
                        if txt not in chars and txt not in extras:
                            chars.append(txt)

            # 有効なパーティ情報がある場合のみ追加
            if chars:
                main_str = " ".join([f"[{c}]" for c in chars[:8]]) # 少し長めの枠も対応
                extra_str = f" | ﾏﾅﾍﾞﾘ/装備: " + ", ".join(extras) if extras else ""
                
                # この編成独自の代用案テキストを作成
                sub_text_parts = []
                if section_subs:
                    for char_name, subs in section_subs:
                        subs_str = " / ".join(subs)
                        sub_text_parts.append(f"└ 💡 {char_name}の代用: {subs_str}")
                
                sub_advice_str = "\n" + "\n".join(sub_text_parts) if sub_text_parts else ""
                
                sections_info.append(f"📌 **{heading_text}**\n 編成: {main_str}{extra_str}{sub_advice_str}")

        preview_content = "\n\n".join(sections_info) if sections_info else "編成セクションが見つかりませんでした"

        message = (
            f"✅ **編成データの解析＆個別代用アドバイス**\n"
            f"📄 **ページ名**: `{page_title}`\n\n"
            f"{preview_content}\n\n"
            f"🔗 {clean_url}"
        )

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
