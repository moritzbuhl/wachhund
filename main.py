# Copyright (c) 2020 Tobias Heider <tobias.heider@stusta.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import sys
import os
import subprocess
import time
import datetime
import asyncio
import config as c

from nio import AsyncClient, MatrixRoom, RoomMessageText

def log(msg):
    now_iso = datetime.datetime.now().isoformat()
    print("%s - %s" % (now_iso, msg))

async def init_matrix():
    client = AsyncClient(c.MATRIX_SERVER, c.MATRIX_USER)
    log(await client.login(c.MATRIX_PW))
    room_id=c.MATRIX_ROOM
    await client.join(c.MATRIX_ROOM)
    res = await client.joined_rooms()
    if room_id not in res.rooms:
        await client.join(room_id)
    return client

async def loop():
    matrix = await init_matrix()
    f = open(c.STATEFILE, "r+");

    log("init done")

    while True:
        commits = getcommits(f)
        for line in commits:
            log(line)
            content = prettify(line)
            await matrix.room_send(
                room_id=c.MATRIX_ROOM,
                message_type="m.room.message",
                content=content
            )
        time.sleep(60 * 5)

    f.close()

def prettify(commit):
    content = {
      "msgtype": "m.notice",
      "body": commit
    }
    l = commit.split(" ", 1)
    url = c.COMMIT_URL_TEMPLATE.format(l[0])
    pretty = "<pre><a href=\"{}\"><b>{}</b></a> {}</pre>".format(url, l[0], l[1])
    content["format"] = "org.matrix.custom.html"
    content["formatted_body"] = pretty
    return content

def getcommits(f):
    f.seek(0)
    last = f.read().rstrip('\n')
    try:
        subprocess.run(["git", "--git-dir={}".format(c.GIT_DIR), "fetch", "origin"], check=True)
        commits = subprocess.run(["git", "--git-dir=" + c.GIT_DIR, "log",
          "--oneline", "--no-decorate", "origin/master", "--"] + c.WATCHDIRS,
          stdout=subprocess.PIPE, text=True, check=True)
    except Exception as e:
        print(e, file = sys.stderr)
        return []

    changes = []
    newest = commits.stdout.split('\n')[0].split(" ", 1)[0]
    for line in commits.stdout.split('\n'):
        commit = line.split(" ", 1)
        if commit[0] == last:
            break
        if line == '':
            print("error: hash not found.", file = sys.stderr)
            return []
        changes.append(line)

    f.seek(0)
    f.write(newest + '\n')
    changes.reverse()
    return changes

asyncio.get_event_loop().run_until_complete(loop())
