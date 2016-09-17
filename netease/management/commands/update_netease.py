from django.core.management import BaseCommand
from netease.models import PlayList, Song
from multiprocessing.dummy import Pool as ThreadPool
from netease.api import get_api_formdata


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--fetch_playlist',
            action='store_true',
            default=False,
        )
        parser.add_argument(
            '--update_playlist',
            action='store_true',
            default=False,
        )
        parser.add_argument(
            '--update_song',
            action='store_true',
            default=False,
        )
        parser.add_argument(
            '--update_album',
            action='store_true',
            default=False,
        )
        parser.add_argument(
            '--update_artist',
            action='store_true',
            default=False,
        )

        parser.add_argument(
            '--update_mv',
            action='store_true',
            default=False,
        )

    def handle(self, *args, **options):
        pool = ThreadPool(8)
        api_data = get_api_formdata()
        if options['fetch_playlist']:
            PlayList.objects.fetch()
        elif options['update_playlist']:
            pl = PlayList.objects.all().order_by('id')
            pool.map(lambda x: x.get_data(), pl)
        elif options['update_song']:
            pool.map(lambda x: x.get_comment_count(api_data), Song.objects.all().order_by('id'))
        pool.close()
        pool.join()
