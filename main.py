from keep_alive import keep_alive
keep_alive()

import time
import asyncio
from telethon.sync import TelegramClient
from telethon import errors
from telethon.tl.types import ChannelParticipantsAdmins
import re

class TelegramForwarder:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient('session_' + phone_number, api_id, api_hash)

    @staticmethod
    def extract_sui_addresses(text):
        # Regex for Sui contract addresses
        sui_address_regex = r'0x[0-9a-fA-F]{64}::[a-zA-Z0-9_]+::[a-zA-Z0-9_]+'
        matches = re.findall(sui_address_regex, text)
        return matches, bool(matches)

    async def connect_client(self):
        while True:
            try:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    await self.client.send_code_request(self.phone_number)
                    try:
                        await self.client.sign_in(self.phone_number, input('Enter the code: '))
                    except errors.rpcerrorlist.SessionPasswordNeededError:
                        password = input('Two-step verification is enabled. Enter your password: ')
                        await self.client.sign_in(password=password)
                print("Client connected successfully.")
                break
            except errors.FloodWaitError as e:
                print(f"Flood wait error. Retrying in {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"Error during connection: {e}. Retrying in 10 seconds.")
                await asyncio.sleep(10)

    async def list_chats(self):
        await self.connect_client()
        dialogs = await self.client.get_dialogs()
        with open(f"chats_of_{self.phone_number}.txt", "w", encoding="utf-8") as chats_file:
            for dialog in dialogs:
                print(f"Chat ID: {dialog.id}, Title: {dialog.title}")
                chats_file.write(f"Chat ID: {dialog.id}, Title: {dialog.title} \n")
        print("List of groups printed successfully!")

    async def get_chats(self, keywords):
        await self.connect_client()
        dialogs = await self.client.get_dialogs()
        for dialog in dialogs:
            if dialog.title and any(keyword in dialog.title.lower() for keyword in keywords):
                print(f"Chat ID: {dialog.id}, Title: {dialog.title}")
                return dialog

    async def forward_messages_to_channel(self, source_chat_id, destination_channel_id, keywords):
        await self.connect_client()
        last_message_id = (await self.client.get_messages(source_chat_id, limit=1))[0].id
        admins = await self.client.get_participants(source_chat_id, filter=ChannelParticipantsAdmins)
        admin_details = [(admin.id, admin.first_name or admin.username or "No Name") for admin in admins]
        
        # Print the admin details (ID and Name pairs)
        bot_ids = [7845011793, 7517160605, 5434266369, 609517172, 6868734170]
        admin_ids = [admin.id for admin in admins]  
		# Assuming this is your original admin_ids list
		
        for admin_id, admin_name in admin_details:
        	print(f"Admin ID: {admin_id}, Admin Name: {admin_name}")
        # Remove bot IDs from the admin_ids list
        admin_ids = [admin_id for admin_id in admin_ids if admin_id not in bot_ids]
        print(admin_ids)  # Updated list without the bot IDs

        while True:
            try:
                print("Checking for messages and forwarding them...")
                messages = await self.client.get_messages(source_chat_id, min_id=last_message_id, limit=None)
                for message in reversed(messages):
                    if hasattr(message, 'text'):
                        CA, Flag = TelegramForwarder.extract_sui_addresses(message.text)
                        sender = await message.get_sender()
                        if Flag and sender and sender.id in admin_ids:
                            print(f"Message contains a contract address: {message.text}")
                            nfdbot_entity = await self.client.get_entity("@nfd_sui_trade_bot")
                            await self.client.send_message(nfdbot_entity, "\n".join(CA))
                            print("Contract address", CA, "forwarded")
                        else:
                            print("No CA in", message.text)
                    last_message_id = max(last_message_id, message.id)
                await asyncio.sleep(5)
            except errors.FloodWaitError as e:
                print(f"Flood wait error. Retrying in {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"Error during message forwarding: {e}. Retrying in 10 seconds.")
                await asyncio.sleep(10)

# Function to read credentials from file
def read_credentials():
    api_id = 22573035
    api_hash = "28fe44c4ac64ae8344641ee68d55af4f"
    phone_number = "+2349036259266"
    return api_id, api_hash, phone_number

# Function to write credentials to file
def write_credentials(api_id, api_hash, phone_number):
    with open("credentials.txt", "w") as file:
        file.write(api_id + "\n")
        file.write(api_hash + "\n")
        file.write(phone_number + "\n")

async def main():
    api_id, api_hash, phone_number = read_credentials()
    if not all([api_id, api_hash, phone_number]):
        api_id = input("Enter your API ID: ")
        api_hash = input("Enter your API Hash: ")
        phone_number = input("Enter your phone number: ")
        write_credentials(api_id, api_hash, phone_number)

    forwarder = TelegramForwarder(api_id, api_hash, phone_number)
    source_tg_id =  int("-1002301121101")
    destination_tg_id = "@nfd_sui_trade_bot"
    keywords = ""

    while True:
        try:
            print("Hey Lex!!")
            await forwarder.forward_messages_to_channel(source_tg_id, destination_tg_id, keywords)
        except Exception as e:
            print(f"Unexpected error: {e}. Restarting main loop in 10 seconds.")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
