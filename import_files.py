#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GMG localfiles plugin -- local file import
# Copyright (C) 2012 Odin Hørthe Omdal
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import uuid

# This is here early because of a race
import mediagoblin
from mediagoblin.app import MediaGoblinApp
from mediagoblin import mg_globals
if __name__ == "__main__":
    mg_dir = os.path.dirname(mediagoblin.__path__[0])
    if os.path.exists(mg_dir + "/mediagoblin_local.ini"):
      config_file = mg_dir + "/mediagoblin_local.ini"
    elif os.path.exists(mg_dir + "/mediagoblin.ini"):
      config_file = mg_dir + "/mediagoblin.ini"
    else:
      raise Exception("Couldn't find mediagoblin.ini")

    mg_app = MediaGoblinApp(config_file, setup_celery=True)

    from mediagoblin.init.celery import setup_celery_app
    setup_celery_app(mg_globals.app_config, \
        mg_globals.global_config, force_celery_always_eager=True)

from celery import registry

from mediagoblin.tools.text import convert_to_tag_list_of_dicts
from mediagoblin.storage import clean_listy_filepath
from mediagoblin.processing import mark_entry_failed
from mediagoblin.processing.task import ProcessMedia
from mediagoblin.media_types import sniff_media, \
    InvalidFileType, FileTypeNotSupported


class MockMedia():
    filename = ""
    stream = None
    def __init__(self, filename, stream):
        self.filename = filename
        self.stream = stream


class ImportCommand(object):
    #args = '<poll_id poll_id ...>'
    help = 'Find new photos and add to database'

    def __init__(self, db, base_dir, **kwargs):
        self.db = db
        self.base_dir = base_dir

    def handle(self):
        #Photo.objects.all().delete()

        os.chdir(self.base_dir)

        for top, dirs, files in os.walk(u'.'):
            # Skip hidden folders
            if '/.' in top:
                continue
            # Skip cache folders
            if '_cache' in top:
                print "cache skip", top
                continue
            if top == ".":
                top = ""

            #folder, new_folder = Folder.objects.select_related("photos") \
            #        .get_or_create(path=os.path.normpath(top) + "/",
            #                defaults={'name': os.path.basename(top)})
            folder_path = os.path.normpath(top)
            try:
                cleaned_top = "/".join(clean_listy_filepath(folder_path.split("/")))
            except Exception:
                cleaned_top = top
            new_folder = not os.path.exists(os.path.join("mg_cache", cleaned_top))

            if not new_folder:
                print u"Skipping folder {0}".format(folder_path).encode("utf-8")
                continue
            new_files = list(set(os.path.splitext(i)[0] for i in files))
            new_files.sort(reverse=True)

            for new_filename in new_files:
                file_url = os.path.join(folder_path, new_filename)

                # More than one file with the same name but different
                # extension?
                exts = [os.path.splitext(f)[1] for f in files if new_filename
                        in f]

                assert len(exts) > 0, "Couldn't find file extension for %s" % file_url

                filepath = self.raw_alternative(file_url, exts)

                try:
                    self.import_file(MockMedia(
                        filename=filepath, stream=open(filepath, "r")))
                except Exception as e:
                    print u"file: {0}  exception: {1}".format(f, e).encode('utf-8')
                    continue


    def find_file(self, file_base, exts):
        """
        Find the raw file if there exist one

        @returns filepath
        """
        for ext in ['.nef', '.NEF']:
            if ext in exts and os.path.exists(file_base + ext):
                return file_base + ext
        return file_base + exts[0]

    def import_file(self, media):
        try:
            media_type, media_manager = sniff_media(media)
        except (InvalidFileType, FileTypeNotSupported) as e:
            print u"File error {0}: {1}".format(media.filename, repr(e)).encode("utf-8")
            return
        entry = self.db.MediaEntry()
        entry.media_type = unicode(media_type)
        entry.title = unicode(os.path.splitext(media.filename)[0])

        entry.uploader = 1
        # Process the user's folksonomy "tags"
        entry.tags = convert_to_tag_list_of_dicts("")
        # Generate a slug from the title
        entry.generate_slug()

        task_id = unicode(uuid.uuid4())

        entry.queued_media_file = media.filename.split("/")
        entry.queued_task_id = task_id

        entry.save()

        process_media = registry.tasks[ProcessMedia.name]
        try:
            process_media.apply_async( [unicode(entry.id)], {}, task_id=task_id)
        except BaseException as exc:
            mark_entry_failed(entry.id, exc)
            raise


if __name__ == "__main__":
    ic = ImportCommand(
        mg_app.db,
        mg_globals.global_config['storage:publicstore']['base_dir'])
    ic.handle()
