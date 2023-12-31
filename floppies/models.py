from django.db import models
from ckeditor.fields import RichTextField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# Create your models here.
#csv for internet archive upload:
#  identifier,file,description,subject[0],subject[1],subject[2],title,creator,date,collection,mediatype,contributor,language

class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Creator(BaseModel ):
    name = models.CharField(max_length=500)
    def __str__(self):
        return self.name

class ArchCollection(BaseModel):
    name = models.CharField(max_length=500)
    def __str__(self):
        return self.name

class Contributor(BaseModel):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class FluxFile(BaseModel):
    zipContent = models.OneToOneField('ZipContent', on_delete=models.CASCADE, primary_key=True)
    file = models.CharField(max_length=2048)
    def __str__(self):
        return self.file

class Language(BaseModel):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class PhotoImage(BaseModel):
    entry = models.ForeignKey('Entry', related_name='photos', on_delete=models.CASCADE, blank=False, null=False)
    image = models.CharField(max_length=2048)
    def __str__(self):
        return self.image

class RandoFile(BaseModel):
    file = models.CharField(max_length=2048)
    suffix = models.CharField(max_length=10, blank=True, null=True)
    entry = models.ForeignKey('Entry', related_name='randos', on_delete=models.CASCADE, blank=False, null=False)
    def __str__(self):
        return self.file

class Subject(BaseModel):
    name = models.CharField(max_length=500)
    def __str__(self):
        return self.name
      
class TextFile(BaseModel):
    zipContent = models.OneToOneField('ZipContent', on_delete=models.CASCADE, primary_key=True)
    raw_read = models.TextField(blank=False)
    converted = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.converted[:200]

class ZipArchive(BaseModel):
    archive = models.CharField(max_length=2048)
    entry = models.ForeignKey('Entry', related_name='ziparchives', on_delete=models.CASCADE, blank=False, null=False)
    def __str__(self):
        return self.archive

class ZipContent(BaseModel):
    zipArchive = models.ForeignKey('ZipArchive', on_delete=models.CASCADE, blank=False, null=False)
    file = models.CharField(max_length=2048)
    md5sum = models.CharField(max_length=32, blank=True, null=True)
    suffix = models.CharField(max_length=20, blank=True, null=True)
    size_bytes = models.BigIntegerField(blank=True, null=True)
    def __str__(self):
        return self.file

class Entry(BaseModel):
    class Mediatypes(models.TextChoices):
        TEXTS = "TX", _("Texts")
        ETREE = "ET", _("Etree")
        AUDIO = "AU", _("Audio")
        MOVIES = "MV", _("Movies")
        SOFTWARE = "SW", _("Software")
        IMAGE = "IM", _("Image")
        DATA = "DA", _("Data")
        WEB = "WB", _("Web")
        COLLECTION = "CO", _("Collection")
        ACCOUNT = "AC", _("Account")

        @classmethod
        def get_mediatype_key(cls, name):
            # Mapping of string representations to Mediatypes choices
            name_to_key = {
                "texts": cls.Mediatypes.TEXTS,
                "etree": cls.Mediatypes.ETREE,
                "audio": cls.Mediatypes.AUDIO,
                "movies": cls.Mediatypes.MOVIES,
                "software": cls.Mediatypes.SOFTWARE,
                "image": cls.Mediatypes.IMAGE,
                "data": cls.Mediatypes.DATA,
                "web": cls.Mediatypes.WEB,
                "collection": cls.Mediatypes.COLLECTION,
                "account": cls.Mediatypes.ACCOUNT
            }
            return name_to_key.get(name.lower(), cls.Mediatypes.SOFTWARE)


    identifier = models.CharField(max_length=500)
    fullArchivePath = models.URLField(max_length=600, blank=True, null=True)
    folder = models.CharField(max_length=2048, blank=True, null=True)
    title = models.CharField(max_length=500)
    creators = models.ManyToManyField(Creator, blank=True)
    publicationDate = models.DateField(null=True, blank=True)
    collections = models.ManyToManyField(ArchCollection, blank=True)
    mediatype = models.CharField(
        max_length=2,
        choices=Mediatypes,
        default=Mediatypes.SOFTWARE,
    )
    contributors = models.ManyToManyField(Contributor, blank=True)
    languages = models.ManyToManyField(Language, blank=True)
    description = RichTextField(blank=True, null=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    uploaded = models.BooleanField(default=False)
    hasFluxFile = models.BooleanField(default=False)
    hasFileContents = models.BooleanField(default=False)
    hasDiskImg = models.BooleanField(default=False)
    needsWork = models.BooleanField(default=False)
    readyToUpload = models.BooleanField(default=False)
    
    def get_absolute_url(self):
        return reverse("floppies:entry-update", kwargs={"pk": self.pk})

    def get_media_files(self):
        """
        Returns a list of file paths for the media files (zip archives and photos) related to this entry.
        """
        media_files = []

        # Add file paths from zip archives
        for zip_archive in self.zipArchives.all():
            media_files.append(zip_archive.archive)

        # Add file paths from photos
        for photo in self.photos.all():
            media_files.append(photo.image)

        return media_files

    def __str__(self):
        return self.title

class ScriptRun(BaseModel):
    entry = models.ForeignKey('Entry', on_delete=models.CASCADE, blank=False, null=False)
    text = models.TextField(blank=False)
    rumtime = models.DateTimeField(auto_now_add=True)
    parentPath = models.CharField(max_length=2048, blank=True, null=True)
    function = models.CharField(max_length=512, blank=True, null=True)
    script = models.CharField(max_length=2048, blank=True, null=True)
    def __str__(self):
        return self.parentPath + " " + self.rumtime.strftime("%Y-%m-%d %H:%M:%S")

class InfoChunk(BaseModel):
    # INFO Version (1 byte)
    fluxFile = models.OneToOneField('FluxFile', on_delete=models.CASCADE, primary_key=True)
    info_version = models.PositiveSmallIntegerField()

    # Creator (32 bytes string, UTF-8 encoded)
    creator = models.CharField(max_length=32)

    # Drive Type (1 byte, mapped to choices)
    DRIVE_TYPE_CHOICES = [
        (1, "5.25″ SS 40trk 0.25 step"),
        (2, "3.5″ DS 80trk Apple CLV"),
        (3, "5.25″ DS 80trk"),
        (4, "5.25″ DS 40trk"),
        (5, "3.5″ DS 80trk"),
        (6, "8″ DS"),
        (7, "3″ DS 80trk"),
        (8, "3″ DS 40trk"),
    ]
    drive_type = models.PositiveSmallIntegerField(choices=DRIVE_TYPE_CHOICES)

    # Write Protected (1 byte, boolean)
    write_protected = models.BooleanField()

    # Synchronized (1 byte, boolean)
    synchronized = models.BooleanField()

    # Hard Sector Count (1 byte)
    hard_sector_count = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.creator} (Version: {self.info_version})"

