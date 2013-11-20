from logging import getLogger
import time

import feedparser
from zope.interface import implements, Interface
from zope import schema

from DateTime import DateTime
from DateTime.interfaces import DateTimeError

from plone.tiles import PersistentTile

from eneawebtv.plonetheme import _

# Accept these bozo_exceptions encountered by feedparser when parsing
# the feed:
ACCEPTED_FEEDPARSER_EXCEPTIONS = (feedparser.CharacterEncodingOverride, )

# store the feeds here (which means in RAM)
FEED_DATA = {}  # url: ({date, title, url, itemlist})

logger = getLogger(__name__)


class IFeed(Interface):

    def __init__(url, timeout):
        """initialize the feed with the given url. will not automatically load it
           timeout defines the time between updates in minutes
        """

    def loaded():
        """return if this feed is in a loaded state"""

    def title():
        """return the title of the feed"""

    def items():
        """return the items of the feed"""

    def feed_link():
        """return the url of this feed in feed:// format"""

    def site_url():
        """return the URL of the site"""

    def last_update_time_in_minutes():
        """return the time this feed was last updated in minutes since epoch"""

    def last_update_time():
        """return the time the feed was last updated as DateTime object"""

    def needs_update():
        """return if this feed needs to be updated"""

    def update():
        """update this feed. will automatically check failure state etc.
           returns True or False whether it succeeded or not
        """

    def update_failed():
        """return if the last update failed or not"""

    def ok():
        """is this feed ok to display?"""


class RSSFeed(object):
    """an RSS feed"""
    implements(IFeed)

    # TODO: discuss whether we want an increasing update time here, probably not though
    FAILURE_DELAY = 10  # time in minutes after which we retry to load it after a failure

    def __init__(self, url, timeout):
        self.url = url
        self.timeout = timeout or 100

        self._items = []
        self._title = ""
        self._siteurl = ""
        self._loaded = False  # is the feed loaded
        self._failed = False  # does it fail at the last update?
        self._last_update_time_in_minutes = 0  # when was the feed last updated?
        self._last_update_time = None  # time as DateTime or Nonw

    @property
    def last_update_time_in_minutes(self):
        """return the time the last update was done in minutes"""
        return self._last_update_time_in_minutes

    @property
    def last_update_time(self):
        """return the time the last update was done in minutes"""
        return self._last_update_time

    @property
    def update_failed(self):
        return self._failed

    @property
    def ok(self):
        return (not self._failed and self._loaded)

    @property
    def loaded(self):
        """return whether this feed is loaded or not"""
        return self._loaded

    @property
    def needs_update(self):
        """check if this feed needs updating"""
        now = time.time() / 60
        return (self.last_update_time_in_minutes + self.timeout) < now

    def update(self):
        """update this feed"""
        now = time.time() / 60  # time in minutes

        try:
            # check for failure and retry
            if self.update_failed:
                if (self.last_update_time_in_minutes + self.FAILURE_DELAY) < now:
                    return self._retrieveFeed()
                else:
                    return False
            # check for regular update
            if self.needs_update:
                return self._retrieveFeed()
        except:
            self._failed = True
            logger.exception('failed to update RSS feed %s', self.url)

        return self.ok

    def _buildItemDict(self, item):
        link = item.links[0]['href']
        itemdict = {
            'title': item.title,
            'url': link,
            'summary': item.get('description', ''),
        }
        if hasattr(item, "updated"):
            try:
                itemdict['updated'] = DateTime(item.updated)
            except DateTimeError:
                # It's okay to drop it because in the
                # template, this is checked with
                # ``exists:``
                pass

        return itemdict

    def _retrieveFeed(self):
        """do the actual work and try to retrieve the feed"""
        url = self.url
        if url != '':
            self._last_update_time_in_minutes = time.time() / 60
            self._last_update_time = DateTime()
            d = feedparser.parse(url)
            if getattr(d, 'bozo', 0) == 1 \
                and not isinstance(d.get('bozo_exception'),
                                   ACCEPTED_FEEDPARSER_EXCEPTIONS):
                self._loaded = True  # we tried at least but have a failed load
                self._failed = True
                return False
            self._title = d.feed.title
            self._siteurl = d.feed.link
            self._items = []
            for item in d['items']:
                try:
                    itemdict = self._buildItemDict(item)
                except (AttributeError, KeyError):
                    continue
                self._items.append(itemdict)
            self._loaded = True
            self._failed = False
            return True
        self._loaded = True
        self._failed = True  # no url set means failed
        return False  # no url set, although that actually should not really happen

    @property
    def items(self):
        return self._items

    # convenience methods for displaying
    #

    @property
    def feed_link(self):
        """return rss url of feed for tile"""
        return self.url.replace("http://", "feed://")

    @property
    def title(self):
        """return title of feed for tile"""
        return self._title

    @property
    def siteurl(self):
        """return the link to the site the RSS feed points to"""
        return self._siteurl


class IRSSTileSchema(Interface):

    tile_title = schema.TextLine(
        title=_(u'Title'),
        description=_(u'Title of the tile.  If omitted, the title of the feed will be used.'),
        required=False,
        default=u'')

    count = schema.Int(title=_(u'Number of items to display'),
                       description=_(u'How many items to list.'),
                       required=True,
                       default=5)
    url = schema.TextLine(title=_(u'URL of RSS feed'),
                        description=_(u'Link of the RSS feed to display.'),
                        required=True,
                        default=u'')

    timeout = schema.Int(title=_(u'Feed reload timeout'),
                        description=_(u'Time in minutes after which the feed should be reloaded.'),
                        required=True,
                        default=100)


class RSSTile(PersistentTile):

    def __call__(self):
        self.update()
        result = super(RSSTile, self).__call__()
        return result

    @property
    def display_title(self):
        """return the title with RSS feed title or from URL"""
        return self.data['tile_title'] or self._getFeed().title

    @property
    def initializing(self):
        """should return True if deferred template should be displayed"""
        feed = self._getFeed()
        if not feed.loaded:
            return True
        if feed.needs_update:
            return True
        return False

    def deferred_update(self):
        """refresh data for serving via KSS"""
        feed = self._getFeed()
        feed.update()

    def update(self):
        """update data before rendering. We can not wait for KSS since users
        may not be using KSS."""
        self.deferred_update()

    def _getFeed(self):
        """return a feed object but do not update it"""
        feed = FEED_DATA.get(self.data['url'], None)
        if feed is None:
            # create it
            feed = FEED_DATA[self.data['url']] = RSSFeed(self.data['url'],
                                                         self.data['timeout'])
        return feed

    @property
    def feed_url(self):
        """return url of feed for tile"""
        return self._getFeed().url

    @property
    def siteurl(self):
        """return url of site for tile"""
        return self._getFeed().siteurl

    @property
    def feedlink(self):
        """return rss url of feed for tile"""
        return self.feed_url.replace("http://", "feed://")

    @property
    def feedAvailable(self):
        """checks if the feed data is available"""
        return self._getFeed().ok

    @property
    def items(self):
        return self._getFeed().items[:self.data['count']]

    @property
    def enabled(self):
        return self._getFeed().ok
