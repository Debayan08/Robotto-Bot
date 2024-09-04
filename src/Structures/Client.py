import pyrogram
from pyromod import Client
from pyrogram import raw, utils, enums, types
from Helpers.Utils import Utils
import hashlib
from datetime import datetime
from typing import Union, List, Optional


class SuperClient(Client):
    def __init__(self, name: str, api_id: int, api_hash: str, bot_token: str, prefix: str):
        super().__init__(name=name, api_id=api_id, api_hash=api_hash,
                         bot_token=bot_token)
        self.prifix = prefix
        self.callback_data_map = {}
        self.utils = Utils()

    async def admincheck(self, message):
        isadmin = await self.get_chat_member(message.chat.id, message.from_user.id)
        return isadmin.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]

    async def send_message(
        self: "pyrogram.Client",
        chat_id: Union[int, str],
        text: str,
        buttons=None,
        parse_mode: Optional["enums.ParseMode"] = None,
        entities: List["types.MessageEntity"] = None,
        disable_web_page_preview: bool = None,
        disable_notification: bool = None,
        reply_to_message_id: int = None,
        schedule_date: datetime = None,
        protect_content: bool = None
    ):

        message, entities = (await utils.parse_text_entities(self, text, parse_mode, entities)).values()

        reply_markup = None

        if buttons:
            for button in buttons:
                original_data = button['callback_data']
                hash_object = hashlib.sha256(original_data.encode())
                hash_key = hash_object.hexdigest()[:10]
                self.callback_data_map[hash_key] = original_data
                button['callback_data'] = hash_key

            reply_markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(
                button['text'], callback_data=button['callback_data'])] for button in buttons])

        r = await self.invoke(
            raw.functions.messages.SendMessage(
                peer=await self.resolve_peer(chat_id),
                no_webpage=disable_web_page_preview or None,
                silent=disable_notification or None,
                reply_to_msg_id=reply_to_message_id,
                random_id=self.rnd_id(),
                schedule_date=utils.datetime_to_timestamp(schedule_date),
                reply_markup=await reply_markup.write(self) if reply_markup else None,
                message=message,
                entities=entities,
                noforwards=protect_content
            )
        )

        if isinstance(r, raw.types.UpdateShortSentMessage):
            peer = await self.resolve_peer(chat_id)

            peer_id = (
                peer.user_id
                if isinstance(peer, raw.types.InputPeerUser)
                else -peer.chat_id
            )

            return types.Message(
                id=r.id,
                chat=types.Chat(
                    id=peer_id,
                    type=enums.ChatType.PRIVATE,
                    client=self
                ),
                text=message,
                date=utils.timestamp_to_datetime(r.date),
                outgoing=r.out,
                reply_markup=reply_markup,
                entities=[
                    types.MessageEntity._parse(None, entity, {})
                    for entity in entities
                ] if entities else None,
                client=self
            )

        for i in r.updates:
            if isinstance(i, (raw.types.UpdateNewMessage,
                              raw.types.UpdateNewChannelMessage,
                              raw.types.UpdateNewScheduledMessage)):
                return await types.Message._parse(
                    self, i.message,
                    {i.id: i for i in r.users},
                    {i.id: i for i in r.chats},
                    is_scheduled=isinstance(
                        i, raw.types.UpdateNewScheduledMessage)
                )
