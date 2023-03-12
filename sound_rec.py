#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 26 19:57:52 2022

@author: jo
"""

import time
import importlib
import pathlib
import bottle
import yaml
import subprocess


BCKND = None
CONFIG = {}
CONFIG_FILE = pathlib.Path('~/.config/sound_rec.yml').expanduser()


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
    def __init__(self, path, backend=None, file_format='WAV', file_name=None,
                 **config):
        if file_name is None:
            self.file_name = '%Y%m%d_%H%M%S'
        else:
            self.file_name = file_name
        self.file_format = file_format
        self.cmdline = f'parec -r --file-format={file_format} {{}}'
        self.path = pathlib.Path(path)
        if not self.path.is_dir():
            self.path.mkdir()
        self.config = config
        self.recording = False
        self.time = 0
        self.target = ''
        self.process = None
        self.error = None

    def status(self):
        if self.process is not None and self.process.poll() is not None:
            self.error = self.process.wait()
            self.recording = False
        res = dict(recording=self.recording,
                   time=self.time,
                   target=self.target)
        if self.recording:
            res['time'] = time.time() - self.starttime
        if self.error is not None:
            res['error'] = self.error
        return res

    def rec(self):
        if self.recording:
            self.stop()
        self.starttime = time.time()
        target = time.strftime(self.file_name,
                               time.localtime(self.starttime))
        target = (self.path / target).with_suffix(f'.{self.file_format.lower()}')
        self.target = str(target.relative_to(self.path))
        p = target.parent
        while not p.is_dir():
            if p.parent.is_dir():
                p.mkdir()
                break
            p = p.parent
        self.process = subprocess.Popen(self.cmdline.format(target).split())
        self.error = None
        self.recording = True

    def stop(self):
        if self.recording:
            self.process.terminate()
            self.recording = False
            self.time = time.time() - self.starttime
            self.error = self.process.wait()


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
        reload = config.pop('reload', False)
        CONFIG.update(config)
        save_config(CONFIG)
        if BCKND is None or reload is not False:
            BCKND = init_backend()
    else:
        CONFIG = read_config()
    return CONFIG


if __name__ == '__main__':
    CONFIG.update(read_config())
    BCKND = init_backend()
    bottle.run(host='127.0.0.1', port=8090, server='twisted',
               reloader=True, debug=True)
