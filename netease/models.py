# coding=utf-8
from __future__ import (unicode_literals, print_function)
import logging
import requests
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import python_2_unicode_compatible
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
import lxml.html
import json
from django.db import IntegrityError
from .api import get_api_formdata

MUSIC_163 = 'http://music.163.com'

logger = logging.getLogger(__name__)


class AbstractNetease(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=255, db_index=True)
    cover_url = models.URLField(blank=True, null=True)
    desc = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class CountLog(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    comment_count = models.PositiveIntegerField(null=True, blank=True)
    play_count = models.PositiveIntegerField(null=True, blank=True)
    share_count = models.PositiveIntegerField(null=True, blank=True)
    favourite_count = models.PositiveIntegerField(null=True, blank=True)
    log_date = models.DateField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'count log. {}'.format(self.pk)

    class Meta:
        unique_together = (('object_id', 'content_type', 'log_date'),)


class PlayListManager(models.Manager):

    def fetch(self):
        #  获取全部playlist url, 并解析得到playlist id 存入数据库。
        start_url = 'http://music.163.com/discover/playlist/'
        while start_url:
            try:
                r = requests.get(start_url)
            except requests.RequestException as e:
                logger.warning('request {} failed, --> {}'.format(start_url, e.message))
            else:
                h = lxml.html.fromstring(r.content.decode('utf-8'))
                msk = h.find_class('msk')
                for m in msk or []:
                    self.get_or_create(id=m.get('href').split('=')[1], defaults={'name': '', 'desc': '', })
                    logger.info(m.get('href'))
                znxt = h.find_class('znxt')
                start_url = (lambda x: 'http://music.163.com{}'.format(x) if x and x.startswith('/') else None)(
                    znxt[0].get('href') if znxt else None)
                if start_url:
                    logger.info('next url: {}'.format(start_url))


@python_2_unicode_compatible
class Tag(models.Model):
    name = models.CharField(max_length=16, unique=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class PlayList(AbstractNetease):
    tags = models.ManyToManyField(Tag)
    objects = PlayListManager()

    def __str__(self):
        return self.name

    def get_data(self):
        if self.name:
            return
        try:
            logger.info('request {}'.format(self.play_list_url))
            r = requests.get(self.play_list_url)
            if not r.ok:
                raise r.raise_for_status()
        except requests.RequestException as e:
            logger.warning('request {} failed.--> {}'.format(self.play_list_url, e.message))
        else:
            h = lxml.html.fromstring(r.content.decode('utf-8'))
            fav_count = (lambda x: x[0].get('data-count') if len(x) == 1 else None)(h.find_class('u-btni-fav'))
            share_class = h.find_class('u-btni-share')
            share_count = (lambda x: x[0].get('data-count') if len(x) == 1 else None)(share_class)
            try:
                play_count = (lambda x: x.text_content().strip() if x is not None else None)(
                    h.get_element_by_id('play-count'))
                comment_count = (lambda x: x.get('data-count') if x is not None else None)(
                    h.get_element_by_id('comment-box'))
            except KeyError:
                play_count, comment_count = None, None
            try:
                CountLog.objects.create(
                    content_object=self, comment_count=comment_count, play_count=play_count, share_count=share_count,
                    favourite_count=fav_count
                )
            except IntegrityError:
                logger.warning('count log IntegrityError')

            self.name = (lambda x: x[0].get('data-res-name') if len(x) == 1 else '')(share_class)
            self.cover_url = (lambda x: x[0].get('data-src') if len(x) == 1 else None)(h.find_class('j-img'))
            try:
                self.desc = h.get_element_by_id('album-desc-more').text_content().strip()
            except KeyError:
                self.desc = ''
            self.save()
            logger.info('playlist: {} - {}'.format(self.id, self.name))
            for t in [i.text_content() for i in h.find_class('u-tag')]:
                tag, _ = Tag.objects.get_or_create(name=t)
                self.tags.add(tag)
            try:
                song_list_pc = h.get_element_by_id('song-list-pre-cache')
            except KeyError:
                return
            if song_list_pc is not None:
                try:
                    song_list = (lambda x: json.loads(x[0].text_content().strip()) if len(x) == 1 else None)(
                        song_list_pc.findall('.//textarea[@style]'))
                except:
                    pass
                else:
                    try:
                        self.parse_song_list(song_list)
                    except IntegrityError:
                        logger.warning('parse song interityerror.....')

    def parse_song_list(self, song_list):
        logger.info('parse song list..')
        for s in song_list:

            album, _ = Album.objects.get_or_create(
                id=s['album']['id'],
                defaults={
                    'name': s['album']['name'], 'cover_url': s['album']['picUrl'], 'desc': ''
                }
            )
            song, _ = Song.objects.get_or_create(
                id=s['id'], defaults={'name': s['name'], 'desc': '', 'album': album, 'lyric': ''}
            )
            song.play_list.add(self)
            for a in s['artists']:
                artist, _ = Artist.objects.get_or_create(
                    id=a['id'], defaults={'name': a['name'], 'desc': ''}
                )
                song.artists.add(artist)
            if s['mvid']:
                mv, _ = Mv.objects.get_or_create(
                    id=s['mvid'], defaults={'name': '', 'desc': '', }
                )

    @property
    def play_list_url(self):
        return '{}/playlist?id={}'.format(MUSIC_163, self.id)

    @property
    def netease_url(self):
        return self.play_list_url


@python_2_unicode_compatible
class Artist(AbstractNetease):
    def __str__(self):
        return self.name

    @property
    def artist_url(self):
        return '{}/artist?id={}'.format(MUSIC_163, self.id)

    @property
    def netease_url(self):
        return self.artist_url


@python_2_unicode_compatible
class Album(AbstractNetease):
    artist = models.ForeignKey(Artist, blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    @property
    def album_url(self):
        return '{}/album?id={}'.format(MUSIC_163, self.id)

    @property
    def netease_url(self):
        return self.album_url


@python_2_unicode_compatible
class Mv(AbstractNetease):
    artist = models.ForeignKey(Artist, blank=True, null=True, on_delete=models.CASCADE)

    @property
    def mv_url(self):
        return '{}/mv?id={}'.format(MUSIC_163, self.id)

    @property
    def netease_url(self):
        return self.mv_url

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Song(AbstractNetease):
    play_list = models.ManyToManyField(PlayList)
    artists = models.ManyToManyField(Artist)
    album = models.ForeignKey(Album, blank=True, null=True, on_delete=models.CASCADE)
    lyric = models.TextField(blank=True)

    @property
    def song_url(self):
        return '{}/song?id={}'.format(MUSIC_163, self.id)

    @property
    def netease_url(self):
        return self.song_url

    def save(self, *args, **kwargs):
        if not self.album.artist and self.artists.count() == 1:
            self.album.artist = self.artists.first()
            self.album.save(update_fields=['artist'])
        super(Song, self).save(*args, **kwargs)

    def get_comment_count(self, data=None):
        url = 'http://music.163.com/weapi/v1/resource/comments/R_SO_4_{}'.format(self.id)
        try:
            r = requests.post(url,
                              headers={'Cookie': 'appver=2.7.1;', 'Referer': 'http://music.163.com/'},
                              data=data or get_api_formdata()
                              )
            if not r.ok:
                raise r.raise_for_status()
            r_json = r.json()
            if r_json.get('code') != 200:
                raise ValueError('{}'.format(r.content))
        except (requests.RequestException, ValueError):
            logger.warning('request {} failed.'.format(url))
        else:
            t = r_json.get('total')
            logger.info('song {} total comment count:{}'.format(self.id, t))
            try:
                CountLog.objects.create(
                    content_object=self, comment_count=t,
                )
            except IntegrityError:
                logger.warning('Song count log IntegrityError--{}'.format(self.id))

    @property
    def raw_song_url(self):
        return ''

    def __str__(self):
        return self.name
