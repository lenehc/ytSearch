import requests
import sys
import re

from itertools import zip_longest
from json import load, JSONDecodeError
from jsonschema import validate
from textwrap import wrap
from prompt_toolkit import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText


INVIDIOUS_INSTANCES = ['yewtu.be', 'vid.puffyan.us', 'yt.artemislena.eu', 'invidious.projectsegfau.lt', 'invidious.slipfox.xyz', 'invidious.privacydev.net', 'vid.priv.au', 'iv.melmac.space', 'iv.ggtyler.dev', 'invidious.lunar.icu', 'inv.zzls.xyz', 'inv.tux.pizza', 'invidious.protokolla.fi', 'iv.nboeck.de', 'invidious.private.coffee', 'yt.drgnz.club', 'iv.datura.network', 'invidious.fdn.fr', 'invidious.perennialte.ch', 'yt.cdaut.de', 'invidious.drgns.space', 'inv.us.projectsegfau.lt', 'invidious.einfachzocken.eu', 'invidious.nerdvpn.de', 'inv.n8pjl.ca', 'youtube.owacon.moe']
COMMANDS_USAGE = {
    'search': 'Search for channels and videos sorted by relevance. Arguments: \"search [searchTerm]\", searchTerm is required. Example \"search toosie slide\"', 
    'channel': 'List all videos from a channel sorted by date published. Arguments: \"channel [channelId]\", channelId is required. Example \"channel UCByOQJjav0CUDwxCk-jVNRQ\"'
}
CONFIG_VAR_HELP = {
    'invidiousInstance': 'The number corresponding to the invidious instance that you want to use, see the table above for a list of available instances. Example: 2',
    'blockedVideoTitles': 'A dictionary of regex patterns, any video whose title matches a pattern will not be shown. To mark the filter as case-insensitive add a value of \"true\", else \"false\". Example: { \"toosie slide\": false }',
    'blockedChannelNames': 'A dictionary of regex patterns, any channel whose names matches a pattern will not be shown. To mark the filter as case-insensitive add a value of \"true\", else \"false\". Example: { \"drake\": true }',
    'blockedChannelIds': 'A list of strings, any channel whose ID matches a string will not be shown. Example: [ \"UCByOQJjav0CUDwxCk-jVNRQ\" ]',
    'ui.margin': 'The number of spaces to prefix each line of text with. Example: 3',
    'ui.width': 'The maxiumum number of columns that a line should be before being wrapped. Example: 50',
    'ui.searchResultsLimit': 'The maximum number of search results (videos and channels) to show. Example: 10',
    'ui.channelVideosLimit': 'The maximum number of a channel\'s videos to show (when using command \"channel\"). Example: 500',
    'ui.textColor.gray1, ui.textColor.gray2, ui.textColor.gray3': 'Hex color codes in string format used to color the interface. Example: \"#8e8e93\"'
}


