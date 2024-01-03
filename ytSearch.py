import requests
import sys
import json
import re

from textwrap import wrap, shorten
from prompt_toolkit import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText


class ValidateConfig:
    pass


def getVarInConfig(var):
    with open('config.json', 'r') as file:
        config =  json.load(file)

    keys = var.split('.')
    currentKey = config

    for idx, key in enumerate(keys):
        try:
            currentKey = currentKey[key]
        except KeyError:
            print('Missing \"{}\" in config.json'.format('.'.join(keys[:idx+1])))
            sys.exit(1)

    return currentKey


INVIDIOUS_INSTANCES = ['yewtu.be', 'vid.puffyan.us', 'yt.artemislena.eu', 'invidious.projectsegfau.lt', 'invidious.slipfox.xyz', 'invidious.privacydev.net', 'vid.priv.au', 'iv.melmac.space', 'iv.ggtyler.dev', 'invidious.lunar.icu', 'inv.zzls.xyz', 'inv.tux.pizza', 'invidious.protokolla.fi', 'iv.nboeck.de', 'invidious.private.coffee', 'yt.drgnz.club', 'iv.datura.network', 'invidious.fdn.fr', 'invidious.perennialte.ch', 'yt.cdaut.de', 'invidious.drgns.space', 'inv.us.projectsegfau.lt', 'invidious.einfachzocken.eu', 'invidious.nerdvpn.de', 'inv.n8pjl.ca', 'youtube.owacon.moe']

TEXT_COLOR = getVarInConfig('ui.textColor')
MARGIN = getVarInConfig('ui.margin') * ' '
WIDTH = getVarInConfig('ui.width')
SEARCH_RESULTS_LIMIT = getVarInConfig('ui.searchResultsLimit')
CHANNEL_VIDEOS_LIMIT = getVarInConfig('ui.channelVideosLimit')
SELECTED_INSTANCE = INVIDIOUS_INSTANCES[getVarInConfig('invidiousInstance')-1]

BLOCKED_VIDEO_TITLES = getVarInConfig('blockedVideoTitles')
BLOCKED_CHANNEL_NAMES = getVarInConfig('blockedChannelNames')
BLOCKED_CHANNEL_IDS = getVarInConfig('blockedChannelIds')


def printRule():
    printLn([('gray3', ''.ljust(WIDTH + len(MARGIN), '—'))], margin=False)


def printError(error):
    printLn([('gray1', error)])


def printUsage():
    print()
    printLn([('gray1', 'Usage       search [term]')])
    printLn([('gray1', '            channel [id]')])
    printRule()
    printLn([('gray1', 'Instances')])
    print()
    for idx, instance in enumerate(INVIDIOUS_INSTANCES):
        printLn([('gray1', '  {} {}'.format(str(idx+1).rjust(2).ljust(4), instance))])
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

        if channelNameWidth > 0:
            channelName = shorten(self.channelName, width=channelNameWidth, placeholder='…')
        else:
            channelName = '…'

        return '{}    {}'.format('{}{}'.format(channelName, self.channelVerifiedText).ljust(channelNameWidth), meta)

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

    def queryApi(self, query, onFail=None):
        try:
            jsonData = requests.get('https://{}/api/v1/{}'.format(SELECTED_INSTANCE, query)).json()
        except:
            printLn([('gray1', 'Unable to establish a connection to \"{}\"'.format(SELECTED_INSTANCE))])
            sys.exit(1)
            
        if type(jsonData) == dict and jsonData.get('error'):
            if onFail:
                printError(onFail)
            else:
                printError('No results')
            sys.exit(1)

        return jsonData

    def renderResults(self, jsonData):
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
            printError('No results')
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
        jsonChannelData = self.queryApi('channels/{}'.format(channelId), onFail='Invalid channel ID \"{}\"'.format(channelId))
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
        
        self.renderResults(videos)
    

def main():
    args = sys.argv[1:]

    if len(args) < 2:
        printUsage()
        sys.exit(1)

    command, *params = args

    app = App()

    if command == 'search':
        app.search(params)
        sys.exit(0)
    elif command == 'channel':
        app.listChannelVideos(params[0])
        sys.exit(0)

    printUsage()
    sys.exit(1)


if __name__ == '__main__':
    main()