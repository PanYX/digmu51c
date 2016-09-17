# -*- coding:utf8 -*-

from __future__ import (unicode_literals, print_function, division)

import base64
import binascii
import json
import os

from Crypto.Cipher import AES

#  from  https://github.com/darknessomi/musicbox/wiki/%E7%BD%91%E6%98%93%E4%BA%91%E9%9F%B3%E4%B9%90%E6%96%B0%E7%89%88WebAPI%E5%88%86%E6%9E%90%E3%80%82

MODULUS = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'
NONCE = '0CoJUm6Qyw8W8jud'
PUBKEY = '010001'


# noinspection PyPep8Naming
def aesEncrypt(text, secKey):
    pad = 16 - len(text) % 16
    text += pad * chr(pad)
    encryptor = AES.new(secKey, 2, '0102030405060708')
    ciphertext = encryptor.encrypt(text)
    ciphertext = base64.b64encode(ciphertext)
    return ciphertext.decode()


# noinspection PyPep8Naming
def rsaEncrypt(text, pk, ml):
    text = text[::-1].encode()
    rs = int(binascii.hexlify(text), 16) ** int(pk, 16) % int(ml, 16)
    return format(rs, 'x').zfill(256)


# noinspection PyPep8Naming
def createSecretKey(size):
    return (''.join(map(lambda xx: (hex(ord(xx))[2:]), os.urandom(size))))[0:16]


def get_api_formdata(data=None):
    sk = createSecretKey(16)
    return {
        'params': aesEncrypt(aesEncrypt(json.dumps(data) if data else '{}', NONCE), sk),
        'encSecKey': rsaEncrypt(sk, PUBKEY, MODULUS)
    }
