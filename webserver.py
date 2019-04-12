import datetime

import tornado.ioloop
import tornado.web

from tornado.options import define, options, parse_command_line

from isthehubup import IsUp, LogIt


define("port", default=5000, help="Listen this port", type=int)
define("debug", default=False, help="Enable debugging and hot reloading", type=bool)


class MainHandler(tornado.web.RequestHandler):
    async def get(self):
        target = "https://mybinder.org"
        self.write("<h1>Hello, world!</h1>")

        logit = LogIt()
        hub = IsUp(target, [logit], every=None)
        await hub.check()

        self.write("<p>")
        self.write("<h2>Checked %s</h2>" % target)
        self.write("<i>at %s UTC</i>" % datetime.datetime.utcnow())

        if logit.url is None:
            self.write("<p>All is good 😀</p>")
        else:
            self.write("<p>")
            self.write(logit.message)
            self.write("</p>")

        self.write("</p>")


def make_app(debug=None):
    return tornado.web.Application(
        [(r"/", MainHandler)],
        debug=debug
    )


if __name__ == "__main__":
    parse_command_line()

    app = make_app(options.debug)
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
