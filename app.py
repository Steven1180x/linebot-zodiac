import json
import os
import random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# ----------------------------------------------------
# 你的金鑰
# ----------------------------------------------------
CHANNEL_ACCESS_TOKEN = "y8IlW1kUPj89iT+su3f10ZbCS01TMlja1/KTMEe7x6iv5KA8ZTJlUprgKb/9h/t0HGVQjUk3LJ78uVDFVS17e5bYcsn/D8dZAMgkD+PKyGZtZPnjmoQrO7b6SJtNiCsYmh8Hvoy5nFfpz65FN/YvvgdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "3e253f14b0e55da927272561a1cc1f0b"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 用 JSON 檔案記錄用戶訂閱的星座
SUBSCRIPTION_FILE = "subscriptions.json"


def load_subscriptions():
  if os.path.exists(SUBSCRIPTION_FILE):
    with open(SUBSCRIPTION_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  return {}


def save_subscriptions(subs):
  with open(SUBSCRIPTION_FILE, "w", encoding="utf-8") as f:
    json.dump(subs, f, ensure_ascii=False, indent=4)


# 簡易星座運勢資料庫
ZODIACS = [
    "白羊座",
    "牡羊座",
    "金牛座",
    "雙子座",
    "巨蟹座",
    "獅子座",
    "處女座",
    "天秤座",
    "天蠍座",
    "射手座",
    "魔羯座",
    "摩羯座",
    "水瓶座",
    "雙魚座",
]
COLORS = ["紅色", "黃色", "藍色", "綠色", "紫色", "白色", "粉紅色"]
FORTUNES = [
    "今天運勢極佳，適合嘗試新事物！",
    "貴人運旺盛，多與人溝通會有意外收穫。",
    "保持平常心，穩紮穩打就能順利過關。",
    "今天適合放鬆心情，適當休息能走更長遠的路。",
    "財運不錯，有小確幸發生的可能！",
]


@app.route("/callback", methods=["POST"])
def callback():
  signature = request.headers.get("X-Line-Signature")
  body = request.get_data(as_text=True)

  try:
    handler.handle(body, signature)
  except InvalidSignatureError:
    abort(400)

  return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
  user_id = event.source.user_id
  user_text = event.message.text.strip()

  # 判斷使用者輸入是否包含星座名稱
  found_zodiac = None
  for z in ZODIACS:
    if z in user_text:
      found_zodiac = z
      break

  if found_zodiac:
    # 🎯 記錄/更新使用者的星座訂閱
    subs = load_subscriptions()
    subs[user_id] = found_zodiac
    save_subscriptions(subs)

    lucky_color = random.choice(COLORS)
    lucky_number = random.randint(1, 9)
    today_fortune = random.choice(FORTUNES)

    reply_text = (
        f"✨【{found_zodiac} 今日運勢指南】✨\n\n"
        f"🎨 幸運顏色：{lucky_color}\n"
        f"🔢 幸運數字：{lucky_number}\n"
        f"💡 今日建議：{today_fortune}\n\n"
        f"✅ (已自動幫您登記每日早安推播喔！)"
    )
  else:
    reply_text = (
        "你好！請輸入你的「星座名字」（例如：天蠍座、獅子座），"
        "我就能為你提供今天的幸運指南，並為你開啟每日早安推播喔！"
    )

  line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))


# ⏰ 每日早安推播 API (給外部排程工具呼叫用)
@app.route("/api/push_daily", methods=["GET"])
def push_daily():
  subs = load_subscriptions()
  success_count = 0

  for user_id, zodiac in subs.items():
    lucky_color = random.choice(COLORS)
    lucky_number = random.randint(1, 9)
    today_fortune = random.choice(FORTUNES)

    msg = (
        f"☀️ 【早安！您的專屬星座運勢】 ☀️\n\n"
        f"✨ 您的星座：{zodiac}\n"
        f"🎨 今日幸運顏色：{lucky_color}\n"
        f"🔢 今日幸運數字：{lucky_number}\n"
        f"💡 今日建議：{today_fortune}"
    )
    try:
      line_bot_api.push_message(user_id, TextSendMessage(text=msg))
      success_count += 1
    except Exception as e:
      print(f"推播失敗給 {user_id}: {e}")

  return f"Daily push sent successfully to {success_count} users!", 200


if __name__ == "__main__":
  app.run(port=5000)