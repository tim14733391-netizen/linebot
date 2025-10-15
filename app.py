# app.py
import requests, re, os, random, datetime
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from opencc import OpenCC
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# 
cloudinary.config(
    cloud_name=os.getenv('dzggyowch'),
    api_key=os.getenv('274937855242792'),
    api_secret=os.getenv('nhgd_egk0ymYcOYBKvOvvGvP5Wg')
)

CHANNEL_ACCESS_TOKEN = os.getenv('9TXCvsiRkR6VIonHZGor0TxisiZtkKLIH2UVbiiopK7KSSgNOC/4EVaWb3L8ZuqpkanRwx6zPHFKJIQW4wg2d2MWDPJYG/ztzbFGG6U2kDW3Dp9AtBMXH7dsmCv0qxmrJP0+JsKeZejnfKs/h9ISCAdB04t89/1O/w1cDnyilFU=')
USER_ID = os.getenv('U64f8cb23dc9efd731fdc1d7b144cc38b')

@app.route('/')
def home():
    return "✅ LINE 早安推播服務已啟動！前往 /push 觸發手動推播。"

@app.route('/push')
def push_message():
    try:
        # (1) 取得每日早安句
        url = 'https://blissbies.com/blog/good-morning-greetings-zh/'
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        bs = BeautifulSoup(r.text, 'lxml')
        content = bs.select('h2.wp-block-heading~p~ol>li')
        content_txt = [x.text.strip() for x in content if x.text.strip()]
        if not content_txt:
            raise RuntimeError("無法在目標頁面抓到早安句")

        # (2) 簡體轉繁體
        cc = OpenCC('s2t')
        phrases = [cc.convert(x) for x in content_txt]

        # (3) 產生當日訊息
        today = datetime.datetime.now().strftime("%Y/%m/%d")
        message_text = random.choice(phrases) + "\n" + f"🌞 早安！今天是 {today}"

        # (4) 取得圖片 URL
        sticker_page = "https://sticker.fpg.com.tw/sticker.aspx?sticker_id=200000602"
        r2 = requests.get(sticker_page, timeout=8)
        r2.raise_for_status()
        soup = BeautifulSoup(r2.text, 'lxml')
        img_list = soup.find_all('img')
        pattern = re.compile(r'.+\.jpg$', re.IGNORECASE)
        img_urls = []
        for img in img_list:
            src = img.get('data-original', '') or img.get('src', '')
            if not src:
                continue
            if not src.startswith('http'):
                src = 'https://sticker.fpg.com.tw/' + src.lstrip('/')
            if pattern.match(src):
                img_urls.append(src)
        img_urls = sorted(set(img_urls))
        if not img_urls:
            raise RuntimeError("找不到符合條件的圖片 URL")

        # (5) 隨機選一張 URL，直接交給 Cloudinary remote fetch（Cloudinary 會去抓取）
        selected_url = random.choice(img_urls)
        # cloudinary.uploader.upload 可以直接傳遠端 URL
        upload_result = cloudinary.uploader.upload(selected_url, timeout=60)
        cloud_url = upload_result.get("secure_url")
        if not cloud_url:
            raise RuntimeError("Cloudinary 回傳沒有 secure_url")

        # (6) 傳送 LINE 推播（push）
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }
        payload = {
            "to": USER_ID,
            "messages": [
                {"type": "text", "text": message_text},
                {"type": "image", "originalContentUrl": cloud_url, "previewImageUrl": cloud_url}
            ]
        }
        res = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload, timeout=8)
        # 將外部回應記錄到 Vercel log（print 可在 Dashboard logs 看到）
        print("LINE API status:", res.status_code, "body:", res.text)

        if res.status_code == 200:
            return jsonify({"ok": True, "msg": "推播成功"}), 200
        else:
            return jsonify({"ok": False, "error": res.text}), 500

    except Exception as e:
        # 將完整錯誤顯示於 logs
        print("ERROR in /push:", repr(e))
        return jsonify({"ok": False, "error": str(e)}), 500








