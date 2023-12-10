from django.db import models
from ckeditor.fields import RichTextField
from django.utils.translation import gettext_lazy as _

# Create your models here.
#csv for internet archive upload:
#  identifier,file,description,subject[0],subject[1],subject[2],title,creator,date,collection,mediatype,contributor,language

class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Creator(models.Model):
    name = models.CharField(max_length=500)
    def __str__(self):
        return self.name

class ArchCollection(models.Model):
    name = models.CharField(max_length=500)
    def __str__(self):
        return self.name

class Contributor(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Language(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Mediatype(models.Model):
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

    mediatype = models.CharField(
        max_length=2,
        choices=Mediatypes.choices,
        default=Mediatypes.SOFTWARE,
    )

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

    def __str__(self):
        return self.mediatype

class PhotoImage(models.Model):
    image = models.FileField(upload_to="images")

class RandoFile(models.Model):
    file = models.FileField(upload_to="randoFiles")

class Subject(models.Model):
    name = models.CharField(max_length=500)
    def __str__(self):
        return self.name
      
class ZipArchive(models.Model):
    archive = models.FileField(upload_to="archives")

class Entry(models.Model):
    identifier = models.SlugField(max_length=500)
    fullArchivePath = models.URLField(max_length=200, null=True, blank=True)
    folder = models.FileField(upload_to="diskMusteringArea")
    title = models.CharField(max_length=500)
    creators = models.ManyToManyField(Creator)
    publicationDate = models.DateField(null=True, blank=True)
    collections = models.ManyToManyField(ArchCollection)
    mediatype = Mediatype()
    contributors = models.ManyToManyField(Contributor)
    languages = models.ManyToManyField(Language)
    description = RichTextField()
    subjects = models.ManyToManyField(Subject)
    archive = ZipArchive()
    photos = models.ManyToManyField(PhotoImage)
    randoFiles = models.ManyToManyField(RandoFile)
    uploaded = models.BooleanField(default=False)
    hasFluxFile = models.BooleanField(default=False)
    hasFileContents = models.BooleanField(default=False)
    needsWork = models.BooleanField(default=False)
    readyToUpload = models.BooleanField(default=False)
    def get_absolute_url(self):
        return reverse("entry-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.title