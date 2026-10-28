import json
import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 從環境變數讀取 LINE Bot 金鑰
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 訂閱資料儲存檔案
SUBSCRIPTION_FILE = "subscriptions.json"

def load_subscriptions():
    if not os.path.exists(SUBSCRIPTION_FILE):
        return {}
    try:
        with open(SUBSCRIPTION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_subscriptions(subs):
    with open(SUBSCRIPTION_FILE, "w", encoding="utf-8") as f:
        json.dump(subs, f, ensure_ascii=False, indent=4)

# 模擬星座運勢的函式（你可以替換成你的爬蟲或 AI 生成邏輯）
def get_zodiac_fortune(zodiac):
    return f"✨ 【{zodiac}今日運勢】 ✨\n整體運勢：★★★★☆\n愛情運勢：運勢平穩，適合與心儀對象多交流。\n財運：偏財運不錯，但避免衝動消費。\n幸運色：藍色\n今天也要保持好心情喔！"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_text = event.message.text.strip()
    
    zodiacs = ["白羊座", "金牛座", "雙子座", "巨蟹座", "獅子座", "處女座", "天秤座", "天蠍座", "射手座", "摩羯座", "水瓶座", "雙魚座"]
    
    # 判斷邏輯 1：如果使用者只是單純打星座（例如「天蠍座」），或是沒有包含設定關鍵字
    if user_text in zodiacs or ("推播" not in user_text and "點" not in user_text):
        matched_zodiac = None
        for z in zodiacs:
            if z in user_text:
                matched_zodiac = z
                break
        
        if matched_zodiac:
            reply_text = get_zodiac_fortune(matched_zodiac)
        else:
            reply_text = "💡 請輸入正確的星座名稱（例如：天蠍座）來查詢運勢，或是設定每日推播（例如：每天10點推播天蠍座）！"

    # 判斷邏輯 2：包含「推播」或「點」，代表要設定定時推播
    else:
        # 從 23 倒數到 0 檢查，避免數字包含關係出錯（例如 10 包含 0）
        target_hour = None
        for h in range(23, -1, -1):
            if f"{h}點" in user_text or f"{h} 點" in user_text:
                target_hour = h
                break
                
        # 抓取星座
        target_zodiac = None
        for z in zodiacs:
            if z in user_text:
                target_zodiac = z
                break

        if target_hour is not None and target_zodiac is not None:
            # 讀取現有訂閱並更新
            subs = load_subscriptions()
            subs[user_id] = {
                "hour": target_hour,
                "zodiac": target_zodiac
            }
            save_subscriptions(subs)
            
            reply_text = f"✅ 設定成功！\n⏰ 預定時間：每天 {target_hour} 點\n✨ 訂閱星座：{target_zodiac}\n\n時間到了之後系統就會自動推播給您喔！"
        else:
            reply_text = "💡 請告訴我您想設定的時間與星座！\n例如請傳送：「**每天10點推播天蠍座**」，我就會幫您記錄下來喔！"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# 讓外部排程（如 cron-job.org）每小時戳一次的路由
@app.route("/api/hourly_check", methods=["GET"])
def hourly_check():
    from datetime import datetime
    import pytz
    
    # 取得台灣當前時間的小時
    tz = pytz.timezone("Asia/Taipei")
    current_hour = datetime.now(tz).hour
    
    subs = load_subscriptions()
    pushed_count = 0
    
    for user_id, data in subs.items():
        if data.get("hour") == current_hour:
            zodiac = data.get("zodiac")
            fortune_msg = f"🔔 【定時運勢推播】\n" + get_zodiac_fortune(zodiac)
            try:
                line_bot_api.push_message(user_id, TextSendMessage(text=fortune_msg))
                pushed_count += 1
            except Exception as e:
                print(f"推播失敗 (User: {user_id}): {e}")
                
    return f"Hourly check completed. Current hour: {current_hour}. Pushed count: {pushed_count}"

if __name__ == "__main__":
    app.run()