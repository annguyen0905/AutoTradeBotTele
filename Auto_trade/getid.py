from telethon import TelegramClient

# Thay thế bằng API ID và API HASH của bạn
api_id = 26543857
api_hash = '3d3ea5c206b896b8d63e42f814d929a8'

# Số điện thoại bạn dùng Telegram (để đăng nhập)
phone = '+84973621972'

client = TelegramClient('session_name', api_id, api_hash)

async def main():
    await client.start(phone=phone)

    print("Danh sách nhóm/kênh bạn đang tham gia:")
    async for dialog in client.iter_dialogs():
        print(f"Name: {dialog.name} - ID: {dialog.id} - Username: {dialog.entity.username}")
    
    # Giả sử bạn đã tìm được ID nhóm bạn muốn
    group_id = 123456789  # thay bằng ID thực từ trên
    entity = await client.get_entity(group_id)

    print(f"\n10 tin nhắn mới nhất trong nhóm {entity.title}:")
    async for message in client.iter_messages(entity, limit=10):
        print(message.sender_id, message.text)

with client:
    client.loop.run_until_complete(main())