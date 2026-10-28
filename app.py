from datetime import datetime, timedelta, timezone
import json
import os
import random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = "y8IlW1kUPj89iT+su3f10ZbCS01TMlja1/KTMEe7x6iv5KA8ZTJlUprgKb/9h/t0HGVQjUk3LJ78uVDFVS17e5bYcsn/D8dZAMgkD+PKyGZtZPnjmoQrO7b6SJtNiCsYmh8Hvoy5nFfpz65FN/YvvgdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "3e253f14b0e55da927272561a1cc1f0b"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

SUBSCRIPTION_FILE = "subscriptions.json"


def load_subscriptions():
  if os.path.exists(SUBSCRIPTION_FILE):
    with open(SUBSCRIPTION_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  return {}


def save_subscriptions(subs):
  with open(SUBSCRIPTION_FILE, "w", encoding="utf-8") as f:
    json.dump(subs, f, ensure_ascii=False, indent=4)


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

  # 1. 找出使用者輸入的星座
  found_zodiac = None
  for z in ZODIACS:
    if z in user_text:
      found_zodiac = z
      break

  # 2. 簡單抓取時間（例如抓取「10點」、「8點」的數字）
  target_hour = None
  for h in range(23, -1, -1):
    if f"{h}點" in user_text or f"{h} 點" in user_text:
      target_hour = h
      break

  # 如果使用者同時提供了時間跟星座（例如：「10點天蠍座」）
  if found_zodiac and target_hour is not None:
    subs = load_subscriptions()
    # 儲存為字典格式：記錄時間與星座
    subs[user_id] = {"hour": target_hour, "zodiac": found_zodiac}
    save_subscriptions(subs)

    reply_text = (
        f"✅ 設定成功！\n"
        f"⏰ 預定時間：每天 {target_hour} 點\n"
        f"✨ 訂閱星座：{found_zodiac}\n\n"
        f"時間到了之後系統就會自動推播給您喔！"
    )
  else:
    reply_text = (
        "💡 請告訴我您想設定的時間與星座！\n"
        "例如請傳送：「**每天10點推播天蠍座**」或「**8點獅子座**」，"
        "我就會幫您記錄下來喔！"
    )

  line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))


# ⏰ 每小時檢查一次的推播 API (給外部每小時排程呼叫)
@app.route("/api/hourly_check", methods=["GET"])
def hourly_check():
  # 取得台灣現實時間的小時 (UTC+8)
  tz_taiwan = timezone(timedelta(hours=8))
  current_hour = datetime.now(tz_taiwan).hour

  subs = load_subscriptions()
  success_count = 0

  for user_id, data in subs.items():
    # 如果使用者設定的推播時間剛好是現在這個小時
    if isinstance(data, dict) and data.get("hour") == current_hour:
      zodiac = data.get("zodiac")
      lucky_color = random.choice(COLORS)
      lucky_number = random.randint(1, 9)
      today_fortune = random.choice(FORTUNES)

      msg = (
          f"☀️ 【定時專屬星座運勢】 ☀️\n\n"
          f"✨ 星座：{zodiac}\n"
          f"🎨 今日幸運顏色：{lucky_color}\n"
          f"🔢 今日幸運數字：{lucky_number}\n"
          f"💡 今日建議：{today_fortune}"
      )
      try:
        line_bot_api.push_message(user_id, TextSendMessage(text=msg))
        success_count += 1
      except Exception as e:
        print(f"推播失敗給 {user_id}: {e}")

  return (
      f"Hourly check completed. Current hour: {current_hour}, Sent:"
      f" {success_count}",
      200,
  )


if __name__ == "__main__":
  app.run(port=5000)