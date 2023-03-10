#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 26 19:57:52 2022

@author: jo
"""

import time
import datetime
import importlib
import pathlib
import bottle
import yaml
import subprocess


BCKND = None
CONFIG = {}
CONFIG_FILE = pathlib.Path('sound_rec.yml')


class Dummy():
    def __init__(self, backend=None, **config):
        self.config = config
        self.recording = False
        self.time = 0
        self.target = 'file.wav'

    def status(self):
        if self.recording:
            return dict(recording=self.recording,
                        time=time.time() - self.starttime,
                        target=self.target)
        else:
            return dict(recording=self.recording,
                        time=self.time,
                        target=self.target)

    def rec(self):
        if self.recording:
            self.stop()
        self.recording = True
        self.starttime = time.time()
        self.target = time.strftime('%Y%m%d_%H%M%S.wav',
                                    time.localtime(self.starttime))

    def stop(self):
        if self.recording:
            self.recording = False
            self.time = time.time() - self.starttime


class Parec():
    def __init__(self, path, backend=None, **config):
        self.cmdline = 'parec -r --file-format=WAV {}'
        self.path = pathlib.Path(path)
        if not self.path.is_dir():
            self.path.mkdir()
        self.config = config
        self.recording = False
        self.time = 0
        self.target = 'file.wav'

    def status(self):
        if self.recording:
            return dict(recording=self.recording,
                        time=time.time() - self.starttime,
                        target=self.target)
        else:
            return dict(recording=self.recording,
                        time=self.time,
                        target=self.target)

    def rec(self):
        if self.recording:
            self.stop()
        self.starttime = time.time()
        self.target = time.strftime('%Y%m%d_%H%M%S.wav',
                                    time.localtime(self.starttime))
        target = (self.path / self.target).with_suffix('.wav')
        self.process = subprocess.Popen(self.cmdline.format(target).split())
        self.recording = True

    def stop(self):
        if self.recording:
            self.process.terminate()
            self.recording = False
            self.time = time.time() - self.starttime
            self.process.wait()


def read_config():
    if CONFIG_FILE.is_file():
        with CONFIG_FILE.open() as f:
            return yaml.safe_load(f)
    return {}


def save_config(config):
    with CONFIG_FILE.open('w') as f:
        yaml.safe_dump(config, f)


def init_backend():
    bcknd = CONFIG.get('backend', None)
    if bcknd is not None:
        *mod, cls = bcknd.split('.')
        mod = '.'.join(mod)
        if mod:
            module = importlib.import_module(mod)
            get = module.__getattribute__
        else:
            module = globals()
            get = module.get
        return get(cls)(**CONFIG)


def stat():
    st = BCKND.status()
    st['duration'] = f"{st['time'] // 3600:02.0f}:{st['time'] // 60:02.0f}:{st['time'] % 60:02.0f}"
    return st


@bottle.route('/rec')
def rec():
    BCKND.rec()
    return stat()


@bottle.route('/stop')
def stop():
    BCKND.stop()
    return stat()


@bottle.route('/status')
def status():
    return stat()


@bottle.route('/config')
def config():
    global CONFIG
    global BCKND
    config = dict(bottle.request.params.items())
    if config:
        CONFIG.update(config)
        save_config(CONFIG)
        if BCKND is None:
            BCKND = init_backend()
    else:
        CONFIG = read_config()
    return CONFIG


if __name__ == '__main__':
    CONFIG.update(read_config())
    BCKND = init_backend()
    bottle.run(host='127.0.0.2', server='twisted', reloader=True, debug=True)
