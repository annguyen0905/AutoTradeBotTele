from telethon import TelegramClient, events, sync
import re

# Thay thế bằng API ID và API HASH của bạn
api_id = 26543857
api_hash = '3d3ea5c206b896b8d63e42f814d929a8'

# Số điện thoại bạn dùng Telegram (để đăng nhập)
phone = '+84973621972'

client = TelegramClient('session_name', api_id, api_hash)

# group_id = 1002097468536  # Group ID bạn cung cấp   -

group_id = 1002490224528  # Group ID bạn cung cấp   -

# --- HÀM PARSE TÍN HIỆU ---
def parse_signal_message(message_text):
    lines = message_text.strip().splitlines()
    result = {
        'type': None,
        'symbol': None,
        'entry': None,
        'stop_loss': None,
        'take_profit': None  # Đổi thành một TP duy nhất
    }

    if not lines:
        return result

    # Dòng 1: Long/Short $SYMBOL Entry Market 0.123
    match = re.search(r'(?i)^(Long|Short)\s+\$(\w+)\s+Entry\s+(?:Market\s+)?([\d.]+)', lines[0])
    if match:
        result['type'] = match.group(1).capitalize()
        result['symbol'] = match.group(2).upper()
        result['entry'] = float(match.group(3))
    else:
        print("⚠️ Không đúng định dạng dòng đầu:", lines[0])
        return result

    # Duyệt các dòng tiếp theo
    for line in lines[1:]:
        line = line.strip()
        if result['stop_loss'] is None and line.lower().startswith(('stl', 'sl')):
            match = re.search(r'\d+(?:\.\d+)?', line)
            if match:
                result['stop_loss'] = float(match.group())

        elif result['take_profit'] is None and line.upper().startswith('TP'):
            match = re.search(r'\d+(?:\.\d+)?', line)
            if match:
                result['take_profit'] = float(match.group())
                break  # ✅ Chỉ lấy TP đầu tiên rồi dừng lại

    return result


# --- LẮNG NGHE TIN NHẮN MỚI ---
@client.on(events.NewMessage(chats=group_id))
async def handler(event):
    message = event.message
    text = message.text.strip()

    # ✅ Chỉ xử lý tin nhắn bắt đầu bằng Long/Short
    if not re.match(r'(?i)^(long|short)\s+\$\w+', text):
        return

    # ✅ Lấy tên người gửi hoặc tên kênh
    sender = await message.get_sender()
    if hasattr(sender, 'first_name'):
        sender_name = sender.first_name
    elif hasattr(sender, 'title'):
        sender_name = sender.title
    else:
        sender_name = 'Unknown'

    # ✅ Parse tín hiệu
    signal_data = parse_signal_message(text)

    print(f"\n📥 Tin nhắn mới từ {sender_name} (ID: {message.sender_id}):")
    print(text)
    print("📊 Phân tích lệnh:")
    print(signal_data)
    print("---")


# --- KHỞI ĐỘNG BOT ---
async def main():
    print("🤖 Đang kết nối và lắng nghe tín hiệu trade...")
    await client.start(phone=phone)
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())