class Config:
    def __init__(self):
        self._errorPrefix = 'Unable to parse config.json: '
        self.jsonSchema = {
            'type': 'object',
            'properties': {
                'invidiousInstance': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': len(INVIDIOUS_INSTANCES)
                },
                'blockedVideoTitles': {
                    'type': 'object',
                    'patternProperties': {
                        '^.*$': {
                            'type': 'boolean'
                        }
                    },
                    'additionalProperties': False
                },
                'blockedChannelNames': {
                    'type': 'object',
                    'patternProperties': {
                        '^.*$': {
                            'type': 'boolean'
                        }
                    },
                    'additionalProperties': False
                },
                'blockedChannelIds': {
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    }
                },
                'ui': {
                    'type': 'object',
                    'properties': {
                        'margin': {
                            'type': 'integer',
                            'minimum': 0
                        },
                        'width': {
                            'type': 'integer',
                            'minimum': 45
                        },
                        'searchResultsLimit': {
                            'type': 'integer',
                            'minimum': 1
                        },
                        'channelVideosLimit': {
                            'type': 'integer',
                            'minimum': 1
                        },
                        'textColor': {
                            'type': 'object',
                            'properties': {
                                'gray1': {
                                    'type': 'string',
                                    'pattern': '^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
                                },
                                'gray2': {
                                    'type': 'string',
                                    'pattern': '^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
                                },
                                'gray3': {
                                    'type': 'string',
                                    'pattern': '^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
                                }
                            },
                            'required': ['gray1', 'gray2', 'gray3']
                        }
                    },
                    'required': ['margin', 'width', 'searchResultsLimit', 'channelVideosLimit', 'textColor']
                }
            },
            'required': ['invidiousInstance', 'blockedVideoTitles', 'blockedChannelNames', 'blockedChannelIds', 'ui']
        }

        with open('config.json', 'r') as file:
            try:
                self.jsonConfig = load(file)
            except JSONDecodeError as error:
                print('{}{} (Line: {}, Column: {})'.format(self._errorPrefix, error.msg, error.lineno, error.colno))
                sys.exit(1)

    def _validateRegEx(self, keyNames):
        for keyName in keyNames:
            for filter in self.jsonConfig[keyName]:
                try:
                    re.compile(filter)
                except re.error:
                    print('{}\'{}\': \'{}\' is not a valid regular expression'.format(self._errorPrefix, keyName, filter))
                    return False
        return True

    def validate(self):
        try:
            validate(instance=self.jsonConfig, schema=self.jsonSchema)
        except Exception as error:
            if error.absolute_path:
                absPath = str(error.absolute_path[0])
                for node in list(error.absolute_path)[1:]:
                    absPath += '.{}'.format(node) if type(node) == str else '[{}]'.format(node)
            else:
                absPath = ''


            errorMessage = '\'{}\': {}'.format(absPath, error.message) if absPath else error.message
            print('{}{}'.format(self._errorPrefix, errorMessage))
            return False

        return self._validateRegEx(['blockedVideoTitles', 'blockedChannelNames'])


CONFIG = Config()
CONFIG.validate()
CONFIG = CONFIG.jsonConfig

SELECTED_INSTANCE = INVIDIOUS_INSTANCES[CONFIG['invidiousInstance']-1]

BLOCKED_VIDEO_TITLES = CONFIG['blockedVideoTitles']
BLOCKED_CHANNEL_NAMES = CONFIG['blockedChannelNames']
BLOCKED_CHANNEL_IDS = CONFIG['blockedChannelIds']

MARGIN = CONFIG['ui']['margin'] * ' '
WIDTH = CONFIG['ui']['width']
TEXT_COLOR = CONFIG['ui']['textColor']
SEARCH_RESULTS_LIMIT = CONFIG['ui']['searchResultsLimit']
CHANNEL_VIDEOS_LIMIT = CONFIG['ui']['channelVideosLimit']


def printRule():
    printLn([('gray3', ''.ljust(WIDTH + len(MARGIN), '—'))], margin=False)


def printError(error):
    printLn([('gray1', error)])


def printTable(table, fieldWidth=15, fieldValueWidth=40, newLineBetweenRows=False):
    formatRow = lambda key, value: '{}{}    {}'.format(MARGIN, str(key).rjust(fieldWidth), value)

    for idx, (key, value) in enumerate(table.items()):
        for fieldRow, valueRow in zip_longest(wrap(str(key), width=fieldWidth), wrap(str(value), width=fieldValueWidth), fillvalue=''):
            printLn([('gray1', formatRow(fieldRow, valueRow))])
        if newLineBetweenRows and idx != len(table)-1:
            print()


def printUsage(command=None, standAlone=False):
    if standAlone:
        print()

    printLn([('gray1', 'Usage')])
    print()

    if command:
        printTable({command: COMMANDS_USAGE[command]}, fieldWidth=8)
    else:
        printTable(COMMANDS_USAGE, fieldWidth=8, newLineBetweenRows=True)

    if standAlone:
        printRule()


def printHelp():
    print()
    printUsage()
    printRule()
    printLn([('gray1', 'Instances')])
    print()

    for idx, instance in enumerate(INVIDIOUS_INSTANCES):
        printLn([('gray1', '  {}   {}'.format(str(idx+1).rjust(2), instance))])

    printRule()
    printLn([('gray1', 'Config')])
    print()
    printTable(CONFIG_VAR_HELP, fieldWidth=24, newLineBetweenRows=True)
    printRule()


