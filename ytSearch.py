import requests
import sys

from munch import Munch
from textwrap import wrap, shorten
from prompt_toolkit import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText


INV_INSTANCES = ["yewtu.be", "vid.puffyan.us", "yt.artemislena.eu", "invidious.projectsegfau.lt", "invidious.slipfox.xyz", "invidious.privacydev.net", "vid.priv.au", "iv.melmac.space", "iv.ggtyler.dev", "invidious.lunar.icu", "inv.zzls.xyz", "inv.tux.pizza", "invidious.protokolla.fi", "iv.nboeck.de", "invidious.private.coffee", "yt.drgnz.club", "iv.datura.network", "invidious.fdn.fr", "invidious.perennialte.ch", "yt.cdaut.de", "invidious.drgns.space", "inv.us.projectsegfau.lt", "invidious.einfachzocken.eu", "invidious.nerdvpn.de", "inv.n8pjl.ca", "youtube.owacon.moe"]
CLASSES = {
    'gray': '#8e8e93',
    'gray2' : '#636366',
    'gray3': '#48484a',
}
MARGIN = "  "
WIDTH = 60


def printRule():
    printLn([("gray3", "".ljust(WIDTH + len(MARGIN), "—"))], margin=False)


def printError(error):
    printLn([("gray", error)])


def printUsage():
    print()
    printLn([("gray", "Usage       [instance] search [term]")])
    printLn([("gray", "                 ―     channel [id]")])
    printRule()
    printLn([("gray", "Instances")])
    print()
    for idx, instance in enumerate(INV_INSTANCES):
        printLn([("gray", f'  {str(idx+1).rjust(2).ljust(4)} {instance}')])
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
        return f'{hours}:{str(minutes).zfill(2)}:{str(seconds).zfill(2)}'
    return f'{minutes}:{str(seconds).zfill(2)}'


def printLn(items, margin=True, **kwargs):
    marginStr = MARGIN if margin else ""
    print_formatted_text(
            FormattedText([("", marginStr)] + [(f'class:{className}', line) for className, line in items]),
            style=Style.from_dict(CLASSES),
            **kwargs,
        )


class Channel:
    def __init__(self, dataObj):
        self.channelName = dataObj.author
        self.channelId = dataObj.authorId
        self.channelHandle = dataObj.channelHandle
        self.subCount = formatCount(dataObj.subCount)
        self.subCount += " subscriber" if self.subCount == "1" else " subscribers"
        self.channelVerified = dataObj.authorVerified

    def render(self):
        channelVerified = " ✓" if self.channelVerified else ""
        blocks = wrap(self.channelName + channelVerified, width=WIDTH)

        for block in blocks:
            printLn([("", block)])

        printLn([("gray", self.subCount)])
        printLn([("gray3", f'[{self.channelHandle}][{self.channelId}]'.rjust(WIDTH))])
        printRule()


class Video:
    def __init__(self, dataObj):
        self.videoId = dataObj.videoId
        self.videoTitle = dataObj.title
        self.channelId = dataObj.authorId
        self.channelName = dataObj.author
        self.channelVerified = dataObj.authorVerified
        self.viewCount = dataObj.viewCountText
        self.published = dataObj.publishedText
        self.videoLength = formatVideoLength(dataObj.lengthSeconds)

    def videoInfo(self):
        meta = f"{self.viewCount} · {self.published}"
        channelNameWidth = WIDTH-len(meta)-4
        if channelNameWidth > 0:
            channelName = shorten(self.channelName, width=channelNameWidth, placeholder="…")
        else:
            channelName = "…"
        if self.channelVerified:
            channelName += " ✓"
        return f'{channelName.ljust(channelNameWidth)}    {meta}'

    def render(self):
        blocks = wrap(self.videoTitle, width=WIDTH, max_lines=2, placeholder="…")

        for block in blocks:
            printLn([("", block)])

        printLn([("gray", self.videoInfo())])
        printLn([("gray2", f'({self.videoLength})'), ("gray3", f'[{self.videoId}][{self.channelId}]'.rjust(WIDTH-len(self.videoLength)-2))])
        printRule()


class App:
    def __init__(self, instanceIdx):
        self.instance = INV_INSTANCES[instanceIdx]

    def filterResults(self, results):
        return results

    def queryApi(self, query):
        try:
            jsonData = requests.get(f"https://{self.instance}/api/v1/{query}").json()

            if type(jsonData) == dict and jsonData.get("error"):
                printError("No results")
                sys.exit(1)

            return jsonData
        except Exception as e:
            printLn([("gray", f"Unable to establish a connection to \"{self.instance}\"")])
            sys.exit()

    def renderResults(self, jsonData):
        results = []
        channelCount = 0
        videoCount = 0

        for i in map(lambda x: Munch(x), jsonData):
            if i.type == "channel":
                channelCount += 1
                results.append(Channel(i))
            elif i.type == "video":
                videoCount += 1
                results.append(Video(i))

        if not results:
            printLn("No results")
            sys.exit(1)
        
        self.filterResults(results)

        channelCountText = "channel" if channelCount == 1 else "channels"
        videoCountText = "video" if videoCount == 1 else "videos"
        channelCountText = f'{channelCount} {channelCountText}'
        videoCountText = f'{videoCount} {videoCountText}'
        text = ""

        if channelCount and videoCount:
            text = f'{channelCountText}, {videoCountText}'
        elif channelCount:
            text = channelCountText
        elif videoCount:
            text = videoCountText

        print()
        printLn([("gray", text)])
        printRule()

        for i in results:
            i.render()

    def search(self, term):
        jsonData = self.queryApi(f"search?q={term}")
        self.renderResults(jsonData)

    def listChannelVideos(self, channelId):
        jsonData = self.queryApi(f"channels/{channelId}/videos")
        self.renderResults(jsonData["videos"])
    

def main():
    args = sys.argv[1:]

    if len(args) < 3:
        printUsage()
        sys.exit(1)

    instanceIndex, command, *params = args

    if instanceIndex.isdigit():
        idx = int(instanceIndex)-1
        if idx < len(INV_INSTANCES):
            app = App(idx)

            if command == "search":
                app.search(params)
                sys.exit(0)
            elif command == "channel":
                app.listChannelVideos(params[0])
                sys.exit(0)

    printUsage()
    sys.exit(1)


if __name__ == "__main__":
    main()