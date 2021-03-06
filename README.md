NB! This is **only** compatible with MediaGoblin 0.3.x, which is very old at this point.

I would be happy for help to port it to newer versions.

 gmg\_localfiles, plugin for GNU MediaGoblin
============================================

Plugin for importing files from your filesystem without duplication.

This plugin lets you have all your original files in one folder on your file
system, and it will stop MediaGoblin from copying those files to its own
locations.

It will try to make mediagoblin not touch/ruin your files (no guarantees!), but
it will make a `mg_cache` folder in the directory.

Example setup in `mediagoblin.ini`:

    [storage:queuestore]
    base_dir = /srv/media/Pictures
    storage_class = gmg_localfiles.storage:PersistentFileStorage

    [storage:publicstore]
    base_dir = /srv/media/Pictures
    base_url = /mgoblin_media/
    storage_class = gmg_localfiles.storage:PersistentFileStorage

    [plugins]
    [[gmg_localfiles]]

You will also need to serve the files, so in `paste.ini`:

    [app:publicstore_serve]
    use = egg:Paste#static
    document_root = %(here)s/user_dev/media/public/

Installation
------------

Put `gmg_localfiles` somewhere on your Python path. You might even just put it
inside the MediaGoblin folder if you want to be done with it quickly ;-)

Running
-------

Go into the `gmg_localfiles` folder and run `python import_files.py`.
