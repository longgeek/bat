#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Longgeek <longgeek@gmail.com>

import simplejson
from bat.lib import images
from bat.lib import monitors
from bat.lib import containers


def msg_main(msg):
    msg = simplejson.loads(msg)
    if 'container' in msg['message_type']:
        return containers.main(msg)

    elif 'image' in msg['message_type']:
        return images.main(msg)

    elif 'monitor' in msg['message_type']:
        return monitors.main(msg)
