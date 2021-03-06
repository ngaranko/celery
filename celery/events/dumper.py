# -*- coding: utf-8 -*-
"""
    celery.events.dumper
    ~~~~~~~~~~~~~~~~~~~~

    THis is a simple program that dumps events to the console
    as they happen.  Think of it like a `tcpdump` for Celery events.

"""
from __future__ import absolute_import, print_function

import sys

from datetime import datetime

from celery.app import app_or_default
from celery.datastructures import LRUCache


TASK_NAMES = LRUCache(limit=0xFFF)

HUMAN_TYPES = {'worker-offline': 'shutdown',
               'worker-online': 'started',
               'worker-heartbeat': 'heartbeat'}


def humanize_type(type):
    try:
        return HUMAN_TYPES[type.lower()]
    except KeyError:
        return type.lower().replace('-', ' ')


class Dumper(object):

    def __init__(self, out=sys.stdout):
        self.out = out

    def say(self, msg):
        print(msg, file=self.out)

    def on_event(self, event):
        timestamp = datetime.utcfromtimestamp(event.pop('timestamp'))
        type = event.pop('type').lower()
        hostname = event.pop('hostname')
        if type.startswith('task-'):
            uuid = event.pop('uuid')
            if type in ('task-received', 'task-sent'):
                task = TASK_NAMES[uuid] = '{0}({1}) args={2} kwargs={3}' \
                    .format(
                        event.pop('name'), uuid,
                        event.pop('args'),
                        event.pop('kwargs'))
            else:
                task = TASK_NAMES.get(uuid, '')
            return self.format_task_event(hostname, timestamp,
                                          type, task, event)
        fields = ', '.join('{0}={1}'.format(key, event[key])
                        for key in sorted(event))
        sep = fields and ':' or ''
        self.say('{0} [{1}] {2}{3} {4}'.format(hostname, timestamp,
                                            humanize_type(type), sep, fields))

    def format_task_event(self, hostname, timestamp, type, task, event):
        fields = ', '.join('{0}={1}'.format(key, event[key])
                        for key in sorted(event))
        sep = fields and ':' or ''
        self.say('{0} [{1}] {2}{3} {4} {5}'.format(hostname, timestamp,
                    humanize_type(type), sep, task, fields))


def evdump(app=None, out=sys.stdout):
    app = app_or_default(app)
    dumper = Dumper(out=out)
    dumper.say('-> evdump: starting capture...')
    conn = app.connection()
    recv = app.events.Receiver(conn, handlers={'*': dumper.on_event})
    try:
        recv.capture()
    except (KeyboardInterrupt, SystemExit):
        conn and conn.close()

if __name__ == '__main__':  # pragma: no cover
    evdump()
