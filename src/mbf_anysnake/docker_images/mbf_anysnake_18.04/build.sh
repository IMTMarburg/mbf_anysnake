#!/usr/bin/python3
import hashlib
import os
from pathlib import Path

hash = hashlib.md5()
hash.update((Path(__file__).parent / 'Dockerfile').read_bytes())
hash.update((Path(__file__).parent / 'sudoers').read_bytes())
tag = hash.hexdigest()

os.system('docker build -t mbf_anysnake_18.04:%s .' % tag)

