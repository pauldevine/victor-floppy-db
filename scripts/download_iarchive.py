#script to dowload the meta data for all floppies uploaded to internet archive
#i used this script to initially populate the database
import os
import sys
import json
import django
import internetarchive as ia
import dateparser

sys.path.insert(0, '/Users/pauldevine/projects/disk_db/victordisk')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")
django.setup()

from floppies.models import Entry, ArchCollection, Contributor, Creator, Language, Subject, Mediatype

def save_metadata_to_django(email):
    search_query = f'uploader:{email} AND mediatype:software'
    search_results = ia.search_items(search_query)

    for result in search_results:
        #identifier,file,description,subject[0],subject[1],subject[2],title,creator,date,collection,mediatype,contributor,language
        item_id = result['identifier']
        item = ia.get_item(item_id)
        metadata = item.metadata
        print("Identifier " + result['identifier'] + " " + metadata.get('title', ''))

        publicationDate_dt=dateparser.parse(metadata.get('publicdate', None))

        entry = Entry(
            identifier = metadata.get('identifier', ''),
            title = metadata.get('title', ''),
            publicationDate = publicationDate_dt,
            description = metadata.get('description', ''),
            uploaded = True
        )
        entry.save()

        # Handling ManyToMany fields like creators, languages, subjects
        creator_names = metadata.get('creator', [])
        if isinstance(creator_names, str):
            creator_names = [creator_names]
        for name in creator_names:
            creator, created = Creator.objects.get_or_create(name=name)
            entry.creators.add(creator)

        # Handling collections
        collection_names = metadata.get('collection', [])
        if isinstance(collection_names, str):
            collection_names = [collection_names]
        for name in collection_names:
            collection, created = ArchCollection.objects.get_or_create(name=name)
            entry.collections.add(collection)

        # Handling contributors
        contributor_names = metadata.get('contributor', [])
        if isinstance(contributor_names, str):
            contributor_names = [contributor_names]
        for name in contributor_names:
            contributor, created = Contributor.objects.get_or_create(name=name)
            entry.contributors.add(contributor)

        # Handling languages
        language_names = metadata.get('language', [])
        if isinstance(language_names, str):
            language_names = [language_names]
        for name in language_names:
            language, created = Language.objects.get_or_create(name=name)
            entry.languages.add(language)

        # Handling subjects
        subject_names = metadata.get('subject', [])
        if isinstance(subject_names, str):
            subject_names = subject_names.split(";")
        for name in subject_names:
            subject, created = Subject.objects.get_or_create(name=name)
            entry.subjects.add(subject)

        # Handling Mediatype if applicable
        mediatype_str = metadata.get('mediatype', [])
        mediatype_key = Mediatype.get_mediatype_key(mediatype_str)
        if mediatype_key:
            mediatype, created = Mediatype.objects.get_or_create(mediatype=mediatype_key)
            entry.mediatype = mediatype
            entry.save()

print("downloading Internet Arhive data for paul.devine@gmail.com")
save_metadata_to_django('paul.devine@gmail.com')
