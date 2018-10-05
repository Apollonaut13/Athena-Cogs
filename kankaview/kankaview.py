from discord.ext import commands
import discord
import aiohttp
import os
from .utils.dataIO import dataIO
from .utils import checks
import tomd

DEFAULT_SETTINGS = {'token': None, 'language': 'en'}
REQUEST_PATH = 'https://kanka.io/api/v1/'


class Campaign:
    def __init__(self, json_data):
        self.id = json_data['id']
        self.name = json_data['name']
        self.locale = json_data['locale']
        self.entry = tomd.convert(json_data['entry'])
        if json_data['image']:
            self.image = 'https://kanka.io/storage/' + json_data['image']
        self.visibility = json_data['visibility']
        self.created_at = json_data['created_at']
        self.updated_at = json_data['updated_at']
        self.members = json_data['members']


class Character:
    def __init__(self, campaign_id, json_data):
        self.campaign_id = campaign_id
        self.age = json_data['age']
        self.created = {'at': json_data['created_at'],
                        'by': json_data['created_by']}
        self.entity_id = json_data['entity_id']
        self.entry = tomd.convert(json_data['entry'])
        self.family_id = json_data['family_id']
        self.id = json_data['id']
        if json_data['image']:
            self.image = 'https://kanka.io/storage/' + json_data['image']
        self.is_dead = json_data['is_dead']
        self.is_private = json_data['is_private']
        self.location_id = json_data['location_id']
        self.name = json_data['name']
        self.race = json_data['race']
        self.section_id = json_data['section_id']
        self.sex = json_data['sex']
        self.title = json_data['title']
        self.type = json_data['type']
        self.updated = {'at': json_data['updated_at'],
                        'by': json_data['updated_by']}


class KankaView:
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/kankaview/settings.json')
        self.headers = self._set_headers()
        self.session = aiohttp.ClientSession(headers=self.headers)

    def _save_settings(self):
        dataIO.save_json('data/kankaview/settings.json', self.settings)

    def _set_headers(self):
        if self.settings['token']:
            headers = {}
            headers['accept'] = 'application/json'
            headers['authorization'] = self.settings['token']
            return headers
        else:
            return None

    async def _get_campaigns_list(self):
        async with self.session.get(REQUEST_PATH + 'campaigns') as r:
            j = await r.json()
            campaigns = []
            for campaign in j['data']:
                campaigns.append(Campaign(campaign))
            return campaigns

    async def _get_campaign(self, id):
        # TODO: Make this do a thing, unless just using _get_campaigns_list
        # will always work
        async with self.session.get('{base_url}campaigns/{id}'.format(
                                    base_url=REQUEST_PATH,
                                    id=id)
                                    ) as r:
            j = await r.json()
            return Campaign(j['data'])

    async def _get_character(self, campaign_id, character_id):
        # TODO: Search by name
        async with self.session.get('{base_url}campaigns/'
                                    '{campaign_id}'
                                    '/characters/'
                                    '{character_id}'.format(
                                        base_url=REQUEST_PATH,
                                        campaign_id=campaign_id,
                                        character_id=character_id)
                                    ) as r:
            j = await r.json()
            return Character(campaign_id, j['data'])

    @commands.group(name='kanka', pass_context=True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def kanka(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @kanka.command(name='campaigns', pass_context=True)
    async def list_campaigns(self, ctx):
        """Lists campaigns"""
        campaigns = await self._get_campaigns_list()
        em = discord.Embed(title='Campaigns List',
                           description='{} campaigns found'.format(
                               len(campaigns)),
                           colour=discord.Color.blue())
        # This only works with up to 25 campaigns
        for campaign in campaigns:
            em.add_field(name=campaign.name,
                         value='https://kanka.io/{lang}/campaign/{id}'.format(
                             lang=self.settings['language'],
                             id=campaign.id
                         ))
        await self.bot.say(embed=em)

    @kanka.command(name='campaign')
    async def display_campaign(self,  id: int):
        # TODO: Add alias and name support
        campaign = await self._get_campaign(id)
        em = discord.Embed(title=campaign.name,
                           description=campaign.entry,
                           url='https://kanka.io/{lang}/campaign/{id}'.format(
                               lang=self.settings['language'],
                               id=campaign.id),
                           colour=discord.Color.blue())
        em.set_thumbnail(url=campaign.image)  # TODO: Test with no image
        em.add_field(name='Owner:', value=campaign.members[0]['user']['name'])
        em.add_field(name='Visibility', value=campaign.visibility.title())
        em.add_field(name='Locale', value=campaign.locale)
        em.add_field(name='Created At',
                     value=campaign.created_at['date'][:-10])
        em.add_field(name='Updated At',
                     value=campaign.updated_at['date'][:-10])
        await self.bot.say(embed=em)

    @kanka.command(name='character')
    async def display_character(self, cmpgn_id: int, character_id: int):
        # TODO: Add search by name support
        # TODO: Attributes and relations
        char = await self._get_character(cmpgn_id, character_id)
        if not char.is_private:
            em = discord.Embed(title=char.name,
                               description=char.entry,
                               url='https://kanka.io/{lang}/campaign/'
                               '{cmpgn_id}'
                               '/characters/'
                               '{character_id}'
                               .format(
                                   lang=self.settings['language'],
                                   cmpgn_id=cmpgn_id,
                                   character_id=character_id),
                               colour=discord.Color.blue())
            em.set_thumbnail(url=char.image)  # TODO: Test with no image
            em.add_field(name='Title', value=char.title)
            em.add_field(name='Age', value=char.age)
            em.add_field(name='Type', value=char.type)
            em.add_field(name='Race', value=char.race)
            em.add_field(name='Is Dead', value=char.is_dead)
            em.add_field(name='Sex', value=char.sex)
            # TODO: Add family
            await self.bot.say(embed=em)
        else:
            await self.bot.say('Entity not found')

    # @kanka.command(name='search', pass_context=True)

    @commands.group(name='kankaset', pass_context=True)
    async def kankaset(self, ctx):
        """Configuration commands for KankaView"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @kankaset.command(name='token')
    async def set_token(self, token: str):
        """Set API token ('Personal Access Token'). Do not included 'Bearer '.
        Be aware that this token is stored in plaintext by the bot."""
        if token[:7] != 'Bearer ':
            token = 'Bearer ' + token
        self.settings['token'] = token
        self._save_settings()
        self._set_headers()
        await self.bot.say('API token set.')

    @kankaset.command(name='reset')
    async def restore_default_settings(self):
        """Return to default settings and forget API key."""
        self.settings = DEFAULT_SETTINGS
        self._save_settings()
        await self.bot.say('API token cleared and settings reset to default.')

    @kankaset.command(name='test')
    async def test_token(self):
        async with self.session.get(REQUEST_PATH + 'campaigns') as r:
            await self.bot.say(r.status)

    # TODO: Add way of changing language


def check_folder():
    if not os.path.exists('data/kankaview'):
        print('Creating data/kankaview folder...')
        os.makedirs('data/kankaview')


def check_file():
    file = 'data/kankaview/settings.json'
    if not dataIO.is_valid_json(file):
        print('Creating default settings.json...')
        dataIO.save_json(file, DEFAULT_SETTINGS)


def setup(bot):
    check_folder()
    check_file()
    kankaview = KankaView(bot)
    bot.add_cog(kankaview)