def formatCount(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


def formatVideoLength(delta):
    minutes, seconds = divmod(delta, 60)
    hours, minutes = divmod(minutes, 60)

    if delta > 3600:
        return '{}:{}:{}'.format(hours, str(minutes).zfill(2), str(seconds).zfill(2))
    return '{}:{}'.format(minutes, str(seconds).zfill(2))


def printLn(items, margin=True, **kwargs):
    marginStr = MARGIN if margin else ''
    print_formatted_text(
            FormattedText([('', marginStr)] + [('class:{}'.format(className), line) for className, line in items]),
            style=Style.from_dict(TEXT_COLOR),
            **kwargs,
        )


def get(destDict, key, defaultValue=''):
    value = destDict.get(key, defaultValue)
    if value == None:
        return defaultValue
    return value


def shortenString(string, width, suffix=''):
    width = width - len(suffix)
    string = string.strip()
    if width <= 0:
        return '…{}'.format(suffix)
    if len(string) > width:
        return '{}…{}'.format(string[:width-1].rstrip(), suffix)
    return '{}{}'.format(string, suffix)


class Channel:
    def __init__(self, jsonData):
        self.channelName = get(jsonData, 'author')
        self.channelId = get(jsonData, 'authorId')
        self.channelHandle = get(jsonData, 'channelHandle')
        self.subCount = get(jsonData, 'subCount', 0)
        self.subCountText = formatCount(self.subCount)
        self.subCountText += ' subscriber' if self.subCount == '1' else ' subscribers'
        self.channelVerified = get(jsonData, 'authorVerified', False)
        self.channelVerifiedText = ' ✓' if self.channelVerified else ''

    def render(self):
        blocks = wrap(self.channelName + self.channelVerifiedText, width=WIDTH)

        for block in blocks:
            printLn([('', block)])

        printLn([('gray1', self.subCountText)])
        printLn([('gray3', '[{}][{}]'.format(self.channelHandle, self.channelId).rjust(WIDTH))])
        printRule()


class Video:
    def __init__(self, jsonData):
        self.videoId = get(jsonData, 'videoId')
        self.videoTitle = get(jsonData, 'title')
        self.channelId = get(jsonData, 'authorId')
        self.channelName = get(jsonData, 'author')
        self.channelVerified = get(jsonData, 'authorVerified', False)
        self.channelVerifiedText = ' ✓' if self.channelVerified else ''
        self.viewCountText = get(jsonData, 'viewCountText', '0 views')
        self.publishedText = get(jsonData, 'publishedText', '0 seconds ago')
        self.videoLength = get(jsonData, 'lengthSeconds', 0)
        self.videoLengthText = formatVideoLength(self.videoLength)

    def videoInfo(self):
        meta = '{} · {}'.format(self.viewCountText, self.publishedText)
        channelNameWidth = WIDTH-len(meta)-4
        channelName = shortenString(self.channelName, width=channelNameWidth, suffix=self.channelVerifiedText)

        return '{}    {}'.format(channelName.ljust(channelNameWidth), meta)

    def render(self):
        blocks = wrap(self.videoTitle, width=WIDTH, max_lines=2, placeholder='…')

        for block in blocks:
            printLn([('', block)])

        printLn([('gray1', self.videoInfo())])
        printLn([('gray2', '({})'.format(self.videoLengthText)), ('gray3', '[{}][{}]'.format(self.videoId, self.channelId).rjust(WIDTH-len(self.videoLengthText)-2))])
        printRule()


class App:
    def __init__(self):
        pass

    def _matchFilter(self, filters, string, regEx=True):
        if regEx:
            for filter, ignoreCase in filters.items():
                if ignoreCase:
                    if re.compile(filter, re.IGNORECASE).search(string):
                        return True
                elif re.search(filter, string):
                    return True
        else:
            for filter in filters:
                if string == filter:
                    return True
        return False

    def filterResults(self, results):
        filteredResults = []

        for i in results:
            if self._matchFilter(BLOCKED_CHANNEL_IDS, i.channelId, regEx=False) or self._matchFilter(BLOCKED_CHANNEL_NAMES, i.channelName):
                continue
            if type(i) == Video:
                if self._matchFilter(BLOCKED_VIDEO_TITLES, i.videoTitle):
                    continue

            filteredResults.append(i)

        return filteredResults

    def queryApi(self, query, noResultsText='No results'):
        try:
            jsonData = requests.get('https://{}/api/v1/{}'.format(SELECTED_INSTANCE, query)).json()
        except:
            printLn([('gray1', 'Unable to establish a connection to \"{}\"'.format(SELECTED_INSTANCE))])
            sys.exit(1)
            
        if type(jsonData) == dict and jsonData.get('error'):
            printError(noResultsText)
            sys.exit(1)

        return jsonData

    def renderResults(self, jsonData, noResultsText='No results'):
        results = []
        channelCount = 0
        videoCount = 0

        for i in jsonData:
            if i['type'] == 'channel':
                results.append(Channel(i))
            elif i['type'] == 'video':
                results.append(Video(i))

        results = self.filterResults(results)

        if not results:
            printError(noResultsText)
            sys.exit(1)

        for i in results:
            if type(i) == Channel:
                channelCount += 1
            elif type(i) == Video:
                videoCount += 1

        channelCountText = 'channel' if channelCount == 1 else 'channels'
        videoCountText = 'video' if videoCount == 1 else 'videos'
        channelCountText = '{} {}'.format(channelCount, channelCountText)
        videoCountText = '{} {}'.format(videoCount, videoCountText)
        text = ''

        if channelCount and videoCount:
            text = '{}, {}'.format(channelCountText, videoCountText)
        elif channelCount:
            text = channelCountText
        elif videoCount:
            text = videoCountText

        print()
        printLn([('gray1', text)])
        printRule()

        for i in results:
            i.render()

    def _addResultsToDict(self, results, destDict):
        for i in results:
            if i['type'] == 'video':
                destDict[i['videoId']] = i
            elif i['type'] == 'channel':
                destDict[i['authorId']] = i

    def search(self, term):
        initialJsonData = self.queryApi('search?q={}'.format(term))

        results = {}
        currentPage = 1

        self._addResultsToDict(initialJsonData[:SEARCH_RESULTS_LIMIT], results)

        while len(results) < SEARCH_RESULTS_LIMIT:
            jsonData = self.queryApi('search?q={}&page={}'.format(term, currentPage))
            self._addResultsToDict(jsonData[:SEARCH_RESULTS_LIMIT-len(results)], results)
            currentPage += 1

        self.renderResults(results.values())

    def listChannelVideos(self, channelId):
        jsonChannelData = self.queryApi('channels/{}'.format(channelId), noResultsText='Invalid channel ID \"{}\"'.format(channelId))
        channel = Channel(jsonChannelData)

        print()
        printRule()
        printLn([('', channel.channelName + channel.channelVerifiedText)])
        printLn([('gray2', channel.subCountText)])

        initialJsonData = self.queryApi('channels/{}/videos'.format(channelId))
        videos = initialJsonData['videos'][:CHANNEL_VIDEOS_LIMIT]
        continuation = initialJsonData.get('continuation')

        while continuation and len(videos) < CHANNEL_VIDEOS_LIMIT:
            jsonVideoData = self.queryApi('channels/{}/videos?continuation={}'.format(channelId, continuation))
            videos += jsonVideoData['videos'][:CHANNEL_VIDEOS_LIMIT-len(videos)]
            continuation = jsonVideoData.get('continuation')
        
        self.renderResults(videos, noResultsText='')
    
    def run(self, command, params):
        if command == 'search':
            if params:
                self.search(params)
                return True
            printUsage(command, standAlone=True)
            sys.exit(1)
        elif command == 'channel':
            if params:
                if len(params) > 1:
                    printError('Unrecognized argument \"{}\"'.format(params[1]))
                    sys.exit(1)
                self.listChannelVideos(params[0])
                return True
            printUsage(command, standAlone=True)
            sys.exit(1)

        return False
    

def main():
    args = sys.argv[1:]

    if args:
        command, *params = args
        if App().run(command, params):
            sys.exit(0)

    printHelp()
    sys.exit(1)


if __name__ == '__main__':
    main()