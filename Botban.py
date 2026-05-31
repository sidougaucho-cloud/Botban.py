#!/usr/bin/python3

import asyncio
from typing import NamedTuple
import logging
import threading
from aiohttp import web

from aiogram import Bot, Dispatcher, types, loggers
from aiogram import exceptions
from aiogram.filters.command import Command

logger = logging.getLogger(__name__)

def run_web():
    app = web.Application()
    async def health(request):
        return web.Response(text="OK")
    app.router.add_get('/', health)
    web.run_app(app, port=8080)

threading.Thread(target=run_web, daemon=True).start()

class NameId(NamedTuple):
    name: str
    id: int | str

    def __str__(self):
        return self.name

class BanChannelBot:
    def __init__(self, token):
        bot = Bot(token=token)
        dp = Dispatcher()
        dp.message(Command('banch'))(self.ban_channel)

        self.dp = dp
        self.bot = bot

    async def ban_from_a_group(self, u: types.User, group: NameId, to_ban: NameId) -> str:
        bot = self.bot
        try:
            admins = await bot.get_chat_administrators(group.id)
        except exceptions.TelegramNotFound:
            return f'Erreur : le chat {group} est introuvable.'

        admin_ids = [cm.user.id for cm in admins]
        if u.id not in admin_ids:
            return f'Erreur : vous n\'êtes pas administrateur de {group}.'

        if bot.id not in admin_ids:
            return f'Erreur : je ne suis pas administrateur de {group}.'

        if await bot.ban_chat_sender_chat(chat_id=group.id, sender_chat_id=to_ban.id):
            return f'{to_ban} a été banni de {group}.'
        else:
            return f'Échec du bannissement de {to_ban} de {group}.'

    async def ban_channel(self, msg: types.Message) -> None:
        logger.info('Reçu %s', msg.text)
        bot = self.bot
        _, *parts = msg.text.split()
        if not parts:
            return

        ch, *group_names = parts
        if not group_names:
            groups = [NameId(msg.chat.username, msg.chat.id)]
        else:
            groups = [NameId(x, x) for x in group_names]
        try:
            if ch.startswith('-') and ch[1:].isdigit():
                to_ban = NameId(ch, int(ch))
            elif ch.isdigit():
                to_ban = NameId(ch, int('-100' + ch))
            else:
                chat = await bot.get_chat(chat_id=ch)
                to_ban = NameId(ch, chat.id)
        except exceptions.TelegramNotFound:
            await bot.send_message(
                chat_id=msg.chat.id,
                text=f'Erreur : le chat {ch} est introuvable.',
                reply_to_message_id=msg.message_id,
            )
            return

        reply = []
        for g in groups:
            reply.append(await self.ban_from_a_group(msg.from_user, g, to_ban))

        await bot.send_message(
            chat_id=msg.chat.id,
            text='\n'.join(reply),
            reply_to_message_id=msg.message_id,
        )

    async def run(self) -> None:
        await self.bot.delete_webhook(drop_pending_updates=True)
        await self.dp.start_polling(self.bot)

async def main(bot_token):
    bcbot = BanChannelBot(bot_token)
    await bcbot.run()

if __name__ == '__main__':
    import os, sys

    token = os.environ.pop('TOKEN', None)
    if not token:
        sys.exit('Veuillez fournir le token du bot dans la variable d\'environnement TOKEN.')

    # Ne pas afficher les messages "Update id=... is handled. Duration 16 ms by bot id=..."
    loggers.event.setLevel(logging.WARNING)

    try:
        asyncio.run(main(token))
    except KeyboardInterrupt:
        pass
