# telegram_to_binance_bot.py

from telethon import TelegramClient, events
import time
import requests
import re
import math
from binance.client import Client
from binance.enums import *

ORDER_TYPE_TAKE_PROFIT_MARKET = 'TAKE_PROFIT_MARKET'
ORDER_TYPE_STOP_MARKET = 'STOP_MARKET'

# === CẤU HÌNH TELEGRAM ===
api_id = 26543857         # Điền API ID Telegram
api_hash = '3d3ea5c206b896b8d63e42f814d929a8'   # Điền API HASH Telegram
session_name = 'auto_trade_bot'

# === CẤU HÌNH BINANCE ===
BINANCE_API_KEY = 'gX0PhXo1gTlwIls8IyxkEitqslRJZZeepLg7LVz0QxK4nB0wwCVf6kbPoYtE0ehs'
BINANCE_SECRET = 'xmLSWGqqznkqCBB6T0vjY9TN9CV5UGy7986WL9HRE7vmVTMQKMlnDjgZ14qkDrxE'

# === GROUP TELEGRAM ID CẦN LẮNG NGHE ===
# GROUP_ID = 1002490224528  # === GROUP TELEGRAM TEST ===
GROUP_ID = 1002097468536  # === GROUP TELEGRAM REAL ===
 

# === KHỞI TẠO TELEGRAM CLIENT ===
client = TelegramClient(session_name, api_id, api_hash)

# === KHỞI TẠO BINANCE CLIENT ===
binance_client = Client(BINANCE_API_KEY, BINANCE_SECRET)
binance_client.API_URL = 'https://fapi.binance.com/fapi'


def get_symbol_precision(symbol):
    info = binance_client.futures_exchange_info()
    for s in info['symbols']:
        if s['symbol'] == symbol:
            quantity_precision = 0
            price_precision = 0
            for f in s['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    step_size = f['stepSize']
                    if '.' in step_size:
                        quantity_precision = len(step_size.rstrip('0').split('.')[-1])
                    else:
                        quantity_precision = 0
                if f['filterType'] == 'PRICE_FILTER':
                    tick_size = f['tickSize']
                    if '.' in tick_size:
                        price_precision = len(tick_size.rstrip('0').split('.')[-1])
                    else:
                        price_precision = 0
            return quantity_precision, price_precision
    return 3, 2  # default fallback


def floor_to_precision(value, precision):
    factor = 10 ** precision
    return math.floor(value * factor) / factor


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
            line_lower = line.lower()
            if line_lower.startswith('stl'):
                part = line.split('.', 1)[1].strip()
                signal['stop_loss'] = float(part)
            elif line_lower.startswith('tp1'):
                part = line.split('.', 1)[1].strip()
                signal['take_profit'] = float(part)
        return signal
    except Exception as e:
        print("Error parsing signal:", e)
        return None


def place_future_order(symbol, side, entry, stop_loss=None, take_profit=None, leverage=2):
    try:
        # Set leverage and margin type
        binance_client.futures_change_leverage(symbol=symbol, leverage=leverage)
        try:
            binance_client.futures_change_margin_type(symbol=symbol, marginType='CROSSED')
        except Exception as e:
            if "No need to change margin type" not in str(e):
                raise

        # Get available USDT balance
        acc_info = binance_client.futures_account()
        available_usdt = float(acc_info['availableBalance'])

        safe_ratio = 0.9
        max_position = available_usdt * safe_ratio * leverage / entry

        # Get precisions
        qty_precision, price_precision = get_symbol_precision(symbol)

        # Floor quantity to allowed precision
        quantity = floor_to_precision(max_position, qty_precision)
        entry = round(entry, price_precision)
        if stop_loss:
            stop_loss = round(stop_loss, price_precision)
        if take_profit:
            take_profit = round(take_profit, price_precision)

        if quantity <= 0:
            print("❌ Số lượng đặt lệnh tính ra <= 0, không đặt lệnh.")
            return

        print(f"👉 Đặt lệnh {side.upper()} {symbol}, Qty: {quantity}, Entry: {entry}")

        # Place main limit order
        order = binance_client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY if side == 'long' else SIDE_SELL,
            type=ORDER_TYPE_LIMIT,
            quantity=quantity,
            price=entry,
            timeInForce=TIME_IN_FORCE_GTC
        )
        print("✅ Đã gửi lệnh LIMIT:", order)

        # Stop Loss
        if stop_loss:
            sl_order = binance_client.futures_create_order(
                symbol=symbol,
                side=SIDE_SELL if side == 'long' else SIDE_BUY,
                type=ORDER_TYPE_STOP_MARKET,
                stopPrice=stop_loss,
                closePosition=True,
                timeInForce=TIME_IN_FORCE_GTC
            )
            print(f"📉 Đã đặt STOP LOSS: orderId={sl_order['orderId']}, symbol={sl_order['symbol']}, stopPrice={sl_order['stopPrice']}")

        # Take Profit
        if take_profit:
            tp_order = binance_client.futures_create_order(
                symbol=symbol,
                side=SIDE_SELL if side == 'long' else SIDE_BUY,
                type=ORDER_TYPE_TAKE_PROFIT_MARKET,
                stopPrice=take_profit,
                closePosition=True,
                timeInForce=TIME_IN_FORCE_GTC
            )
            print(f"📈 Đã đặt TAKE PROFIT: orderId={tp_order['orderId']}, symbol={tp_order['symbol']}, stopPrice={tp_order['stopPrice']}")

    except Exception as e:
        print("❌ Lỗi khi đặt lệnh:", e)


@client.on(events.NewMessage(chats=GROUP_ID))
async def handler(event):
    message = event.message
    text = message.message.strip()
    if not (text.lower().startswith('long') or text.lower().startswith('short')):
        return

    sender = await event.get_sender()
    sender_name = sender.first_name if hasattr(sender, 'first_name') else getattr(sender, 'title', 'Unknown')
    print(f"\n📨 Tín hiệu mới từ {sender_name}:\n{text}")

    signal = parse_signal_message(text)
    if signal is None:
        print("⚠️ Không thể phân tích tín hiệu.")
        return

    print(f"📊 Đã phân tích tín hiệu: {signal}")

    symbol = signal['symbol'] + 'USDT'
    entry = signal.get('entry', 0)
    if entry <= 0:
        print("❌ Entry không hợp lệ, bỏ qua tín hiệu.")
        return

    side = signal['type']
    stop_loss = signal.get('stop_loss')
    take_profit = signal.get('take_profit')

    place_future_order(symbol, side, entry, stop_loss, take_profit)


if __name__ == '__main__':
    print("🤖 Bot đang chạy và lắng nghe tín hiệu từ Telegram...")
    client.start()
    client.run_until_disconnected()