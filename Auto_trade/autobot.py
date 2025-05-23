# telegram_to_mexc_bot.py

from telethon import TelegramClient, events
import time
import hmac
import hashlib
import requests

# === CẤU HÌNH TELEGRAM ===
api_id = 26543857         # Điền API ID Telegram
api_hash = '3d3ea5c206b896b8d63e42f814d929a8'   # Điền API HASH Telegram
session_name = 'auto_trade_bot'

# === CẤU HÌNH MEXC ===
API_KEY = 'mx0vglFdM4I3XQjP7C'
API_SECRET = '2e0c926eaef347ce806d86f641306692'
BASE_URL = 'https://contract.mexc.com'

# === GROUP TELEGRAM ID CẦN LẮNG NGHE ===
GROUP_ID = 1002490224528

# === KHỞI TẠO TELEGRAM CLIENT ===
client = TelegramClient(session_name, api_id, api_hash)


def sign_request(params, secret_key):
    sorted_params = sorted(params.items())
    query = '&'.join([f"{k}={v}" for k, v in sorted_params])
    return hmac.new(secret_key.encode(), query.encode(), hashlib.sha256).hexdigest()

def place_future_order(symbol, price, vol, side, leverage=10):
    endpoint = '/api/v1/private/order/submit'
    url = BASE_URL + endpoint
    timestamp = int(time.time() * 1000)

    params = {
        'api_key': API_KEY,
        'req_time': timestamp,
        'symbol': symbol,
        'price': price,
        'vol': vol,
        'leverage': leverage,
        'side': side,       # 1 = long, 2 = short
        'type': 1           # 1 = market
    }
    params['sign'] = sign_request(params, API_SECRET)
    res = requests.post(url, data=params)
    print(res.json())


def parse_signal_message(text):
    lines = text.strip().splitlines()
    if not lines:
        return None

    signal = {}

    if lines[0].lower().startswith('long'):
        signal['type'] = 'long'
    elif lines[0].lower().startswith('short'):
        signal['type'] = 'short'
    else:
        return None

    try:
        signal['symbol'] = lines[0].split('$')[1].split()[0].strip().upper()
        signal['entry'] = float(lines[0].split()[-1])
        for line in lines:
            if line.lower().startswith('stl'):
                signal['stop_loss'] = float(line.split('.')[-1].strip())
            if line.lower().startswith('tp1'):
                signal['take_profit'] = float(line.split('.')[-1].strip())
        return signal
    except:
        return None


@client.on(events.NewMessage(chats=GROUP_ID))
async def handler(event):
    message = event.message
    sender = await event.get_sender()
    text = message.message.strip()

    if not (text.lower().startswith('long') or text.lower().startswith('short')):
        return

    sender_name = sender.first_name if hasattr(sender, 'first_name') else getattr(sender, 'title', 'Unknown')
    print(f"\n📨 Tín hiệu mới từ {sender_name}:\n{text}\n")

    signal = parse_signal_message(text)
    if signal is None:
        print("⚠️ Không thể phân tích tín hiệu.")
        return

    print(f"📊 Đã phân tích tín hiệu: {signal}")

    # Thực hiện đặt lệnh
    symbol = signal['symbol'] + '_USDT'
    entry = signal['entry']
    side = 1 if signal['type'] == 'long' else 2
    vol = round(20 / entry, 3)  # Giao dịch với 20 USDT, có thể chỉnh lại

    place_future_order(symbol, price=0, vol=vol, side=side)


if __name__ == '__main__':
    print("🤖 Bot đang chạy và lắng nghe tín hiệu từ Telegram...")
    client.start()
    client.run_until_disconnected()