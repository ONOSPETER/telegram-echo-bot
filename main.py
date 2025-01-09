from keep_alive import keep_alive
keep_alive()
import time
import asyncio
from telethon.sync import TelegramClient
from telethon import errors
from telethon.sessions import StringSession
import re
import logging

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

class TelegramForwarder:
    def __init__(self, api_id, api_hash, phone_number, session_string=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.session_string = session_string or None
        self.client = TelegramClient(StringSession(self.session_string), api_id, api_hash)

    @staticmethod
    def extract_sui_addresses(text):
        sui_address_regex = r'0x[0-9a-fA-F]{64}::[a-zA-Z0-9_]+::[a-zA-Z0-9_]+'
        matches = re.findall(sui_address_regex, text)
        return matches, bool(matches)

    async def connect_client(self):
        while True:
            try:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    logging.info("User is not authorized. Requesting login code.")
                    try:
                        await self.client.send_code_request(self.phone_number)
                        code = input('Enter the code sent to your phone: ')
                        await self.client.sign_in(self.phone_number, code)
                        # Save session in memory
                        self.session_string = self.client.session.save()
                        logging.info(f"Session saved in memory: {self.session_string}")
                    except errors.SessionPasswordNeededError:
                        password = input('Two-step verification enabled. Enter your password: ')
                        await self.client.sign_in(password=password)
                        self.session_string = self.client.session.save()
                        logging.info(f"Session saved in memory: {self.session_string}")
                    except errors.rpcerrorlist.AuthRestartError as e:
                        logging.error(f"Authentication restart error: {e}")
                        return
                logging.info("Client connected successfully.")
                break
            except errors.FloodWaitError as e:
                logging.warning(f"Flood wait error. Retrying in {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
            except errors.rpcerrorlist.PhoneCodeInvalidError:
                logging.error("Invalid code entered. Please try again.")
                return
            except errors.rpcerrorlist.PhoneCodeExpiredError:
                logging.error("Code expired. Please restart the authentication process.")
                return
            except errors.rpcerrorlist.ResendCodeRequest as e:
                logging.error(f"Code exhausted. Retry after some time: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes before retrying
            except Exception as e:
                logging.error(f"Error during connection: {e}. Retrying in 10 seconds.")
                await asyncio.sleep(10)

    async def forward_messages_to_channel(self, source_chat_id, destination_channel_id, keywords):
        await self.connect_client()
        # (Existing implementation remains unchanged...)

# Function to get API credentials and phone number
def get_credentials():
    api_id = 22573035
    api_hash = "28fe44c4ac64ae8344641ee68d55af4f"
    phone_number = "+2349036259266"
    session_string = None  # Initialize session string as None
    return api_id, api_hash, phone_number, session_string

async def main():
    api_id, api_hash, phone_number, session_string = get_credentials()
    forwarder = TelegramForwarder(api_id, api_hash, phone_number, session_string)

    source_tg_id = int("-1002301121101")
    destination_tg_id = "@nfd_sui_trade_bot"
    keywords = ""

    try:
        await forwarder.connect_client()
        if forwarder.session_string:
            logging.info("Session retained in memory.")
        await forwarder.forward_messages_to_channel(source_tg_id, destination_tg_id, keywords)
    except Exception as e:
        logging.error(f"Unexpected error: {e}. Restarting main loop in 10 seconds.")
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
