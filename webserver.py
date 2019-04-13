import datetime

import tornado.ioloop
import tornado.web

from tornado.options import define, options, parse_command_line

from isthehubup import IsUp, LogIt


define("port", default=5000, help="Listen this port", type=int)
define("debug", default=False, help="Enable debugging and hot reloading", type=bool)


class MainHandler(tornado.web.RequestHandler):
    async def get(self):
        target = "https://mybinder.org/"
        self.write('<head><script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.24.0/moment-with-locales.min.js" integrity="sha256-AdQN98MVZs44Eq2yTwtoKufhnU+uZ7v2kXnD5vqzZVo=" crossorigin="anonymous"></script></head>')
        self.write("<h1>Is the hub up?</h1>")

        logit = LogIt()
        hub = IsUp(target, [logit], every=None)
        await hub.check()
        now = datetime.datetime.utcnow()

        self.write("<p>")
        self.write("<h2>Checking %s ...</h2>" % target)
        self.write("""<i><span id='time'>at {date} UTC</span></i>""".format(date=now))

        if logit.url is None:
            self.write("<p>All is good 😀</p>")
        else:
            self.write("<p>Something happened 😟</p>")
            self.write("<p>")
            self.write(logit.message)
            self.write("</p>")

        self.write("<p>")
        self.write('Freshly made with <a href="https://github.com/betatim/isthehubup">open-source</a> 🌈')
        self.write("</p>")

        self.write("</p>")
        self.write("""
                <script>
                    var element;
                    element = document.getElementById("time");
                    if (element) {
                      element.innerHTML = moment('%sZ').format('LLL');
                    }
                </script>""" % now)


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
