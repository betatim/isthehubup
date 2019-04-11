import asyncio
import datetime
import json
import logging
import os
import sys
import urllib

from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient


MG_API_KEY = os.getenv("MG_API_KEY", None)
if MG_API_KEY is None:
    print("Set the MG_API_KEY environment variable.")
    sys.exit(1)

GITTER_API_KEY = os.getenv("GITTER_API_KEY", None)
if GITTER_API_KEY is None:
    print("Set the GITTER_API_KEY environment variable.")
    sys.exit(1)


def timedelta(delta):
    return datetime.timedelta(seconds=delta)


class IsUp:
    def __init__(self, url, reporters, every=60):
        self.reporters = reporters
        self.url = url
        self.every = every

        self.client = AsyncHTTPClient()

    async def check(self):
        logging.info(f"Is {self.url} up?")

        r = await self.client.fetch(
            self.url, raise_error=False, request_timeout=5
        )

        if r.code >= 400:
            logging.warning(f"{self.url} returned a {r.code}.")

            reports = [
                reporter.report(self.url, f"{self.url} returned a {r.code}.")
                for reporter in self.reporters
            ]

            await asyncio.gather(*reports)

        # wait till we are done to schedule the next call
        IOLoop.current().call_later(self.every, self.check)


class BinderBuilds:
    def __init__(self, repo_spec, reporters, every=600):
        self.every = every
        self.reporters = reporters
        self.url = "https://mybinder.org/build/" + repo_spec

        self.client = AsyncHTTPClient()
        self._reset()

    def _reset(self):
        self._body = b""
        self._phase = ""
        self._log_lines = ""

    def _buffer(self, chunk):
        self._body += chunk

        idx = self._body.find(b"\n\n")
        while idx > -1:
            message = self._body[:idx].decode("utf8", "replace")
            after_newlines = idx + 2
            self._body = self._body[after_newlines:]

            if message.startswith("data:"):
                data = json.loads(message.split(":", 1)[1])
                self._phase = data["phase"]
                self._log_lines += "%s %s" % (
                    data["phase"].upper(),
                    data["message"],
                )

            idx = self._body.find(b"\n\n")

    async def check(self):
        logging.info("Does %s launch?" % self.url)
        r = await self.client.fetch(
            self.url,
            raise_error=False,
            streaming_callback=self._buffer,
            request_timeout=3000,
        )

        if r.code >= 400 or self._phase != "ready":
            logging.warning(f"Launching {self.url} failed with a {r.code}.")

            reports = [
                reporter.report(self.url, self._log_lines)
                for reporter in self.reporters
            ]

            await asyncio.gather(*reports)

        else:
            logging.info(f"Launching {self.url} took {r.request_time}s.")

        self._reset()
        # wait till we are done to schedule the next call
        IOLoop.current().call_later(self.every, self.check)


class Gitter:
    def __init__(self, channel, at_most_every=600):
        self.at_most_every = timedelta(at_most_every)
        self._last_report = datetime.datetime.utcnow() - self.at_most_every

        self.channel = channel

        self.client = AsyncHTTPClient()

    async def get_channel_id(self):
        r = await self.client.fetch(
            "https://api.gitter.im/v1/rooms",
            headers=dict(Authorization=f"Bearer {GITTER_API_KEY}"),
        )
        rooms = json.loads(r.body.decode("utf8", "replace"))
        for room in rooms:
            if room["name"] == self.channel:
                channel_id = room["id"]
                break
        else:
            raise RuntimeError("Can't find room f{channel}.")

        return channel_id

    async def report(self, url, message):
        now = datetime.datetime.utcnow()
        if now - self._last_report >= self.at_most_every:
            self._last_report = now

            channel_id = await self.get_channel_id()

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {GITTER_API_KEY}",
            }
            self.client.fetch(
                f"https://api.gitter.im/v1/rooms/{channel_id}/chatMessages",
                method="POST",
                body=json.dumps({"text": f"is {url} down?"}),
                headers=headers,
            )


class Email:
    def __init__(self, to, at_most_every=600):
        self.to = to
        self.at_most_every = timedelta(at_most_every)
        self._last_time = datetime.datetime.utcnow() - self.at_most_every

        self.client = AsyncHTTPClient()

    async def report(self, url, message):
        now = datetime.datetime.utcnow()
        if now - self._last_time >= self.at_most_every:
            self._last_time = now

            data = {
                "from": "Is the Hub Up <ishubup@mg.wildtreetech.com>",
                "sender": "Is the Hub Up <ishubup@mg.wildtreetech.com>",
                "to": self.to,
                "subject": "%s is down" % url,
                "text": "%s\n\n%s"
                % (now.strftime("%d %B %Y at %X UTC"), message),
            }

            await self.client.fetch(
                "https://api.mailgun.net/v3/mg.wildtreetech.com/messages",
                method="POST",
                auth_username="api",
                auth_password=MG_API_KEY,
                body=urllib.parse.urlencode(data),
            )


async def main():
    checks = [
        IsUp(
            "https://mybinder.org",
            [
                Email("betatim@gmail.com"),
                Gitter("jupyterhub/mybinder.org-deploy"),
            ],
        ),
        IsUp(
            "https://archive.analytics.mybinder.org/",
            [
                Email("betatim@gmail.com"),
                Gitter("jupyterhub/mybinder.org-deploy"),
            ],
        ),
        IsUp(
            "https://hub.mybinder.org/hub/api",
            [
                Email("betatim@gmail.com"),
                Gitter("jupyterhub/mybinder.org-deploy"),
            ],
        ),
        BinderBuilds(
            "gh/binder-examples/requirements/master",
            [
                Email("betatim@gmail.com"),
                Gitter("jupyterhub/mybinder.org-deploy"),
            ],
        ),
        # IsUp(
        #    "https://httpbin.org/status/404",
        #    [Email("betatim@gmail.com"), Gitter("Build-a-binder/Lobby")],
        #    every=4,
        # ),
    ]
    for check in checks:
        IOLoop.current().add_callback(check.check)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        datefmt="%X",
        format="%(asctime)s %(levelname)-8s %(message)s",
    )

    IOLoop.current().run_sync(main)
    IOLoop.current().start()
