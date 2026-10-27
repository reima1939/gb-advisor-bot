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

        # GameWithの編成ページ特有の「編成データが載っているエリア（例: buildsやparty関連のブロック）」を探索
        # まずはページ内の武器やキャラの画像・要素を安全に絞り込むため、特定のエリアを探します
        items = []
        
        # 編成パーツ画像やテキストが入りやすいテーブルや特定のコンテナをターゲットにする
        # ここでは「編成」や「装備」に関連する名前やalt属性を持つ要素を確実にキャッチします
        for img in soup.find_all('img'):
            alt_text = img.get('alt', '').strip()
            if not alt_text:
                continue

            # 広告やサイトメニュー、明らかに無関係なものを完全に弾く
            skip_keywords = [
                "GameWith", "banner", "大バナー", "icon", "App Store", "Google Play",
                "SSRキャラ評価", "攻略", "マルチバトル", "一覧", "TOP", "検索", "リリース", "キャンペーン"
            ]
            
            # 除外ワードが含まれておらず、かつ名前っぽいもの
            if not any(kw.lower() in alt_text.lower() for kw in skip_keywords):
                # グラブルの武器名・キャラ名にありがちなキーワードが含まれるか、あるいは純粋なパーツ候補として追加
                if alt_text not in items:
                    items.append(alt_text)

        # 抽出されたアイテムリスト（最大15件）
        preview_list = "\n".join([f"・{item}" for item in items[:15]]) if items else "編成アイテムが見つかりませんでした"

        message = (
            f"✅ **編成データの抽出テストに成功しました！**\n"
            f"📄 **編成名**: `{page_title}`\n\n"
            f"🎯 **検出されたパーツ候補**:\n"
            f"{preview_list}\n\n"
            f"🔗 {clean_url}"
        )
        await ctx.send(message)

    except Exception as e:
        await ctx.send(f"❌ エラーが発生しました: `{str(e)}`")

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