class MetaChunk(BaseModel):
    fluxFile = models.OneToOneField('FluxFile', on_delete=models.CASCADE, primary_key=True)
    title = models.CharField(max_length=255, blank=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    developer = models.CharField(max_length=255, blank=True, null=True)
    copyright = models.CharField(max_length=255, blank=True, null=True)
    version = models.CharField(max_length=255, blank=True, null=True)

    # Language choices
    LANGUAGES = [
        ('en', 'English'), ('es', 'Spanish'), ('fr', 'French'), ('de', 'German'),
        ('zh', 'Chinese'), ('ja', 'Japanese'), ('it', 'Italian'), ('nl', 'Dutch'),
        ('pt', 'Portuguese'), ('da', 'Danish'), ('fi', 'Finnish'), ('no', 'Norwegian'),
        ('sv', 'Swedish'), ('ru', 'Russian'), ('pl', 'Polish'), ('tr', 'Turkish'),
        ('ar', 'Arabic'), ('th', 'Thai'), ('cs', 'Czech'), ('hu', 'Hungarian'),
        ('ca', 'Catalan'), ('hr', 'Croatian'), ('el', 'Greek'), ('he', 'Hebrew'),
        ('ro', 'Romanian'), ('sk', 'Slovak'), ('uk', 'Ukrainian'), ('id', 'Indonesian'),
        ('ms', 'Malay'), ('vi', 'Vietnamese'),
        ('zz', 'Other'),
    ]

    language = models.CharField(max_length=2, choices=LANGUAGES, blank=True, null=True)

    requires_platform = models.CharField(max_length=255, blank=True, null=True)
    requires_machine = models.CharField(max_length=255, blank=True, null=True)
    requires_ram = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    side = models.CharField(max_length=255, blank=True, null=True)
    side_name = models.CharField(max_length=255, blank=True, null=True)
    contributor = models.CharField(max_length=255, blank=True, null=True)

    # ISO8601 date
    image_date = models.DateTimeField(blank=True, null=True)

    @classmethod
    def get_language_abbr(cls, language_name):
        """
        Returns the two-letter abbreviation for a given language name.
        If the language is not found, returns None.
        """
        for abbr, name in cls.LANGUAGES:
            if name.lower() == language_name.lower():
                return abbr
        return None

    @classmethod
    def get_language_from_abbr(cls, language_abbr):
        """
        Returns the two-letter abbreviation for a given language name.
        If the language is not found, returns None.
        """
        for abbr, name in cls.LANGUAGES:
            if abbr.lower() == language_abbr.lower():
                return name
        return None

    def __str__(self):
        return self.title if self.title else "Unnamed Meta Chunk"

    class Meta:
        verbose_name = "Meta Chunk"
        verbose_name_plural = "Meta Chunks"
