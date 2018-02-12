#!/usr/bin/env python3

# ParrotBot -- Discord bot for quoting messages.
# Copyright (C) 2018 Martin Wurm
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
import time
import datetime
import json
import re
import urllib.request

class ParrotBot(discord.Client):
    """Extend discord.Client with an event listener and additional methods."""

    def __init__(self, config, *args, **kwargs):
        """
        Extend class attributes of discord.Client.

        Pass all arguments except for config to discord.Client.__init__() and
        define new class attributes.

        Parameters
        ----------
        configs : dict
            Configuration object for the bot, created from the Configuration
            file. Gets turned into a class attribute.
        *args
            Non-keyworded arguments passed to the class upon initialisation.
        **kwargs
            Keyworded arguments passed to the class upon initialisation.
        """
        super(ParrotBot, self).__init__(*args, **kwargs)

        # Configuration object.
        self.config = config

        # How many messages are fetched at most by search_message_by_quote().
        self.log_fetch_limit = 100

        # Will be set to True after initialisation.
        self.initialised = False

    async def post_server_count(self):
        """
        Post how many servers are connected to Discord bot list sites.

        Create a JSON string containing how many servers are connected right
        now and post it to discordbots.org and bots.discord.pw using the
        respective tokens from the config file. If the token for a site is not
        given, ignore that site.
        """
        count_json = json.dumps({
            "server_count": len(self.servers)
        })

        # discordbots.org
        if self.config["discordbots_org_token"]:
            # Resolve HTTP redirects
            dbotsorg_redirect_url = urllib.request.urlopen(
                "http://discordbots.org/api/bots/%s/stats" % (self.user.id)
            ).geturl()

            # Construct request and post server count
            dbotsorg_req = urllib.request.Request(dbotsorg_redirect_url)

            dbotsorg_req.add_header(
                "Content-Type",
                "application/json"
            )
            dbotsorg_req.add_header(
                "Authorization",
                self.config["discordbots_org_token"]
            )

            urllib.request.urlopen(dbotsorg_req, count_json.encode("ascii"))

        # bots.discord.pw
        if self.config["bots_discord_pw_token"]:
            # Resolve HTTP redirects
            botsdpw_redirect_url_req = urllib.request.Request(
                "http://bots.discord.pw/api/bots/%s/stats" % (self.user.id)
            )

            botsdpw_redirect_url_req.add_header(
                "Authorization",
                self.config["bots_discord_pw_token"]
            )

            botsdpw_redirect_url = urllib.request.urlopen(
                botsdpw_redirect_url_req
            ).geturl()

            # Construct request and post server count
            botsdpw_req = urllib.request.Request(botsdpw_redirect_url)

            botsdpw_req.add_header(
                "Content-Type",
                "application/json"
            )
            botsdpw_req.add_header(
                "Authorization",
                self.config["bots_discord_pw_token"]
            )

            urllib.request.urlopen(botsdpw_req, count_json.encode("ascii"))

    async def is_same_user(self, user_obj, user_str):
        """
        Check if a given string represents a given User.

        If the string resembles a mention string, truncate it so that only
        the user ID is left.

        Then, check if:
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
        # If user_str is a mention string, replace it by just the ID contained
        # in it
        mention_search_result = self.re_user_mention.search(user_str)

        if mention_search_result:
            user_str = mention_search_result.group("ID")

        # Escape user input
        user_str = re.escape(user_str)

        user_obj_full_name = user_obj.name + '#' + user_obj.discriminator

        if user_obj.id.find(user_str) == 0 \
        or re.search(user_str, user_obj_full_name, flags=re.IGNORECASE) \
        or re.search(user_str, user_obj.display_name, flags=re.IGNORECASE):
            return True
        else:
            return False

    async def search_message_by_quote(self, quote, partial=False):
        """
        Finds a quote in a given channel and returns the found Message.

        Fetch an amount of messages older than the given quote from the channel
        the quote originates from, depending on self.log_fetch_limit. Then
        search for a message containing the quote or one whose ID begins with
        the quote string and return it if found. If an author is given in the
        quote, only consider posts of that author. If no matching message is
        found, return None.

        Parameters
        ----------
        quote : discord.Message
            Message object containing a quote from another Message from the
            same channel.
        partial : boolean
            [Optional] Whether the quote being dealt with is a partial one.

        Returns
        -------
        discord.Message or None
        """
        if partial:
            match = self.re_partial_quote.fullmatch(quote.content).groupdict()
        else:
            match = self.re_quote.fullmatch(quote.content).groupdict()

        async for message in self.logs_from(
            quote.channel,
            limit=self.log_fetch_limit,
            before=quote
        ):
            if not match["author"] \
            or await self.is_same_user(message.author, match["author"]):
                if not message.author.bot \
                and not message.content.startswith(">") \
                and (message.id.find(match["content"]) == 0 and not partial \
                or re.search(
                    re.escape(match["content"]),
                    message.content,
                    flags=re.IGNORECASE
                )):
                    return message

        return None

    async def timedelta_timestamp_string(self, timedelta):
        """
        Generate a string that expresses a time difference in words.

        Calculate the time difference of a given timedate.timedelta object in
        years, days, hours, minutes, and seconds and return a string expressing
        that in a natural way.

        Parameters
        ----------
        timedelta : timedate.timedelta
            The time difference that should be expressed in words.

        Returns
        -------
        str
        """
        days = timedelta.days

        years = days // 365
        days -= years * 365

        seconds = timedelta.seconds

        minutes = seconds // 60
        seconds -= minutes * 60

        hours = minutes // 60
        minutes -= hours * 60

        timedelta_string = ""

        if years > 0:
            timedelta_string += str(years) + " years"

            # Was this the last element to be printed? If not ...
            if days + hours + minutes + seconds > 0:
                timedelta_string += " and "
            if days + hours + minutes + seconds > 0:
                # Was this the second last element to be printed? If so ...
                if hours + minutes + seconds == 0:
                    timedelta_string += " and "
                else:
                    timedelta_string += ", "

        if days > 0:
            timedelta_string += str(days) + " days"

            # Was this the last element to be printed? If not ...
            if hours + minutes + seconds > 0:
                # Was this the second last element to be printed? If so ...
                if minutes + seconds == 0:
                    timedelta_string += " and "
                else:
                    timedelta_string += ", "

        if hours > 0:
            timedelta_string += str(hours) + " hours"

            # Was this the last element to be printed? If not ...
            if minutes + seconds > 0:
                # Was this the second last element to be printed? If so ...
                if seconds == 0:
                    timedelta_string += " and "
                else:
                    timedelta_string += ", "

        if minutes > 0:
            timedelta_string += str(minutes) + " minutes"

            # Was this the last element to be printed? If not ...
            if days + hours + minutes + seconds > 0:
                timedelta_string += " and "

        if seconds > 0:
            timedelta_string += str(seconds) + " seconds"

        return timedelta_string

    async def create_quote_embed(self, quoting_user, quote, alt=None):
        """
        Create a discord.Embed object that can then be posted to a channel.

        Generate a label containing the display name of the quoting user,
        whether the quoted message has been edited and how much time has passed
        between when the message has been sent and when it was edited.

        Create a new discord.Embed object and map:
            1. the display name of the author of the quote to Embed.author.name
            2. their avatar to Embed.author.icon_url
            3. the quote's content (or alt, if given) to Embed.description
            4. the label generated earlier to Embed.footer.text
            5. the avatar of the quoting user to Embed.footer.icon_url
            6. the timestamp of the quoted message to Embed.timestamp.
        Return the object.

        Parameters
        ----------
        quoting_user : discord.User
            The user originally quoting the other message.
        quote : discord.Message
            The quoted message.
        alt : str
            [Optional] An alternate message text for the embed box.

        Returns
        -------
        discord.Embed
        """

        quote_embed = discord.Embed(description=alt or quote.content)
        quote_embed.set_author(
            name=quote.author.display_name,
            icon_url=quote.author.avatar_url
        )

        footertext = "Quoted by %s." % (quoting_user.display_name)

        if quote.edited_timestamp: # Message was edited
            post_edit_delta = quote.edited_timestamp - quote.timestamp
            footertext += " Edited %s later." % (
                await self.timedelta_timestamp_string(post_edit_delta)
            )

        quote_embed.set_footer(
            text=footertext,
            icon_url=quoting_user.avatar_url
        )

        quote_embed.timestamp = quote.timestamp

        return quote_embed

    async def quote_message(self, quote, partial=False):
        """
        Try to find the quoted message and post an according embed message.

        Try to find the quoted message by passing quote to
        self.search_message_by_quote(). If a fitting message was found and the
        bot is allowed to send messages in the channel, construct an according
        discord.Embed object and post it to the channel the quote originates
        from, then delete the original quoting message if allowed. If no fitting
        message was found, don't do anything.

        Parameters
        ----------
        quote : discord.Message
            Message that could contain a quote from another message.
        partial : boolean
            [Optional] Whether a partial quote is requested. In this case, only
            show the part given by the user in the embed box.
        """
        quoted_message = await self.search_message_by_quote(quote, partial)

        # Find own member object on the server.
        bot_member = quote.server.get_member(self.user.id)

        # Check if the bot is allowed to send messages in that channel.
        bot_may_send = quote.channel.permissions_for(bot_member).send_messages

        if quoted_message and bot_may_send:
            if partial:
                quote_request_match = self.re_partial_quote.fullmatch(
                    quote.content
                )

                matched_quote = re.search(
                    quote_request_match.group("content"),
                    quoted_message.content,
                    flags=re.IGNORECASE
                )

                quote_embed = await self.create_quote_embed(
                    quote.author,
                    quoted_message,
                    matched_quote.group(0)
                )
            else:
                quote_embed = await self.create_quote_embed(
                    quote.author,
                    quoted_message
                )

            await self.send_message(quote.channel, embed=quote_embed)

            try:
                await self.delete_message(quote)
            except discord.Forbidden:
                pass

    async def send_help_message(self, channel):
        """Send the help message of the bot to the given channel."""
        await self.send_message(
            channel,
            content="Quoting other users’ messages is easy. Just type a "
            "greater-sign (>), followed by an excerpt from the message you "
            "want to quote:\n```> sample message```\nI will attempt to "
            "find the right message based on that excerpt and display it.\n"
            "If I found the wrong message, consider increasing the length of "
            "your excerpt. You can also preceed the greater-sign with a user’s "
            "name to limit my search to messages from that user:\n"
            "```sample_user > sample message```\nIf you want me to not display "
            "the full message but only the part you gave me, type two "
            "greater-signs instead of one:\n```>> sample```\nFor more "
            "information on me, type “<@%s> info”. Also, if you still have "
             "questions, feel free to join my support Discord: "
             "https://discord.gg/rMXH2Rg" % (self.user.id)
        )

    async def send_info_message(self, channel):
        """Send information about the bot to the given channel."""
        await self.send_message(
            channel,
            content="Hi, my name is ParrotBot and I’m here to assist you with "
            "quoting other users’ messages – a functionality Discord still "
            "lacks by default. If you’d like to know how to do that, just type "
            "“<@%s> help”. Also, feel free to take a look at my source code on "
            "https://github.com/mart-w/parrotbot/ if you’re interested in the "
            "nitty gritty details.\n\nPlease note that I am free software: you "
            "can redistribute my source code and/or modify it under the terms "
            "of the GNU General Public License as published by the Free "
            "Software Foundation, either version 3 of the License, or "
            "(at your option) any later version.\n\nI am distributed in the "
            "hope that I will be useful, but **without any warranty**; without "
            "even the implied warranty of merchantability or fitness for a "
            "particular purpose. See the GNU General Public License for more "
            "details: http://www.gnu.org/licenses/" % (self.user.id)
        )

    async def handle_command(self, message):
        """
        Respond to a command given by a user.

        Use the regular expression for commands to check whether a command has
        actually been given by the user. If so and if it is a valid command,
        execute it. If not command is given or the command is not valid, assume
        that the info command is meant.

        Parameters
        ----------
        message : discord.Message
            The message containing the command.
        """
        command_match = self.re_command.fullmatch(message.content)

        command = command_match.group("command")

        if command in ("help", "?", "commands"):
            await self.send_help_message(message.channel)
        else:
            await self.send_info_message(message.channel)

    # Event listeners.

    async def on_ready(self):
        """
        Print ready message, post server count and set the bot's presence.

        Compile the needed regular expresssion objects. Then
        print a message saying that the server is ready and how many servers it
        is connected to. If the according value in the config file is set to
        True, also list all connected servers. Post the amount of connected
        servers to bot list sites, if according tokens are fiven in the config
        file. Finally set the bot's presence (game status) if one is specified
        in the config file.
        """
        # Regular expression objects used to recognise quotes.
        self.re_quote = re.compile(
            r"\s*(?P<author>(?:<.*?>)|(?:.*?))\s*>\s*(?P<content>.+)"
        )
        self.re_partial_quote = re.compile(
            r"\s*(?P<author>(?:<.*?>)|(?:.*?))\s*>>\s*(?P<content>.+)"
        )

        # Regular expression object for user mention strings.
        self.re_user_mention = re.compile(r"<@!?(?P<ID>.*?)>")

        # Must be initialised here because it depends on self.user.id.
        self.re_command = re.compile(
            r"\s*<@!?" + self.user.id + r">\s*(?P<command>.*?)\s*"
        )

        print("ParrotBot is ready.")
        print("\nConnected Servers: %d" % (len(self.servers)))

        if self.config["server_list"]:
            for server in self.servers:
                print("%s - %s" % (server.id, server.name))

        print()

        await self.post_server_count()

        if "presence" in self.config:
            presence = discord.Game()
            presence.name = self.config["presence"]
            await self.change_presence(game=presence)

        self.initialised = True

    async def on_server_join(self, server):
        """Print number of connected servers when connecting to a new server."""
        print("Joined Server %s -- %s." % (server.id, server.name))
        print("Connected Servers: %d\n" % (len(self.servers)))
        await self.post_server_count()

    async def on_server_remove(self, server):
        """Print number of connected servers when leaving a server."""
        print("Left Server %s -- %s." % (server.id, server.name))
        print("Connected Servers: %d\n" % (len(self.servers)))
        await self.post_server_count()

    async def on_message(self, message):
        """
        Check if the bot should respond to the message and act accordingly.

        If the bot is initialised and the message matches the regular expression
        for commands, execute the command. If not, check whether the message
        matches the regular expression for quotes or partial quote and quote the
        message if that is the case. Messages from bots are ignored.

        Parameters
        ----------
        message : discord.message
            The message the bot received.
        """
        if self.initialised \
        and not message.author.bot \
        and message.channel.permissions_for(message.server.me).send_messages:
            if self.re_command.fullmatch(message.content):
                await self.handle_command(message)
            elif self.re_partial_quote.fullmatch(message.content):
                await self.quote_message(message, True)
            elif self.re_quote.fullmatch(message.content):
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

# Configuration object.
config = {}

# Will be set to True if config.json misses keys or does not exist yet.
configfile_needs_update = False

# Try to read configuration file.
try:
    with open("config.json", "r") as configfile:
        config = json.load(configfile)
except FileNotFoundError:
    print("Configuration file not found!")
    configfile_needs_update = True

# Check for token.txt for backwards compatibility. If found, get the token file
# from it and use it for the new configuration, if that does not contain a token
# yet.
try:
    with open("token.txt", "r") as tokenfile:
        token_from_txt = tokenfile.readline().rstrip()
        print(
            "token.txt found. Usage of this file is deprecated; the token will "
            "be written to the new config.json file."
        )
        if "discord-token" not in config:
            config["discord-token"] = token_from_txt
            configfile_needs_update = True
except FileNotFoundError:
    pass

# Check if the loaded configuration misses keys. If so, ask for user input or
# assume a default value.

# Discord API token.
if "discord-token" not in config:
    configfile_needs_update = True
    config["discord-token"] = input(
        "Discord API token not found. Please enter your API token: "
    )

# discordbots.org API token
if "discordbots_org_token" not in config:
    configfile_needs_update = True
    config["discordbots_org_token"] = input(
        "discordbots.org API token not found. Please enter your API token "
        "(leave empty to ignore discordbots.org): "
    )

# bots.discord.pw API token
if "bots_discord_pw_token" not in config:
    configfile_needs_update = True
    config["bots_discord_pw_token"] = input(
        "bots.discord.pw API token not found. Please enter your API token "
        "(leave empty to ignore bots.discord.pw): "
    )

# presence (game status)
if "presence" not in config:
    configfile_needs_update = True
    config["presence"] = input(
        "Please specify a presence or game status. This will be shown in the "
        "bot's user profile (leave empty to disable this feature): "
    )

# whether the server list should be displayed on startup
if "server_list" not in config:
    configfile_needs_update = True

    answer = None

    while answer == None or answer.lower() not in ("y", "yes", "n", "no", ""):
        answer = input(
            "Should the bot list all connected servers on startup? [Y/n]: "
        )

        if answer.lower() not in ("y", "yes", "n", "no", ""):
            print("\nPlease answer with either yes or no.\n")

    if answer.lower() in ("y", "yes", ""):
        config["server_list"] = True
    else:
        config["server_list"] = False

# (Re)write configuration file if it didn't exist or missed keys.
if configfile_needs_update:
    with open("config.json", "w") as configfile:
        json.dump(config, configfile, indent=2)
        print("Configuration file updated.")


while True:
    try:
        # Initialise client object with the loaded configuration.
        client = ParrotBot(config)
        # Start bot session.
        print("Start bot session with token %s" % (config["discord-token"]))
        client.run(config["discord-token"])
    except Exception as exception:
        print(type(exception))
        print(exception)
        print("\n--------------------------------------------")
        print("An error occured. Retrying in 5 seconds ...")
        print("--------------------------------------------\n")

        time.sleep(5)
