#!/usr/bin/env python3

# ParrotBot -- Discord bot for quoting messages.
# Copyright (C) 2017 Martin W.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import discord
import asyncio
import datetime
import re

class ParrotBot(discord.Client):
    """Extend discord.Client with an event listener and additional methods."""

    def __init__(self, *args, **kwargs):
        """
        Extend class attributes of discord.Client.

        Pass all arguments to discord.Client.__init__() and define new class
        attributes.

        Parameters
        ----------
        *args
            Non-keyworded arguments passed to the class upon initialisation.
        **kwargs
            Keyworded arguments passed to the class upon initialisation.
        """
        super(ParrotBot, self).__init__(*args, **kwargs)

        # Regular expression object to recognise quotes.
        self.re_quote = re.compile(r"(?P<author>.*?)\s*>\s*(?P<content>.+)")

        # How many messages are fetched at most by search_message_by_quote().
        self.log_fetch_limit = 100

    async def is_same_user(self, user_obj, user_str):
        """
        Check if a given string represents a given User.

        Check if:
            1. the given string is (the beginning of) the user's id.
            2. the given string is (contained in) the user's full user name.
            3. the given string is (contained in) the user's display name.

        If any of that is true, return True, otherwise return False.

        Parameters
        ----------
        user_obj : discord.User
        user_str : str

        Returns
        -------
        boolean
        """
        user_obj_full_name = user_obj.name + '#' + user_obj.discriminator

        if user_obj.id.find(user_str) == 0 \
        or re.search(user_str, user_obj_full_name, flags=re.IGNORECASE) \
        or re.search(user_str, user_obj.display_name, flags=re.IGNORECASE):
            return True
        else:
            return False

    async def search_message_by_quote(self, quote):
        """
        Finds a quote in a given channel and returns the found Message.

        Fetch an amount of messages older than the given quote from the channel
        the quote originates from, depending on self.log_fetch_limit. Then
        search for a message containing the quote and return it if found. If an
        author is given in the quote, only consider posts of that author. If no
        matching message is found, return None.

        Parameters
        ----------
        quote : discord.Message
            Message object containing a quote from another Message from the
            same channel.

        Returns
        -------
        discord.Message or None
        """
        match = self.re_quote.fullmatch(quote.content).groupdict()

        async for message in self.logs_from( \
            quote.channel, \
            limit=self.log_fetch_limit, \
            before=quote \
        ):
            if not match["author"] \
            or await self.is_same_user(message.author, match["author"]):
                if re.search( \
                    re.escape(match["content"]), \
                    message.content, \
                    flags=re.IGNORECASE \
                ):
                    return message

        return None

    async def create_quote_embed(self, quoting_user, quote):
        """
        Create a discord.Embed object that can then be posted to a channel.

        Generate a label containing the display name of the quoting user, the
        date and time the quoted message was posted on and the time and date it
        was edited, if it was edited.

        Create a new discord.Embed object and map:
            1. the display name of the author of the quote to Embed.author.name
            2. their avatar to Embed.author.icon_url
            3. the quote's content to Embed.description
            4. the label generated earlier to Embed.footer.text
            5. the avatar of the quoting user to Embed.footer.icon_url.
        Return the object.

        Parameters
        ----------
        quoting_user : discord.User
            The user originally quoting the other message.
        quote : discord.Message
            The quoted message.

        Returns
        -------
        discord.Embed
        """
        timedatelabel = quote.timestamp.strftime("%x, %X")

        if quote.edited_timestamp: # Message was edited
            timedatelabel += quote.edited_timestamp.strftime(
                ", edited on %x, %X"
            )

        quote_embed = discord.Embed(description=quote.content)
        quote_embed.set_author(
            name=quote.author.display_name,
            icon_url=quote.author.avatar_url
        )
        quote_embed.set_footer(
            text="%s. Quoted by %s." % (
                timedatelabel, quoting_user.display_name
            ),
            icon_url=quoting_user.avatar_url
        )

        return quote_embed

    async def quote_message(self, quote):
        """
        Try to find the quoted message and post an according embed message.

        Try to find the quoted message by passing quote to
        self.search_message_by_quote(). If a fitting message was found,
        construct an according discord.Embed object and post it to the channel
        the quote originates from, then delete the original quoting message if
        allowed. If no fitting message was found, do nothing.

        Parameters
        ----------
        quote : discord.Message
            Message that could contain a quote from another message.
        """
        quoted_message = await self.search_message_by_quote(quote)

        if quoted_message:
            quote_embed = await self.create_quote_embed(
                quote.author,
                quoted_message
            )

            await self.send_message(quote.channel, embed=quote_embed)

            try:
                await self.delete_message(quote)
            except discord.Forbidden:
                pass


    # Event listeners.

    async def on_ready(self):
        """Print that the bot is ready and list connected servers."""
        print("ParrotBot is ready.")
        print("Connected Servers: %d\n" % (len(self.servers)))

    async def on_server_join(self, server):
        """Print number of connected servers when connecting to a new server."""
        print("Joined Server %s -- %s." % (server.id, server.name))
        print("Connected Servers: %d\n" % (len(self.servers)))

    async def on_server_remove(self, server):
        """Print number of connected servers when leaving a server."""
        print("Left Server %s -- %s." % (server.id, server.name))
        print("Connected Servers: %d\n" % (len(self.servers)))

    async def on_message(self, message):
        """Check if message matches the quotation regex and quote it if so."""
        if self.re_quote.fullmatch(message.content):
            await self.quote_message(message)


# Print GNU GPL notice
print("""ParrotBot  Copyright (C) 2017  Martin W.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.\n""")

# Read API token from token file.
with open("token.txt", "r") as tokenfile:
    api_token = tokenfile.readline().rstrip()

# Initialise client object.
client = ParrotBot()

# Start bot session.
print("Start bot session with token %s" % (api_token))
client.run(api_token)
