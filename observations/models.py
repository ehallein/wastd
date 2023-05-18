"""Observation models.

These models support opportunistic encounters with stranded, dead, injured,
nesting turtles and possibly other wildlife, such as cetaceans and pinnipeds.

Species use a local name list, but should lookup a webservice.
This Observation is generic for all species. Other Models can FK this Model
to add species-specific measurements.

Observer name / address / phone / email is captured through the observer being
a system user.

The combination of species and health determines subsequent measurements and
actions:

* [turtle, dugong, cetacean] damage observation
* [turtle, dugong, cetacean] distinguishing features
* [taxon] morphometrics
* [flipper, pit, sat] tag observation
* disposal actions

"""
import itertools
import logging
import urllib
from datetime import timedelta
from dateutil import tz
from dateutil.relativedelta import relativedelta

import slugify
from django.conf import settings
from django.contrib.gis.db import models as geo_models
from django.db import models
from django.db.models.fields import DurationField
from django.template import loader
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition
from django_fsm_log.decorators import fsm_log_by, fsm_log_description
from django_fsm_log.models import StateLog
from polymorphic.models import PolymorphicModel
from rest_framework.reverse import reverse as rest_reverse

from shared.models import (
    LegacySourceMixin,
    QualityControlMixin,
    UrlsMixin,
)
from users.models import User, Organisation
from . import lookups


LOGGER = logging.getLogger("turtles")


def encounter_media(instance, filename):
    """Return an upload file path for an encounter media attachment."""
    if not instance.encounter.id:
        instance.encounter.save()
    return "encounter/{0}/{1}".format(instance.encounter.source_id, filename)


def campaign_media(instance, filename):
    """Return an upload file path for a campaign media attachment."""
    if not instance.campaign.id:
        instance.campaign.save()
    return "campaign/{0}/{1}".format(instance.campaign.id, filename)


def survey_media(instance, filename):
    """Return an upload path for survey media."""
    if not instance.survey.id:
        instance.survey.save()
    return "survey/{0}/{1}".format(instance.survey.id, filename)


class Area(geo_models.Model):
    """An area with a polygonal extent.

    This model accommodates anything with a polygonal extent, providing:

    * Area type (to classify different kinds of areas)
    * Area name must be unique within area type
    * Polygonal extent of the area

    Some additional fields are populated behind the scenes at each save and
    serve to cache low churn, high use content:

    * centroid: useful for spatial analysis and location queries
    * northern extent: useful to sort by latitude
    * as html: an HTML map popup
    """

    AREATYPE_MPA = "MPA"
    AREATYPE_LOCALITY = "Locality"
    AREATYPE_SITE = "Site"
    AREATYPE_DBCA_REGION = "Region"
    AREATYPE_DBCA_DISTRICT = "District"

    AREATYPE_CHOICES = (
        (AREATYPE_MPA, "MPA"),
        (AREATYPE_LOCALITY, "Locality"),
        (AREATYPE_SITE, "Site"),
        (AREATYPE_DBCA_REGION, "DBCA Region"),
        (AREATYPE_DBCA_DISTRICT, "DBCA District"),
    )

    area_type = models.CharField(
        max_length=300,
        verbose_name=_("Area type"),
        default=AREATYPE_SITE,
        choices=AREATYPE_CHOICES,
        help_text=_("The area type."),
    )

    name = models.CharField(
        max_length=1000,
        verbose_name=_("Area Name"),
        help_text=_("The name of the area."),
    )

    w2_location_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("W2 Location Code"),
        help_text=_(
            "The location code under which this area is known to the WAMTRAM turtle tagging database."
        ),
    )

    w2_place_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("W2 Place Code"),
        help_text=_(
            "The place code under which this area is known to the WAMTRAM turtle tagging database."
        ),
    )

    centroid = geo_models.PointField(
        srid=4326,
        editable=False,
        blank=True,
        null=True,
        verbose_name=_("Centroid"),
        help_text=_("The centroid is a simplified presentation of the Area."),
    )

    northern_extent = models.FloatField(
        verbose_name=_("Northernmost latitude"),
        editable=False,
        blank=True,
        null=True,
        help_text=_("The northernmost latitude serves to sort areas."),
    )

    length_surveyed_m = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name=_("Surveyed length [m]"),
        blank=True,
        null=True,
        help_text=_(
            "The length of meters covered by a survey of this area. "
            "E.g., the meters of high water mark along a beach."
        ),
    )

    length_survey_roundtrip_m = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name=_("Survey roundtrip [m]"),
        blank=True,
        null=True,
        help_text=_(
            "The total length of meters walked during an end to end "
            "survey of this area."
        ),
    )

    as_html = models.TextField(
        verbose_name=_("HTML representation"),
        blank=True,
        null=True,
        editable=False,
        help_text=_("The cached HTML representation for display purposes."),
    )

    geom = geo_models.PolygonField(
        srid=4326,
        verbose_name=_("Location"),
        help_text=_("The exact extent of the area as polygon in WGS84."),
    )

    class Meta:
        ordering = ["-northern_extent", "name"]
        unique_together = ("area_type", "name")
        verbose_name = "Area"
        verbose_name_plural = "Areas"

    def save(self, *args, **kwargs):
        """Cache centroid and northern extent."""
        self.as_html = self.get_popup
        if not self.northern_extent:
            self.northern_extent = self.derived_northern_extent
        if not self.centroid:
            self.centroid = self.derived_centroid
        super(Area, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.area_type} {self.name}"

    @property
    def derived_centroid(self):
        """The centroid, derived from the polygon."""
        return self.geom.centroid or None

    @property
    def derived_northern_extent(self):
        """The northern extent, derived from the polygon."""
        return self.geom.extent[3] or None

    @property
    def get_popup(self):
        """Generate HTML popup content."""
        t = loader.get_template("popup/{0}.html".format(self._meta.model_name))
        c = dict(original=self)
        return mark_safe(t.render(c))

    @property
    def leaflet_title(self):
        """A title for leaflet map markers."""
        return self.__str__()

    @property
    def absolute_admin_url(self):
        """Return the absolute admin change URL."""
        return reverse(
            "admin:{0}_{1}_change".format(self._meta.app_label, self._meta.model_name),
            args=[self.pk],
        )

    @property
    def all_encounters_url(self):
        """All Encounters within this Area."""
        return "/admin/observations/encounter/?{0}__id__exact={1}".format(
            "site" if self.area_type == Area.AREATYPE_SITE else "area",
            self.pk,
        )

    @property
    def animal_encounters_url(self):
        """The admin URL for AnimalEncounters within this Area."""
        return "/admin/observations/animalencounter/?{0}__id__exact={1}".format(
            "site" if self.area_type == Area.AREATYPE_SITE else "area",
            self.pk,
        )

    def make_rest_listurl(self, format="json"):
        """Return the API list URL in given format (default: JSON).

        Permissible formats depend on configured renderers:
        api (human readable HTML), csv, json, jsonp, yaml, latex (PDF).
        """
        return rest_reverse(self._meta.model_name + "-list", kwargs={"format": format})

    def make_rest_detailurl(self, format="json"):
        """Return the API detail URL in given format (default: JSON).

        Permissible formats depend on configured renderers:
        api (human readable HTML), csv, json, jsonp, yaml, latex (PDF).
        """
        return rest_reverse(
            self._meta.model_name + "-detail", kwargs={"pk": self.pk, "format": format}
        )


class SiteVisitStartEnd(geo_models.Model):
    """A start or end point to a site visit."""

    source = models.CharField(
        max_length=300,
        verbose_name=_("Data Source"),
        default=lookups.SOURCE_DEFAULT,
        choices=lookups.SOURCE_CHOICES,
        help_text=_("Where was this record captured initially?"),
    )

    source_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Source ID"),
        help_text=_(
            "The ID of the record in the original source, or "
            "a newly allocated ID if left blank. Delete and save "
            "to regenerate this ID."
        ),
    )

    datetime = models.DateTimeField(
        verbose_name=_("Observation time"),
        help_text=_("Local time (no daylight savings), stored as UTC."),
    )

    location = geo_models.PointField(
        srid=4326,
        verbose_name=_("Location"),
        help_text=_("The observation location as point in WGS84"),
    )

    type = models.CharField(
        max_length=300,
        verbose_name=_("Type"),
        choices=(("start", "start"), ("end", "end")),
        default="start",
        help_text=_("Start of end of site visit?"),
    )

    # media attachment

    def __str__(self):
        return "Site visit start or end on {0}".format(self.datetime.isoformat())


class Campaign(geo_models.Model):
    """An endeavour of a team to a Locality within a defined time range.

    * Campaign are owned by an Organisation.
    * Campaign own all Surveys and Encounters within its area and time range.
    * Campaign can nominate other Organisations as viewers of their data.

    High level specs: https://github.com/dbca-wa/biosys-turtles/issues/81
    """

    destination = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="campaigns",
        verbose_name=_("Destination"),
        help_text=_("The surveyed Locality."),
    )

    start_time = models.DateTimeField(
        verbose_name=_("Campaign start"),
        blank=True,
        null=True,
        help_text=_(
            "The Campaign start, shown as local time "
            "(no daylight savings), stored as UTC."
        ),
    )

    end_time = models.DateTimeField(
        verbose_name=_("Campaign end"),
        blank=True,
        null=True,
        help_text=_(
            "The Campaign end, shown as local time "
            "(no daylight savings), stored as UTC."
        ),
    )

    comments = models.TextField(
        verbose_name=_("Comments"),
        blank=True,
        null=True,
        help_text=_("Comments about the Campaign."),
    )

    team = models.ManyToManyField(User, blank=True, related_name="campaign_team")

    owner = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        editable=True,
        blank=True,
        null=True,
        related_name="campaigns",
        verbose_name=_("Owner"),
        help_text=_(
            "The organisation that ran this Campaign owns all records (Surveys and Encounters)."
        ),
    )

    viewers = models.ManyToManyField(
        Organisation,
        related_name="shared_campaigns",
        blank=True,
        help_text=_(
            "The nominated organisations are able to view the Campaign's records."
        ),
    )

    class Meta:
        ordering = ["-start_time", "destination", "owner"]

    def __str__(self):
        return "{0} {1} {2} to {3}".format(
            "-" if not self.owner else self.owner.label,
            "-" if not self.destination else self.destination.name,
            "na"
            if not self.start_time
            else self.start_time.astimezone(tz.tzlocal()).strftime("%Y-%m-%d"),
            "na"
            if not self.end_time
            else self.end_time.astimezone(tz.tzlocal()).strftime("%Y-%m-%d"),
        )

    @property
    def surveys(self):
        """Return a QuerySet of Surveys or None.

        If any of destination, start_time or end_time are empty, return None,
        else return Surveys within the Campaign's area and time range.
        """
        if self.destination and self.start_time and self.end_time:
            return Survey.objects.filter(
                site__geom__coveredby=self.destination.geom,
                start_time__gte=self.start_time,
                end_time__lte=self.end_time,
            )
        return None

    @property
    def orphaned_surveys(self):
        """Return Surveys that should be, but are not linked to this Campaign.

        This includes Surveys without a Campaign,
        and Surveys linked to another Campaign.
        We assume that Campaigns do not overlap.
        """
        if self.surveys:
            return self.surveys.exclude(campaign=self)
        return None

    @property
    def encounters(self):
        """Return the QuerySet of all Encounters within this Campaign."""
        if self.destination and self.start_time and self.end_time:
            return Encounter.objects.filter(
                where__coveredby=self.destination.geom,
                when__gte=self.start_time,
                when__lte=self.end_time,
            )
        return None

    @property
    def orphaned_encounters(self):
        """Return Encounters  that should be, but are not linked to this Campaign.

        This includes Encounters without a Campaign,
        and Encounters linked to another Campaign.
        We assume that Campaigns do not overlap.
        """
        if self.encounters:
            return self.encounters.exclude(campaign=self)
        return None

    def adopt_all_surveys_and_encounters(self):
        """Adopt all surveys and encounters in this Campaign."""
        no_svy = 0
        no_enc = 0
        if self.surveys:
            no_svy = self.surveys.update(campaign=self)
        if self.encounters:
            no_enc = self.encounters.update(campaign=self)
        LOGGER.info("Adopted {0} surveys and {1} encounters.".format(no_svy, no_enc))

    def adopt_all_orphaned_surveys_and_encounters(self):
        """Adopt all orphaned surveys and encounters in this Campaign."""
        no_svy = 0
        no_enc = 0
        if self.orphaned_surveys:
            no_svy = self.orphaned_surveys.update(campaign=self)
        if self.orphaned_encounters:
            no_enc = self.orphaned_encounters.update(campaign=self)
        LOGGER.info("Adopted {0} surveys and {1} encounters.".format(no_svy, no_enc))


class CampaignMediaAttachment(models.Model):
    """A media attachment to a Campaign."""

    MEDIA_TYPE_CHOICES = (
        ("datasheet", _("Data sheet")),
        ("journal", _("Field journal")),
        ("communication", _("Communication record")),
        ("photograph", _("Photograph")),
        ("other", _("Other")),
    )

    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Campaign"),
        help_text=_("The linked Campaign."),
    )

    media_type = models.CharField(
        max_length=300,
        verbose_name=_("Attachment type"),
        choices=MEDIA_TYPE_CHOICES,
        default="datasheet",
        help_text=_("What is the attached file about?"),
    )

    title = models.CharField(
        max_length=300,
        verbose_name=_("Attachment name"),
        blank=True,
        null=True,
        help_text=_("Give the attachment a representative name"),
    )

    attachment = models.FileField(
        upload_to=campaign_media,
        max_length=500,
        verbose_name=_("File attachment"),
        help_text=_("Upload the file"),
    )

    def __str__(self):
        return "Attachment {0} {1} for {2}".format(
            self.pk, self.title, self.campaign.__str__()
        )

    @property
    def filepath(self):
        """Path to file."""
        return force_text(self.attachment.file)


class Survey(QualityControlMixin, UrlsMixin, geo_models.Model):
    """A visit to one site by a team of field workers collecting data."""

    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_("Campaign"),
        help_text=_(
            "The overarching Campaign instigating this Survey "
            "is automatically linked when a Campaign is saved."
        ),
    )

    source = models.CharField(
        max_length=300,
        verbose_name=_("Data Source"),
        default=lookups.SOURCE_DEFAULT,
        choices=lookups.SOURCE_CHOICES,
        help_text=_("Where was this record captured initially?"),
    )

    source_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Source ID"),
        help_text=_("The ID of the start point in the original source."),
    )

    device_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Device ID"),
        help_text=_("The ID of the recording device, if available."),
    )

    area = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Surveyed Area"),
        related_name="survey_area",
        help_text=_("The general area this survey took place in."),
    )

    site = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Surveyed Site"),
        help_text=_("The surveyed site, if known."),
    )

    transect = geo_models.LineStringField(
        srid=4326,
        blank=True,
        null=True,
        verbose_name=_("Transect line"),
        help_text=_(
            "The surveyed path as LineString in WGS84, optional."
            " E.g. automatically captured by form Track Tally."
        ),
    )

    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_DEFAULT,
        default=settings.ADMIN_USER,
        related_name="reported_surveys",
        verbose_name=_("Recorded by"),
        blank=True,
        null=True,
        help_text=_(
            "The person who captured the start point, "
            "ideally this person also recoreded the encounters and end point."
        ),
    )

    start_location = geo_models.PointField(
        srid=4326,
        blank=True,
        null=True,
        verbose_name=_("Survey start point"),
        help_text=_("The start location as point in WGS84."),
    )

    start_location_accuracy_m = models.FloatField(
        verbose_name=_("Start location accuracy (m)"),
        null=True,
        blank=True,
        help_text=_("The accuracy of the supplied start location in metres, if given."),
    )

    start_time = models.DateTimeField(
        verbose_name=_("Survey start time"),
        blank=True,
        null=True,
        help_text=_(
            "The datetime of entering the site, shown as local time "
            "(no daylight savings), stored as UTC."
            " The time of 'feet in the sand, start recording encounters'."
        ),
    )

    start_photo = models.FileField(
        upload_to=survey_media,
        blank=True,
        null=True,
        max_length=500,
        verbose_name=_("Site photo start"),
        help_text=_("Site conditions at start of survey."),
    )

    start_comments = models.TextField(
        verbose_name=_("Comments at start"),
        blank=True,
        null=True,
        help_text=_(
            "Describe any circumstances affecting data collection, "
            "e.g. days without surveys."
        ),
    )

    end_source_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Source ID of end point"),
        help_text=_("The ID of the record in the original source."),
    )

    end_device_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("End Device ID"),
        help_text=_(
            "The ID of the recording device which captured the end point, if available."
        ),
    )

    end_location = geo_models.PointField(
        srid=4326,
        blank=True,
        null=True,
        verbose_name=_("Survey end point"),
        help_text=_("The end location as point in WGS84."),
    )

    end_location_accuracy_m = models.FloatField(
        verbose_name=_("End location accuracy (m)"),
        null=True,
        blank=True,
        help_text=_("The accuracy of the supplied end location in metres, if given."),
    )

    end_time = models.DateTimeField(
        verbose_name=_("Survey end time"),
        blank=True,
        null=True,
        help_text=_(
            "The datetime of leaving the site, shown as local time "
            "(no daylight savings), stored as UTC."
            " The time of 'feet in the sand, done recording encounters.'"
        ),
    )

    end_photo = models.FileField(
        upload_to=campaign_media,
        blank=True,
        null=True,
        max_length=500,
        verbose_name=_("Site photo end"),
        help_text=_("Site conditions at end of survey."),
    )

    end_comments = models.TextField(
        verbose_name=_("Comments at finish"),
        blank=True,
        null=True,
        help_text=_(
            "Describe any circumstances affecting data collection, "
            "e.g. days without surveys."
        ),
    )

    production = models.BooleanField(
        default=True,
        verbose_name=_("Production run"),
        help_text=_(
            "Whether the survey is a real (production) survey, or a training survey."
        ),
    )

    team = models.ManyToManyField(
        User,
        blank=True,
        related_name="survey_team",
        help_text=_(
            "Additional field workers, apart from the reporter,"
            " who assisted with data collection."
        ),
    )

    label = models.CharField(
        blank=True,
        null=True,
        max_length=500,
        verbose_name=_("Label"),
        help_text=_("A human-readable, self-explanatory label."),
    )

    class Meta:
        ordering = [
            "-start_time",
        ]
        unique_together = ("source", "source_id")

    def __str__(self):
        return self.label or str(self.pk)

    @property
    def make_label(self):
        return "Survey {0} of {1} from {2} {3} to {4}".format(
            self.pk,
            "unknown site" if not self.site else self.site.name,
            "na"
            if not self.start_time
            else self.start_time.astimezone(tz.tzlocal()).strftime("%Y-%m-%d "),
            ""
            if not self.start_time
            else self.start_time.astimezone(tz.tzlocal()).strftime("%H:%M"),
            ""
            if not self.end_time
            else self.end_time.astimezone(tz.tzlocal()).strftime("%H:%M %Z"),
        )

    def label_short(self):
        return "Survey {} of {}".format(self.pk, "unknown site" if not self.site else self.site.name)

    @property
    def as_html(self):
        """An HTML representation."""
        t = loader.get_template("popup/{0}.html".format(self._meta.model_name))
        return mark_safe(t.render({"original": self}))

    @property
    def absolute_admin_url(self):
        """Return the absolute admin change URL."""
        return reverse(
            "admin:{0}_{1}_change".format(self._meta.app_label, self._meta.model_name),
            args=[self.pk],
        )

    def card_template(self):
        return "observations/survey_card.html"

    @property
    def encounters(self):
        """Return the QuerySet of all Encounters within this Survey unless it's a training run."""
        if not self.production:
            LOGGER.info(
                "[observations.models.survey.encounters] Not a production survey, skipping."
            )
            return None
        if not self.end_time:
            LOGGER.info(
                "[observations.models.survey.encounters] No end_time set, can't filter Encounters."
            )
            return None
        elif not self.site:
            LOGGER.info(
                "[observations.models.survey.encounters] No site set, can't filter Encounters."
            )
            return None
        else:
            # https://docs.djangoproject.com/en/3.2/ref/contrib/gis/geoquerysets/#coveredby
            return Encounter.objects.filter(
                where__coveredby=self.site.geom,
                when__gte=self.start_time,
                when__lte=self.end_time,
            )

    @property
    def start_date(self):
        """The calendar date of the survey's start time in the local timezone."""
        return self.start_time.astimezone(tz.tzlocal()).date()

    @property
    def duplicate_surveys(self):
        """A queryset of other surveys on the same date and site with intersecting durations."""
        return (
            Survey.objects.filter(site=self.site, start_time__date=self.start_date)
            .exclude(pk=self.pk)
            .exclude(start_time__gte=self.end_time)  # surveys starting after self
            .exclude(end_time__lte=self.start_time)  # surveys ending before self
        )

    @property
    def no_duplicates(self):
        """The number of duplicate surveys."""
        return self.duplicate_surveys.count()

    @property
    def has_duplicates(self):
        """Whether there are duplicate surveys."""
        return self.no_duplicates > 0

    def close_duplicates(self, actor=None):
        """Mark this Survey as the only production survey, others as training and adopt all Encounters.

        Data import of Surveys reconstructed from SVS and SVE, adjusting site bondaries,
        and previous import algorithms, can cause duplicate Surveys to be created.

        The QA operator needs to identify duplicates, mark each as "not production" (=training, testing, or duplicate),
        set this Survey as "production", then save each of them and set to "curated".

        Duplicate Surveys are recognized by an overlap of place and time. They can however extend longer individually,
        so that duplicates can contain Encounters outside the duration of the production Survey.
        The remaining production Survey needs to adjust its start and end time to include all Encounters of all closed
        duplicate surveys.

        The production Survey adopts all Encounters within its spatial bounds.
        Encounters outside its spatial bounds can occur if the Survey site was adjusted manually.
        These will be orphaned after this operation, and can be adopted either by saving an adjacent survey,
        or running "adopt orphaned encounters".
        """
        survey_pks = [survey.pk for survey in self.duplicate_surveys.all()] + [self.pk]
        all_encounters = Encounter.objects.filter(survey_id__in=survey_pks)
        curator = actor if actor else User.objects.get(pk=1)
        msg = "Closing {0} duplicate(s) of Survey {1} as {2}.".format(
            len(survey_pks) - 1, self.pk, curator
        )

        # All duplicate Surveys shall be closed (not production) and own no Encounters
        for d in self.duplicate_surveys.all():
            LOGGER.info("Closing Survey {0} with actor {1}".format(d.pk, curator))
            d.production = False
            d.save()
            if d.status != QualityControlMixin.STATUS_CURATED:
                d.curate(by=curator)
                d.save()
            for a in d.attachments.all():
                a.survey = self
                a.save()

        # From all Encounters (if any), adjust duration
        if all_encounters.count() > 0:
            earliest_enc = min([e.when for e in all_encounters])
            earliest_buffered = earliest_enc - timedelta(minutes=30)
            latest_enc = max([e.when for e in all_encounters])
            latest_buffered = latest_enc + timedelta(minutes=30)

            msg += " {0} combined Encounters were found from duplicates between {1} and {2}.".format(
                all_encounters.count(),
                earliest_enc.astimezone(tz.tzlocal()).strftime("%Y-%m-%d %H:%M %Z"),
                latest_enc.astimezone(tz.tzlocal()).strftime("%Y-%m-%d %H:%M %Z"),
            )
            if earliest_enc < self.start_time:
                msg += " Adjusted Survey start time from {0} to 30 mins before earliest Encounter, {1}.".format(
                    self.start_time.astimezone(tz.tzlocal()).strftime(
                        "%Y-%m-%d %H:%M %Z"
                    ),
                    earliest_buffered.astimezone(tz.tzlocal()).strftime(
                        "%Y-%m-%d %H:%M %Z"
                    ),
                )
                self.start_time = earliest_buffered
            if latest_enc > self.end_time:
                msg += " Adjusted Survey end time from {0} to 30 mins after latest Encounter, {1}.".format(
                    self.end_time.astimezone(tz.tzlocal()).strftime(
                        "%Y-%m-%d %H:%M %Z"
                    ),
                    latest_buffered.astimezone(tz.tzlocal()).strftime(
                        "%Y-%m-%d %H:%M %Z"
                    ),
                )
                self.end_time = latest_buffered

        # This Survey is the production survey owning all Encounters
        self.production = True
        self.save()
        if self.status != QualityControlMixin.STATUS_CURATED:
            self.curate(by=curator)
            self.save()

        # ...except cuckoo Encounters
        if all_encounters.count() > 0 and self.site is not None:
            cuckoo_encounters = all_encounters.exclude(where__coveredby=self.site.geom)
            for e in cuckoo_encounters:
                e.site = None
                e.survey = None
                e.save()
            msg += " Evicted {0} cuckoo Encounters observed outside the site.".format(
                cuckoo_encounters.count()
            )

        # Post-save runs claim_encounters
        self.save()
        LOGGER.info(msg)
        return msg


def claim_end_points(survey_instance):
    """Claim SurveyEnd.

    The first SurveyEnd with the matching site,
    and an end_time within six hours after start_time is used
    to set corresponding end_location, end_time, end_comments,
    end_photo and end_source_id.

    Since the end point could be taken with a different device (e.g.
    if primary device malfunctions), we will not filter down to
    the same device_id.

    If no SurveyEnd is found and no end_time is set, the end_time is set to
    start_time plus six hours. This should allow the survey to claim its Encounters.

    TODO we could be a bit cleverer and find the latest encounter on the same day and site.
    """
    se = SurveyEnd.objects.filter(
        site=survey_instance.site,
        # device_id=survey_instance.device_id,
        end_time__gte=survey_instance.start_time,
        end_time__lte=survey_instance.start_time + timedelta(hours=6),
    ).first()
    if se:
        survey_instance.end_location = se.end_location
        survey_instance.end_time = se.end_time
        survey_instance.end_comments = se.end_comments
        survey_instance.end_photo = se.end_photo
        survey_instance.end_source_id = se.source_id
        survey_instance.end_device_id = se.device_id
    else:
        if not survey_instance.end_time:
            survey_instance.end_time = survey_instance.start_time + timedelta(hours=6)
            survey_instance.end_comments = (
                "[NEEDS QA][Missing SiteVisitEnd] Survey end guessed."
            )
            LOGGER.info(
                "[Survey.claim_end_points] Missing SiteVisitEnd for Survey"
                " {0}".format(survey_instance)
            )


class SurveyEnd(geo_models.Model):
    """A visit to one site by a team of field workers collecting data."""

    source = models.CharField(
        max_length=300,
        verbose_name=_("Data Source"),
        default=lookups.SOURCE_DEFAULT,
        choices=lookups.SOURCE_CHOICES,
        help_text=_("Where was this record captured initially?"),
    )

    source_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Source ID"),
        help_text=_("The ID of the start point in the original source."),
    )

    device_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Device ID"),
        help_text=_("The ID of the recording device, if available."),
    )

    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_DEFAULT,
        default=settings.ADMIN_USER,
        verbose_name=_("Recorded by"),
        blank=True,
        null=True,
        help_text=_(
            "The person who captured the start point, "
            "ideally this person also recoreded the encounters and end point."
        ),
    )

    site = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Surveyed site"),
        help_text=_("The surveyed site, if known."),
    )

    end_location = geo_models.PointField(
        srid=4326,
        blank=True,
        null=True,
        verbose_name=_("Survey end point"),
        help_text=_("The end location as point in WGS84."),
    )

    end_time = models.DateTimeField(
        verbose_name=_("Survey end time"),
        blank=True,
        null=True,
        help_text=_(
            "The datetime of leaving the site, shown as local time "
            "(no daylight savings), stored as UTC."
            " The time of 'feet in the sand, done recording encounters.'"
        ),
    )

    end_photo = models.FileField(
        upload_to=survey_media,
        max_length=500,
        verbose_name=_("Site photo end"),
        help_text=_("Site conditions at end of survey."),
    )

    end_comments = models.TextField(
        verbose_name=_("Comments at finish"),
        blank=True,
        null=True,
        help_text=_(
            "Describe any circumstances affecting data collection, "
            "e.g. days without surveys."
        ),
    )

    class Meta:
        verbose_name = "Survey"
        verbose_name_plural = "Surveys"
        ordering = ["end_location", "end_time"]
        unique_together = ("source", "source_id")

    def save(self, *args, **kwargs):
        """Guess site."""
        self.site = self.guess_site
        super(SurveyEnd, self).save(*args, **kwargs)

    def __str__(self):
        return "SurveyEnd {0} at {1} on {2}".format(
            self.pk,
            "na" if not self.site else self.site,
            "na" if not self.end_time else self.end_time.isoformat(),
        )

    @property
    def guess_site(self):
        """Return the first Area containing the start_location or None."""
        candidates = Area.objects.filter(
            area_type=Area.AREATYPE_SITE, geom__covers=self.end_location
        )
        return None if not candidates else candidates.first()


class SurveyMediaAttachment(LegacySourceMixin, models.Model):
    """A media attachment to a Survey, e.g. start or end photos."""

    MEDIA_TYPE_CHOICES = (
        ("data_sheet", _("Data sheet")),
        ("communication", _("Communication record")),
        ("photograph", _("Photograph")),
        ("other", _("Other")),
    )

    survey = models.ForeignKey(
        Survey,
        on_delete=models.PROTECT,
        verbose_name=_("Survey"),
        related_name="attachments",
        help_text=("The Survey this attachment belongs to."),
    )

    media_type = models.CharField(
        max_length=300,
        verbose_name=_("Attachment type"),
        choices=MEDIA_TYPE_CHOICES,
        default="photograph",
        help_text=_("What is the attached file about?"),
    )

    title = models.CharField(
        max_length=300,
        verbose_name=_("Attachment name"),
        blank=True,
        null=True,
        help_text=_("Give the attachment a representative name."),
    )

    attachment = models.FileField(
        upload_to=survey_media,
        max_length=500,
        verbose_name=_("File attachment"),
        help_text=_("Upload the file."),
    )

    class Meta:
        verbose_name = "Survey Media Attachment"

    def __str__(self):
        return "Media {0} {1} for {2}".format(
            self.pk if self.pk else "",
            self.title,
            self.survey.__str__() if self.survey else "",
        )

    @property
    def filepath(self):
        """The path to attached file."""
        try:
            fpath = force_text(self.attachment.file)
        except BaseException:
            fpath = None
        return fpath

    @property
    def thumbnail(self):
        if self.attachment:
            return mark_safe(
                '<a href="{0}" target="_" rel="nofollow" '
                'title="Click to view full screen in new browser tab">'
                '<img src="{0}" alt="{1} {2}" style="height:100px;"></img>'
                "</a>".format(
                    self.attachment.url, self.get_media_type_display(), self.title
                )
            )
        else:
            return ""


# Encounter models -----------------------------------------------------------#
class Encounter(PolymorphicModel, UrlsMixin, geo_models.Model):
    """The base Encounter class.

    * When: Datetime of encounter, stored in UTC, entered and displayed in local
      timezome.
    * Where: Point in WGS84.
    * Who: The observer has to be a registered system user.
    * Source: The previous point of truth for the record.
    * Source ID: The ID of the encounter at the previous point of truth. This
      can be a corporate file number, a database primary key, and likely is
      prefixed or post-fixed. Batch imports can (if they use the ID consistently)
      use the ID to identify previously imported records and avoid duplication.

    A suggested naming standard for paper records is
    ``<prefix><date><running-number>``, with possible

    * prefix indicates data type (stranding, tagging, nest obs etc)
    * date is reversed Y-m-d
    * a running number caters for multiple records of the same prefix and date

    These Paper record IDs should be recorded on the original paper forms
    (before scanning), used as file names for the PDF'd scans, and typed into
    WAStD.

    The QA status can only be changed through transition methods, not directly.
    Changes to the QA status, as wells as versions of the data are logged to
    preserve the data lineage.
    """

    LOCATION_DEFAULT = "1000"
    LOCATION_ACCURACY_CHOICES = (
        ("10", _("GPS reading at exact location (10 m)")),
        (LOCATION_DEFAULT, _("Site centroid or place name (1 km)")),
        ("10000", _("Rough estimate (10 km)")),
    )

    ENCOUNTER_STRANDING = "stranding"
    ENCOUNTER_TAGGING = "tagging"
    ENCOUNTER_INWATER = "inwater"
    ENCOUNTER_NEST = "nest"
    ENCOUNTER_TRACKS = "tracks"
    ENCOUNTER_TAG = "tag-management"
    ENCOUNTER_LOGGER = "logger"
    ENCOUNTER_OTHER = "other"

    ENCOUNTER_TYPES = (
        (ENCOUNTER_STRANDING, "Stranding"),
        (ENCOUNTER_TAGGING, "Tagging"),
        (ENCOUNTER_NEST, "Nest"),
        (ENCOUNTER_TRACKS, "Tracks"),
        (ENCOUNTER_INWATER, "In water"),
        (ENCOUNTER_TAG, "Tag Management"),
        (ENCOUNTER_LOGGER, "Logger"),
        (ENCOUNTER_OTHER, "Other"),
    )

    LEAFLET_ICON = {
        ENCOUNTER_STRANDING: "exclamation-circle",
        ENCOUNTER_TAGGING: "tags",
        ENCOUNTER_NEST: "home",
        ENCOUNTER_TRACKS: "truck",
        ENCOUNTER_TAG: "cog",
        ENCOUNTER_INWATER: "tint",
        ENCOUNTER_LOGGER: "tablet",
        ENCOUNTER_OTHER: "question-circle",
    }

    LEAFLET_COLOUR = {
        ENCOUNTER_STRANDING: "darkred",
        ENCOUNTER_TAGGING: "blue",
        ENCOUNTER_INWATER: "blue",
        ENCOUNTER_NEST: "green",
        ENCOUNTER_TRACKS: "cadetblue",
        ENCOUNTER_TAG: "darkpuple",
        ENCOUNTER_LOGGER: "orange",
        ENCOUNTER_OTHER: "purple",
    }

    STATUS_NEW = "new"
    STATUS_IMPORTED = "imported"
    STATUS_MANUAL_INPUT = "manual input"
    STATUS_PROOFREAD = "proofread"
    STATUS_CURATED = "curated"
    STATUS_PUBLISHED = "published"
    STATUS_FLAGGED = "flagged"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = (
        (STATUS_NEW, _("New")),
        (STATUS_IMPORTED, _("Imported")),
        (STATUS_MANUAL_INPUT, _("Manual input")),
        (STATUS_PROOFREAD, _("Proofread")),
        (STATUS_CURATED, _("Curated")),
        (STATUS_PUBLISHED, _("Published")),
        (STATUS_FLAGGED, _("Flagged")),
        (STATUS_REJECTED, _("Rejected")),
    )

    STATUS_LABELS = {
        STATUS_NEW: "secondary",
        STATUS_IMPORTED: "secondary",
        STATUS_MANUAL_INPUT: "secondary",
        STATUS_PROOFREAD: "warning",
        STATUS_CURATED: "success",
        STATUS_PUBLISHED: "info",
        STATUS_FLAGGED: "warning",
        STATUS_REJECTED: "danger",
    }

    status = FSMField(
        default=STATUS_NEW, choices=STATUS_CHOICES, verbose_name=_("QA Status")
    )

    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_("Campaign"),
        help_text=_(
            "The overarching Campaign instigating this Encounter "
            "is automatically linked when a Campaign saved."
        ),
    )

    survey = models.ForeignKey(
        Survey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Survey"),
        # related_name='encounters', # clashes with Survey.encounters property
        help_text=_("The survey during which this encounter happened."),
    )

    area = models.ForeignKey(
        Area,  # Always an Area of type 'Locality'.
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Area"),
        related_name="encounter_area",
        help_text=_("The general area this encounter took place in."),
    )

    site = models.ForeignKey(
        Area,  # Always an Area of type 'Site'.
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Surveyed site"),
        related_name="encounter_site",
        help_text=_("The surveyed site, if known."),
    )

    source = models.CharField(
        max_length=300,
        db_index=True,
        verbose_name=_("Data Source"),
        default=lookups.SOURCE_DEFAULT,
        choices=lookups.SOURCE_CHOICES,
        help_text=_("Where was this record captured initially?"),
    )

    source_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Source ID"),
        help_text=_(
            "The ID of the record in the original source, or "
            "a newly allocated ID if left blank. Delete and save "
            "to regenerate this ID."
        ),
    )

    where = geo_models.PointField(
        srid=4326,
        verbose_name=_("Observed at"),
        help_text=_("The observation location as point in WGS84"),
    )

    when = models.DateTimeField(
        db_index=True,
        verbose_name=_("Observed on"),
        help_text=_(
            "The observation datetime, shown as local time "
            "(no daylight savings), stored as UTC."
        ),
    )

    location_accuracy = models.CharField(
        max_length=300,
        verbose_name=_("Location accuracy class (m)"),
        default=LOCATION_DEFAULT,
        choices=LOCATION_ACCURACY_CHOICES,
        help_text=_(
            "The source of the supplied location " "implies a rough location accuracy."
        ),
    )

    location_accuracy_m = models.FloatField(
        verbose_name=_("Location accuracy (m)"),
        null=True,
        blank=True,
        help_text=_("The accuracy of the supplied location in metres, if given."),
    )

    name = models.CharField(
        max_length=1000,
        editable=False,
        blank=True,
        null=True,
        verbose_name=_("Encounter Subject Identifer"),
        help_text=_(
            "An automatically inferred read-only identifier for the encountered subject,"
            " e.g. in the case of AnimalEncounters, the animal's earliest associated tag ID."
            " Encounters with the same identifer are encounters of the same subject (e.g. the same turtle)."
        ),
    )

    observer = models.ForeignKey(
        User,
        on_delete=models.SET_DEFAULT,
        default=settings.ADMIN_USER,
        verbose_name=_("Observed by"),
        related_name="encounters_observed",
        help_text=_(
            "The person who encountered the subject, and executed any measurements. "
            "The observer is the source of measurement bias."
        ),
    )

    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_DEFAULT,
        default=settings.ADMIN_USER,
        verbose_name=_("Recorded by"),
        related_name="encounters_reported",
        help_text=_(
            "The person who wrote the initial data sheet in the field. "
            "The reporter is the source of handwriting and spelling errors. "
        ),
    )

    as_html = models.TextField(
        verbose_name=_("HTML representation"),
        blank=True,
        null=True,
        editable=False,
        help_text=_("The cached HTML representation for display purposes."),
    )

    as_latex = models.TextField(
        verbose_name=_("Latex fragment"),
        blank=True,
        null=True,
        editable=False,
        help_text=_("The cached Latex fragment for reporting purposes."),
    )

    encounter_type = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        editable=False,
        verbose_name=_("Encounter type"),
        default=ENCOUNTER_STRANDING,
        choices=ENCOUNTER_TYPES,
        help_text=_("The primary concern of this encounter."),
    )

    comments = models.TextField(
        verbose_name=_("Comments"),
        blank=True,
        null=True,
        help_text=_("Comments"),
    )

    class Meta:
        ordering = ["-when", "where"]
        unique_together = ("source", "source_id")
        index_together = [
            ["when", "where"],
        ]
        verbose_name = "Encounter"
        verbose_name_plural = "Encounters"
        get_latest_by = "when"

    @property
    def opts(self):
        """Make _meta accessible from templates."""
        return self._meta

    def __str__(self):
        return "Encounter {0} on {1} by {2}".format(self.pk, self.when, self.observer)

    @property
    def status_colour(self):
        """Return a Bootstrap4 CSS colour class for each status."""
        return self.STATUS_LABELS[self.status]

    # FSM transitions --------------------------------------------------------#
    #def can_proofread(self):
    #    """Return true if this document can be proofread."""
    #    return True

    # New -> Proofread
    #@fsm_log_by
    #@transition(
    #    field=status,
    #    source=STATUS_NEW,
    #    target=STATUS_PROOFREAD,
    #    conditions=[can_proofread],
    #    # permission=lambda instance, user: user in instance.all_permitted,
    #    custom=dict(
    #        verbose="Submit for QA",
    #        explanation=(
    #            "Submit this record as a faithful representation of the "
    #            "data source for QA to become an accepted record."
    #        ),
    #        notify=True,
    #    ),
    #)
    #def proofread(self, by=None):
    #    """Mark encounter as proof-read.

    #    Proofreading compares the attached data sheet with entered values.
    #    Proofread data is deemed a faithful representation of original data
    #    captured on a paper field data collection form, or stored in a legacy
    #    system.
    #    """
    #    return

    #def can_require_proofreading(self):
    #    """Return true if this document can be proofread."""
    #    return True

    # Proofread -> New
    #@fsm_log_by
    #@transition(
    #    field=status,
    #    source=STATUS_PROOFREAD,
    #    target=STATUS_NEW,
    #    conditions=[can_require_proofreading],
    #    # permission=lambda instance, user: user in instance.all_permitted,
    #    custom=dict(
    #        verbose="Require proofreading",
    #        explanation=(
    #            "This record deviates from the data source and "
    #            "requires proofreading."
    #        ),
    #        notify=True,
    #    ),
    #)
    #def require_proofreading(self, by=None):
    #    """Mark encounter as having typos, requiring more proofreading.

    #    Proofreading compares the attached data sheet with entered values.
    #    If a discrepancy to the data sheet is found, proofreading is required.
    #    """
    #    return

    def can_curate(self):
        """Return true if this record can be accepted."""
        return True

    # New|Imported|Manual input|Flagged -> Curated
    @fsm_log_by
    @fsm_log_description
    @transition(
        field=status,
        source=[STATUS_NEW, STATUS_IMPORTED, STATUS_MANUAL_INPUT, STATUS_FLAGGED],
        target=STATUS_CURATED,
        conditions=[can_curate],
        # permission=lambda instance, user: user in instance.all_permitted,
        custom=dict(
            verbose="Curate as trustworthy",
            explanation=("This record is deemed trustworthy."),
            notify=True,
            url_path="curate/",
            badge="badge-success",
        ),
    )
    def curate(self, by=None, description=None):
        """Accept record as trustworthy.

        Curated data is deemed trustworthy by a subject matter expert.
        Records can be marked as curated from new, proofread, or flagged.
        """
        return

    def can_flag(self):
        """Return true if curated status can be revoked."""
        return True

    # New|Imported|Manual input|Curated -> Flagged
    @fsm_log_by
    @fsm_log_description
    @transition(
        field=status,
        source=[STATUS_NEW, STATUS_IMPORTED, STATUS_MANUAL_INPUT, STATUS_CURATED],
        target=STATUS_FLAGGED,
        conditions=[can_flag],
        # permission=lambda instance, user: user in instance.all_permitted,
        custom=dict(
            verbose="Flag as not trustworthy",
            explanation=(
                "This record cannot be true. This record requires"
                " review by a subject matter expert."
            ),
            notify=True,
            url_path="flag/",
            badge="badge-warning",
        ),
    )
    def flag(self, by=None, description=None):
        """Flag as requiring review by a subject matter expert.
        """
        return

    def can_reject(self):
        """Return true if the record can be rejected as entirely wrong.
        """
        return True

    # New|Imported|Manual input|Flagged -> Rejected
    @fsm_log_by
    @fsm_log_description
    @transition(
        field=status,
        source=[STATUS_NEW, STATUS_IMPORTED, STATUS_MANUAL_INPUT, STATUS_FLAGGED],
        target=STATUS_REJECTED,
        conditions=[can_reject],
        # permission=lambda instance, user: user in instance.all_permitted,
        custom=dict(
            verbose="Reject as not trustworthy",
            explanation=("This record is confirmed wrong and not usable."),
            notify=True,
            url_path="reject/",
            badge="badge-danger",
        ),
    )
    def reject(self, by=None, description=None):
        """Confirm that a record is confirmed wrong and not usable.
        """
        return

    #def can_reset(self):
    #    """Return true if the record QA status can be reset."""
    #    return True

    # Rejected -> New
    #@fsm_log_by
    #@transition(
    #    field=status,
    #    source=STATUS_REJECTED,
    #    target=STATUS_NEW,
    #    conditions=[can_reset],
    #    # permission=lambda instance, user: user in instance.all_permitted,
    #    custom=dict(
    #        verbose="Reset QA status",
    #        explanation=("The QA status of this record needs to be reset."),
    #        notify=True,
    #        url_path="reset/",
    #    ),
    #)
    #def reset(self, by=None):
    #    """Reset the QA status of a record to NEW.

    #    This allows a record to be brought into the desired QA status.
    #    """
    #    return

    #def can_publish(self):
    #    """Return true if this document can be published."""
    #    return True

    # Curated -> Published
    #@fsm_log_by
    #@transition(
    #    field=status,
    #    source=STATUS_CURATED,
    #    target=STATUS_PUBLISHED,
    #    conditions=[can_publish],
    #    # permission=lambda instance, user: user in instance.all_permitted,
    #    custom=dict(
    #        verbose="Publish",
    #        explanation=("This record is fit for release."),
    #        notify=True,
    #        url_path="publish/",
    #    ),
    #)
    #def publish(self, by=None):
    #    """Mark encounter as ready to be published.

    #    Published data has been deemed fit for release by the data owner.
    #    """
    #    return

    #def can_embargo(self):
    #    """Return true if encounter can be embargoed."""
    #    return True

    # Published -> Curated
    #@fsm_log_by
    #@transition(
    #    field=status,
    #    source=STATUS_PUBLISHED,
    #    target=STATUS_CURATED,
    #    conditions=[can_embargo],
    #    # permission=lambda instance, user: user in instance.all_permitted,
    #    custom=dict(
    #        verbose="Embargo",
    #        explanation=("This record is not fit for release."),
    #        notify=True,
    #        url_path="embargo/",
    #    ),
    #)
    #def embargo(self, by=None):
    #    """Mark encounter as NOT ready to be published.

    #    Published data has been deemed fit for release by the data owner.
    #    Embargoed data is marked as curated, but not ready for release.
    #    """
    #    return

    # Override create and update until we have front end forms
    @classmethod
    def create_url(cls):
        """Create url. Default: app:model-create."""
        return reverse(
            "admin:{0}_{1}_add".format(cls._meta.app_label, cls._meta.model_name)
        )

    @property
    def update_url(self):
        """Update url. Redirects to admin update URL, as we don't have a front end form yet."""
        return self.absolute_admin_url

    @property
    def absolute_admin_url(self):
        """Return the absolute admin change URL."""
        return reverse(
            "admin:{0}_{1}_change".format(self._meta.app_label, self._meta.model_name),
            args=[
                self.pk,
            ],
        )

    def make_rest_listurl(self, format="json"):
        """Return the API list URL in given format (default: JSON).

        Permissible formats depend on configured renderers:
        api (human readable HTML), csv, json, jsonp, yaml, latex (PDF).
        """
        return rest_reverse(self._meta.model_name + "-list", kwargs={"format": format})

    def make_rest_detailurl(self, format="json"):
        """Return the API detail URL in given format (default: JSON).

        Permissible formats depend on configured renderers:
        api (human readable HTML), csv, json, jsonp, yaml, latex (PDF).
        """
        return rest_reverse(
            self._meta.model_name + "-detail", kwargs={"pk": self.pk, "format": format}
        )

    def get_curate_url(self):
        return reverse("observations:animalencounter-curate", kwargs={"pk": self.pk})

    def get_flag_url(self):
        return reverse("observations:animalencounter-flag", kwargs={"pk": self.pk})

    # -------------------------------------------------------------------------
    # Derived properties
    def can_change(self):
        # Returns True if editing this object is permitted, False otherwise.
        # Determined by the object's QA status.
        if self.status in [
            self.STATUS_NEW,
            self.STATUS_PROOFREAD,
            self.STATUS_FLAGGED,
            self.STATUS_REJECTED
        ]:
            return True
        return False

    def card_template(self):
        return "observations/encounter_card.html"

    @property
    def leaflet_title(self):
        """A string for Leaflet map marker titles. Cache me as field."""
        return "{} {} {}".format(
            self.when.astimezone(tz.tzlocal()).strftime("%d-%b-%Y %H:%M:%S") if self.when else "",
            self.get_encounter_type_display(),
            self.name or "",
        ).strip()

    @property
    def leaflet_icon(self):
        """Return the Fontawesome icon class for the encounter type."""
        return Encounter.LEAFLET_ICON[self.encounter_type]

    @property
    def leaflet_colour(self):
        """Return the Leaflet.awesome-markers colour for the encounter type."""
        return Encounter.LEAFLET_COLOUR[self.encounter_type]

    @property
    def tx_logs(self):
        """A list of dicts of QA timestamp, status and operator."""
        return [
            dict(
                timestamp=log.timestamp.isoformat(),
                status=log.state,
                operator=log.by.name if log.by else None,
            )
            for log in StateLog.objects.for_(self)
        ]

    def get_encounter_type(self):
        """Infer the encounter type.

        "Track" encounters have a TrackTallyObservation, those who don't have
        one but involve a TagObservation are tag management encounters (tag
        orders, distribution, returns, decommissioning).
        Lastly, the catch-all is "other" but complete records should not end up
        as such.
        """
        if self.observation_set.instance_of(TrackTallyObservation).exists():
            return self.ENCOUNTER_TRACKS
        elif self.observation_set.instance_of(TagObservation).exists():
            return self.ENCOUNTER_TAG
        else:
            return self.ENCOUNTER_OTHER

    @property
    def short_name(self):
        """A short, often unique, human-readable representation of the encounter.

        Slugified and dash-separated:

        * Date of encounter as YYYY-mm-dd
        * longitude in WGS 84 DD, rounded to 4 decimals (<10m),
        * latitude in WGS 84 DD, rounded to 4 decimals (<10m), (missing sign!!)
        * health,
        * maturity,
        * species.

        The short_name could be non-unique for encounters of multiple stranded
        animals of the same species and deadness.
        """
        return slugify.slugify(
            "-".join(
                [
                    self.when.astimezone(tz.tzlocal()).strftime("%Y-%m-%d %H:%M %Z"),
                    force_text(round(self.longitude, 4)).replace(".", "-"),
                    force_text(round(self.latitude, 4)).replace(".", "-"),
                ]
            )
        )

    @property
    def date(self):
        """Return the date component of Encounter.when."""
        return self.when.date()

    @property
    def date_string(self):
        """Return the date as string."""
        return str(self.when.date())

    @property
    def datetime(self):
        """Return the full datetime of the Encounter."""
        return self.when

    @property
    def season(self):
        """Return the season of the Encounter, the start year of the fiscal year.

        Calculated as the calendar year 180 days before the date of the Encounter.
        """
        return (self.when - relativedelta(months=6)).year

    # def save(self, *args, **kwargs):
    #     """Cache expensive properties.

    #     The popup content changes when fields change, and is expensive to build.
    #     As it is required ofen and under performance-critical circumstances -
    #     populating the home screen with lots of popups - is is re-calculated
    #     whenever the contents change (on save) rather when it is required for
    #     display.

    #     The source ID will be auto-generated from ``short_name`` (if not set)
    #     but is not guaranteed to be unique.
    #     The User will be prompted to provide a unique source ID if necessary,
    #     e.g. by appending a running number.
    #     The source ID can be re-created by deleting it and re-saving the object.

    #     The encounter type is inferred from the type of attached Observations.
    #     This logic is overridden in subclasses.

    #     The name is calculated from a complex lookup across associated TagObservations.
    #     """

    #     super(Encounter, self).save(*args, **kwargs)

    # Name -------------------------------------------------------------------#
    @property
    def guess_site(self):
        """Return the first Area containing the start_location or None."""
        candidates = Area.objects.filter(
            area_type=Area.AREATYPE_SITE, geom__covers=self.where
        )
        return None if not candidates else candidates.first()

    @property
    def guess_area(self):
        """Return the first Area containing the start_location or None."""
        candidates = Area.objects.filter(
            area_type=Area.AREATYPE_LOCALITY, geom__covers=self.where
        )
        return None if not candidates else candidates.first()

    def set_name(self, name):
        """Set the animal name to a given value."""
        self.name = name
        self.save()

    @property
    def inferred_name(self):
        """Return the inferred name from related new capture if existing.

        TODO replace with reconstruct_animal_names logic
        """
        return None
        # TODO less dirty
        try:
            return [enc.name for enc in self.related_encounters if enc.is_new_capture][0]
        except BaseException:
            return None

    def set_name_in_related_encounters(self, name):
        """Set the animal name in all related AnimalEncounters."""
        [a.set_name(name) for a in self.related_encounters]

    def set_name_and_propagate(self, name):
        """Set the animal name in this and all related Encounters."""
        # self.set_name(name)  # already contained in next line
        self.set_name_in_related_encounters(name)

    @property
    def related_encounters(self):
        """Return all Encounters with the same Animal.

        This algorithm collects all Encounters with the same animal by
        traversing an Encounter's TagObservations and their encounter histories.

        The algorithm starts with the Encounter (``self``) as initial
        known Encounter (``known_enc``), and ``self.tags`` as both initial known
        (``known_tags``) and new TagObs (``new_tags``).
        While there are new TagObs, a "while" loop harvests new encounters:

        * For each tag in ``new_tags``, retrieve the encounter history.
        * Combine and deduplicate the encounter histories
        * Remove known encounters and call this set of encounters ``new_enc``.
        * Add ``new_enc`` to ``known_enc``.
        * Combine and deduplicate all tags of all encounters in ``new_enc`` and
          call this set of TabObservations ``new_tags``.
        * Add ``new_tags`` to ``known_tags``.
        * Repeat the loop if the list of new tags is not empty.

        Finally, deduplicate and return ``known_enc``. These are all encounters
        that concern the same animal as this (self) encounter, as proven through
        the shared presence of TagObservations.
        """
        known_enc = [
            self,
        ]
        known_tags = list(self.tags)
        new_enc = []
        new_tags = self.tags
        show_must_go_on = True

        while show_must_go_on:
            new_enc = TagObservation.encounter_histories(new_tags, without=known_enc)
            known_enc.extend(new_enc)
            new_tags = Encounter.tag_lists(new_enc)
            known_tags += new_tags
            show_must_go_on = len(new_tags) > 0

        return list(set(known_enc))

    @property
    def tags(self):
        """Return a queryset of TagObservations."""
        return self.observation_set.instance_of(TagObservation)

    @property
    def flipper_tags(self):
        """Return a queryset of Flipper and PIT Tag Observations."""
        return self.observation_set.instance_of(TagObservation).filter(
            tagobservation__tag_type__in=["flipper-tag", "pit-tag"]
        )

    @property
    def primary_flipper_tag(self):
        """Return the TagObservation of the primary (by location in animal) flipper or PIT tag."""
        return self.flipper_tags.order_by("tagobservation__tag_location").first()

    @classmethod
    def tag_lists(cls, encounter_list):
        """Return the related tags of list of encounters.

        TODO double-check performance
        """
        return list(
            set(itertools.chain.from_iterable([e.tags for e in encounter_list]))
        )

    @property
    def is_new_capture(self):
        """Return whether the Encounter is a new capture (hint: never).

        Encounters can involve tags, but are never new captures.
        AnimalEncounters override this property, as they can be new captures.
        """
        return False

    # HTML popup -------------------------------------------------------------#
    @property
    def wkt(self):
        """Return the point coordinates as Well Known Text (WKT)."""
        return self.where.wkt

    def get_popup(self):
        """Generate HTML popup content."""
        t = loader.get_template("popup/{}.html".format(self._meta.model_name))
        return mark_safe(t.render({"original": self}))

    def get_report(self):
        """Generate an HTML report of the Encounter."""
        t = loader.get_template("reports/{}.html".format(self._meta.model_name))
        return mark_safe(t.render({"original": self}))

    @property
    def observation_set(self):
        """Manually implement the backwards relation to the Observation model."""
        return Observation.objects.filter(encounter=self)

    @property
    def latitude(self):
        """Return the WGS 84 DD latitude."""
        return self.where.y

    @property
    def longitude(self):
        """Return the WGS 84 DD longitude."""
        return self.where.x

    @property
    def crs(self):
        """Return the location CRS."""
        return self.where.srs.name

    @property
    def status_label(self):
        """Return the boostrap tag-* CSS label flavour for the QA status."""
        return QualityControlMixin.STATUS_LABELS[self.status]

    @property
    def photographs(self):
        """Return the URLs of all attached photograph or none."""
        try:
            return list(
                self.observation_set.instance_of(MediaAttachment)
            )
        except BaseException:
            return None


class AnimalEncounter(Encounter):
    """The encounter of an animal of a species.

    Extends the base Encounter class with:

    * taxonomic group (choices), can be used to filter remaining form choices
    * species (choices)
    * sex (choices)
    * maturity (choices)
    * health (choices)
    * activity (choices)
    * behaviour (free text)
    * habitat (choices)

    Turtle Strandings are encounters of turtles
    """

    taxon = models.CharField(
        max_length=300,
        verbose_name=_("Taxonomic group"),
        choices=lookups.TAXON_CHOICES,
        default=lookups.TAXON_CHOICES_DEFAULT,
        help_text=_("The taxonomic group of the animal."),
    )

    species = models.CharField(
        max_length=300,
        verbose_name=_("Species"),
        choices=lookups.SPECIES_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("The species of the animal."),
    )

    sex = models.CharField(
        max_length=300,
        verbose_name=_("Sex"),
        choices=lookups.SEX_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("The animal's sex."),
    )

    maturity = models.CharField(
        max_length=300,
        verbose_name=_("Maturity"),
        choices=lookups.MATURITY_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("The animal's maturity."),
    )

    health = models.CharField(
        max_length=300,
        verbose_name=_("Health status"),
        choices=lookups.HEALTH_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("The animal's physical health"),
    )

    activity = models.CharField(
        max_length=300,
        verbose_name=_("Activity"),
        choices=lookups.ACTIVITY_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("The animal's activity at the time of observation."),
    )

    behaviour = models.TextField(
        verbose_name=_("Condition and behaviour"),
        blank=True,
        null=True,
        help_text=_("Notes on condition or behaviour."),
    )

    habitat = models.CharField(
        max_length=500,
        verbose_name=_("Habitat"),
        choices=lookups.HABITAT_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("The habitat in which the animal was encountered."),
    )

    sighting_status = models.CharField(
        max_length=300,
        verbose_name=_("Sighting status"),
        choices=lookups.SIGHTING_STATUS_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_(
            "The status is inferred automatically based on whether"
            " and where this animal was processed and identified last."
        ),
    )

    sighting_status_reason = models.CharField(
        max_length=1000,
        verbose_name=_("Sighting status reason"),
        blank=True,
        null=True,
        help_text=_("The rationale for the inferred sighting status."),
    )

    identifiers = models.TextField(
        verbose_name=_("Identifiers"),
        blank=True,
        null=True,
        help_text=_(
            "A space-separated list of all identifers ever recorded "
            "as associated with this animal. This list includes identifiers "
            "recorded only in earlier or later encounters."
        ),
    )

    datetime_of_last_sighting = models.DateTimeField(
        verbose_name=_("Last seen on"),
        blank=True,
        null=True,
        help_text=_(
            "The observation datetime of this animal's last sighting, "
            "shown as local time (no daylight savings), stored as UTC. "
            "Blank if the animal has never been seen before."
        ),
    )

    site_of_last_sighting = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="encounter_last_sighting",
        verbose_name=_("Last seen at"),
        help_text=_("The Site in which the animal was encountered last."),
    )

    site_of_first_sighting = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="encounter_first_sighting",
        verbose_name=_("First seen at"),
        help_text=_("The Site in which the animal was encountered first."),
    )

    # ODK form Turtle Tagging > nest_observed_nesting_success
    nesting_event = models.CharField(  # TODO rename to nesting_success
        max_length=300,
        verbose_name=_("Nesting success"),
        choices=lookups.NESTING_SUCCESS_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("What indication of nesting success was observed?"),
    )

    # Populated from Turtle Tagging > nest_nesting_disturbed
    # Behaviour:      Turtle Tagging > nesting_disturbance_cause
    nesting_disturbed = models.CharField(
        max_length=300,
        verbose_name=_("Nesting disturbed"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_(
            "Was the nesting interrupted? " "If so, specify disturbance in comments."
        ),
    )

    laparoscopy = models.BooleanField(
        max_length=300,
        verbose_name=_("Laparoscopy conducted"),
        default=False,
        help_text=_(
            "Was the animal's sex and maturity determined through " "laparoscopy?"
        ),
    )

    checked_for_injuries = models.CharField(
        max_length=300,
        verbose_name=_("Checked for injuries"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Was the animal checked for injuries, were any found?"),
    )

    scanned_for_pit_tags = models.CharField(
        max_length=300,
        verbose_name=_("Scanned for PIT tags"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Was the animal scanned for PIT tags, were any found?"),
    )

    checked_for_flipper_tags = models.CharField(
        max_length=300,
        verbose_name=_("Checked for flipper tags"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Was the animal checked for flipper tags, were any found?"),
    )

    cause_of_death = models.CharField(
        max_length=300,
        verbose_name=_("Cause of death"),
        choices=lookups.CAUSE_OF_DEATH_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("If dead, is the case of death known?"),
    )

    cause_of_death_confidence = models.CharField(
        max_length=300,
        verbose_name=_("Cause of death confidence"),
        choices=lookups.CONFIDENCE_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("What is the cause of death, if known, based on?"),
    )

    class Meta:
        verbose_name = "Animal Encounter"
        verbose_name_plural = "Animal Encounters"
        get_latest_by = "when"
        # base_manager_name = 'base_objects'  # fix delete bug

    def __str__(self):
        tpl = "AnimalEncounter {0} on {1} by {2} of {3}, {4} {5} {6} on {7}"
        return tpl.format(
            self.pk,
            self.when.astimezone(tz.tzlocal()).strftime("%Y-%m-%d %H:%M %Z"),
            self.observer.name,
            self.get_species_display(),
            self.get_health_display(),
            self.get_maturity_display(),
            self.get_sex_display(),
            self.get_habitat_display(),
        )

    def get_encounter_type(self):
        """Infer the encounter type.

        AnimalEncounters are either in water, tagging or stranding encounters.
        If the animal is dead (at various decompositional stages), a stranding
        is assumed.
        In water captures happen if the habitat is in the list of aquatic
        habitats.
        Remaining encounters are assumed to be taggings, as other encounters are
        excluded. Note that an animal encountered in water, or even a dead
        animal (whether that makes sense or not) can also be tagged.
        """
        if self.nesting_event in lookups.NESTING_PRESENT:
            return Encounter.ENCOUNTER_TAGGING
        elif self.health in lookups.DEATH_STAGES:
            return Encounter.ENCOUNTER_STRANDING
        elif self.habitat in lookups.HABITAT_WATER:
            # this will ignore inwater encounters without habitat
            return Encounter.ENCOUNTER_INWATER
        else:
            # not stranding or in water = fallback to tagging
            return Encounter.ENCOUNTER_TAGGING

    @property
    def short_name(self):
        """A short, often unique, human-readable representation of the encounter.

        Slugified and dash-separated:

        * Date of encounter as YYYY-mm-dd
        * longitude in WGS 84 DD, rounded to 4 decimals (<10m),
        * latitude in WGS 84 DD, rounded to 4 decimals (<10m), (missing sign!!)
        * health,
        * maturity,
        * species,
        * name if available (requires "update names" and tag obs)

        The short_name could be non-unique for encounters of multiple stranded
        animals of the same species and deadness.
        """
        nameparts = [
            self.when.astimezone(tz.tzlocal()).strftime("%Y-%m-%d %H:%M %Z"),
            force_text(round(self.longitude, 4)).replace(".", "-"),
            force_text(round(self.latitude, 4)).replace(".", "-"),
            self.health,
            self.maturity,
            self.sex,
            self.species,
        ]
        if self.name is not None:
            nameparts.append(self.name)
        return slugify.slugify("-".join(nameparts))

    @property
    def latitude(self):
        """Return the WGS 84 DD latitude."""
        return self.where.y

    @property
    def longitude(self):
        """Return the WGS 84 DD longitude."""
        return self.where.x

    @property
    def is_stranding(self):
        """Return whether the Encounters is stranding or tagging.

        If the animal is not "alive", it's a stranding encounter, else it's a
        tagging encounter.
        """
        return self.health != "alive"

    @property
    def is_new_capture(self):
        """Return whether this Encounter is a new capture.

        New captures are named after their primary flipper tag.
        An Encounter is a new capture if there are:

        * no associated TagObservations of ``is_recapture`` status
        * at least one associated TabObservation of ``is_new`` status
        """
        new_tagobs = set([x for x in self.flipper_tags if x.is_new])
        old_tagobs = set([x for x in self.flipper_tags if x.is_recapture])
        has_new_tagobs = len(new_tagobs) > 0
        has_old_tagobs = len(old_tagobs) > 0
        return has_new_tagobs and not has_old_tagobs

    def get_absolute_url(self):
        return reverse("observations:animalencounter-detail", kwargs={"pk": self.pk})

    def card_template(self):
        return "observations/animalencounter_card.html"


class TurtleNestEncounter(Encounter):
    """The encounter of turtle nest during its life cycle.
    May represent a track with no nest, and track & nest, or a nest with no track.

    The observations are assumed to follow DBCA protocol.
    TurtleNestEncouters by third parties can be recorded, but related
    observations cannot if they don't follow DBCA protocol.

    Stages:

    * false crawl (aborted nesting attempt)
    * new (turtle is present, observed during nesting/tagging)
    * fresh (morning after, observed during track count)
    * predated (nest and eggs destroyed by predator)
    * hatched (eggs hatched)
    """

    nest_age = models.CharField(
        max_length=300,
        verbose_name=_("Age"),
        choices=lookups.NEST_AGE_CHOICES,
        default=lookups.NEST_AGE_DEFAULT,
        help_text=_("The track or nest age."),
    )

    nest_type = models.CharField(
        max_length=300,
        verbose_name=_("Type"),
        choices=lookups.NEST_TYPE_CHOICES,
        default=lookups.NEST_TYPE_DEFAULT,
        help_text=_("The track or nest type."),
    )

    species = models.CharField(
        max_length=300,
        verbose_name=_("Species"),
        choices=lookups.TURTLE_SPECIES_CHOICES,
        default=lookups.TURTLE_SPECIES_DEFAULT,
        help_text=_("The species of the animal which created the track or nest."),
    )

    habitat = models.CharField(
        max_length=500,
        verbose_name=_("Habitat"),
        choices=lookups.BEACH_POSITION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("The habitat in which the track or nest was encountered."),
    )

    disturbance = models.CharField(
        max_length=300,
        verbose_name=_("Evidence of predation or disturbance"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Is there evidence of predation or other disturbance?"),
    )

    nest_tagged = models.CharField(
        max_length=300,
        verbose_name=_("Nest tag present"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Was a nest tag applied, re-sighted, or otherwise encountered?"),
    )

    logger_found = models.CharField(
        max_length=300,
        verbose_name=_("Logger present"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Was a data logger deployed, retrieved, or otherwise encountered?"),
    )

    eggs_counted = models.CharField(
        max_length=300,
        verbose_name=_("Nest excavated and eggs counted"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Was the nest excavated and were turtle eggs counted?"),
    )

    hatchlings_measured = models.CharField(
        max_length=300,
        verbose_name=_("Hatchlings measured"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_(
            "Were turtle hatchlings encountered and their morphometrics measured?"
        ),
    )

    fan_angles_measured = models.CharField(
        max_length=300,
        verbose_name=_("Hatchling emergence recorded"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Were hatchling emergence track fan angles recorded?"),
    )

    class Meta:
        verbose_name = "Turtle Nest Encounter"
        verbose_name_plural = "Turtle Nest Encounters"
        get_latest_by = "when"

    def __str__(self):
        return f"{self.pk}: {self.get_nest_type_display()}, {self.get_nest_age_display()}, {self.get_species_display()}"

    def get_encounter_type(self):
        if self.nest_type in ["successful-crawl", "nest", "hatched-nest"]:
            return Encounter.ENCOUNTER_NEST
        else:
            return Encounter.ENCOUNTER_TRACKS

    @property
    def short_name(self):
        """A short, often unique, human-readable representation of the encounter.

        Slugified and dash-separated:

        * Date of encounter as YYYY-mm-dd
        * longitude in WGS 84 DD, rounded to 4 decimals (<10m),
        * latitude in WGS 84 DD, rounded to 4 decimals (<10m), (missing sign!!)
        * nest age (type),
        * species,
        * name if available (requires "update names" and tag obs)

        The short_name could be non-unique.
        """
        nameparts = [
            self.when.astimezone(tz.tzlocal()).strftime("%Y-%m-%d %H:%M %Z"),
            force_text(round(self.longitude, 4)).replace(".", "-"),
            force_text(round(self.latitude, 4)).replace(".", "-"),
            self.nest_age,
            self.species,
        ]
        if self.name is not None:
            nameparts.append(self.name)
        return slugify.slugify("-".join(nameparts))

    @property
    def latitude(self):
        """Return the WGS 84 DD latitude."""
        return self.where.y

    @property
    def longitude(self):
        """Return the WGS 84 DD longitude."""
        return self.where.x

    @property
    def inferred_name(self):
        """Return the first NestTag name or None."""
        nest_tag = self.observation_set.instance_of(NestTagObservation).first()
        if nest_tag:
            return nest_tag.name
        else:
            return None

    def get_absolute_url(self):
        return reverse(
            "observations:turtlenestencounter-detail", kwargs={"pk": self.pk}
        )

    def get_curate_url(self):
        return reverse("observations:turtlenestencounter-curate", kwargs={"pk": self.pk})

    def get_flag_url(self):
        return reverse("observations:turtlenestencounter-flag", kwargs={"pk": self.pk})

    def card_template(self):
        return "observations/turtlenestencounter_card.html"

    def get_nest_observation(self):
        """A turtle nest encounter should be associated with 0-1 nest observation objects.
        Returns the related turtle nest observation or None.
        """
        if self.observation_set.instance_of(TurtleNestObservation).exists():
            return self.observation_set.instance_of(TurtleNestObservation).first()
        else:
            return None

    def get_nesttag_observation(self):
        """A turtle nest encounter should be associated with 0-1 NestTagObservation objects.
        Returns the related NestTagObservation or None.
        """
        if self.observation_set.instance_of(NestTagObservation).exists():
            return self.observation_set.instance_of(NestTagObservation).first()
        else:
            return None

    def get_logger_observation(self):
        """A turtle nest encounter should be associated with 0-1 LoggerObservation objects.
        Returns the related LoggerObservation or None.
        """
        if self.observation_set.instance_of(LoggerObservation).exists():
            return self.observation_set.instance_of(LoggerObservation).first()
        else:
            return None


class LineTransectEncounter(Encounter):
    """Encounter with a line transect.

    An observer tallies (not individually georeferenced) observations along
    a line transect, while recording the transect route live and keeping the
    tally until the end of the transect.

    Although individually geo-referenced Encounters are preferable, this Encounter
    type supports tallies of abundant entities (like turtle tracks on a saturation
    beach), collected under time pressure.

    Examples:

    ODK form "Track Tally", providing per record:
    * One LineTransectEncounter with zero to many related:
    * TrackTallyObservation
    * TurtleNestDisturbanceTallyObservation
    """

    transect = geo_models.LineStringField(
        srid=4326,
        dim=2,
        verbose_name=_("Transect line"),
        help_text=_("The line transect as LineString in WGS84"),
    )

    class Meta:
        verbose_name = "Line Transect Encounter"
        verbose_name_plural = "Line Transect Encounters"
        get_latest_by = "when"

    def __str__(self):
        return "Line tx {0}".format(self.pk)

    def inferred_name(self):
        """Return an empty string."""
        return ""

    def get_encounter_type(self):
        """Infer the encounter type.

        If TrackTallyObservations are related, it's a track observation.

        TODO support other types of line transects when added
        """
        return Encounter.ENCOUNTER_TRACKS

    @property
    def short_name(self):
        """A short, often unique, human-readable representation of the encounter.

        Slugified and dash-separated:

        * Date of encounter as YYYY-mm-dd
        * longitude in WGS 84 DD, rounded to 4 decimals (<10m),
        * latitude in WGS 84 DD, rounded to 4 decimals (<10m), (missing sign!!)
        * nest age (type),
        * species,
        * name if available (requires "update names" and tag obs)

        The short_name could be non-unique.
        """
        nameparts = [
            self.when.astimezone(tz.tzlocal()).strftime("%Y-%m-%d %H:%M %Z"),
            force_text(round(self.longitude, 4)).replace(".", "-"),
            force_text(round(self.latitude, 4)).replace(".", "-"),
        ]
        if self.name is not None:
            nameparts.append(self.name)
        return slugify.slugify("-".join(nameparts))

    @property
    def latitude(self):
        """Return the WGS 84 DD latitude."""
        return self.where.y

    @property
    def longitude(self):
        """Return the WGS 84 DD longitude."""
        return self.where.x

    def card_template(self):
        return "observations/linetransectencounter_card.html"


class LoggerEncounter(Encounter):
    """The encounter of an electronic logger during its life cycle.

    Stages:

    * programmed (in office)
    * posted to field team (in mail)
    * deployed (in situ)
    * resighted (in situ)
    * retrieved (in situ)
    * downloaded (in office)

    The life cycle can be repeated. The logger can be downloaded, reprogrammed
    and deployed again in situ.

    This model is deprecated and LoggerEncounters will become
    Encounters with LoggerObservations.
    """

    LOGGER_TYPE_DEFAULT = "temperature-logger"
    LOGGER_TYPE_CHOICES = (
        (LOGGER_TYPE_DEFAULT, "Temperature Logger"),
        ("data-logger", "Data Logger"),
        ("ctd-data-logger", "Conductivity, Temperature, Depth SR data logger"),
    )

    LOGGER_STATUS_DEFAULT = "resighted"
    LOGGER_STATUS_NEW = "programmed"
    LOGGER_STATUS_CHOICES = (
        (LOGGER_STATUS_NEW, "programmed"),
        ("posted", "posted to field team"),
        ("deployed", "deployed in situ"),
        ("resighted", "resighted in situ"),
        ("retrieved", "retrieved in situ"),
        ("downloaded", "downloaded"),
    )

    logger_type = models.CharField(
        max_length=300,
        default=LOGGER_TYPE_DEFAULT,
        verbose_name=_("Type"),
        choices=LOGGER_TYPE_CHOICES,
        help_text=_("The logger type."),
    )

    deployment_status = models.CharField(
        max_length=300,
        default=LOGGER_STATUS_DEFAULT,
        verbose_name=_("Status"),
        choices=LOGGER_STATUS_CHOICES,
        help_text=_("The logger life cycle status."),
    )

    logger_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Logger ID"),
        help_text=_("The ID of a logger must be unique within the tag type."),
    )

    class Meta:
        verbose_name = "Logger Encounter"
        verbose_name_plural = "Logger Encounters"
        get_latest_by = "when"

    def __str__(self):
        return "{0} {1} {2}".format(
            self.get_logger_type_display(),
            self.name or "",
            self.get_deployment_status_display(),
        )

    def get_encounter_type(self):
        """Infer the encounter type.

        LoggerEncounters are always logger encounters. Would you have guessed?
        """
        return Encounter.ENCOUNTER_LOGGER

    @property
    def short_name(self):
        """A short, often unique, human-readable representation of the encounter.

        Slugified and dash-separated:

        * logger type
        * deployment status
        * logger id

        The short_name could be non-unique for very similar encounters.
        In this case, a modifier can be added by the user to ensure uniqueness.
        """
        nameparts = [self.logger_type, self.deployment_status, self.logger_id]
        if self.name is not None:
            nameparts.append(self.name)
        return slugify.slugify("-".join(nameparts))

    @property
    def inferred_name(self):
        """Set the encounter name from logger ID."""
        return self.logger_id

    @property
    def latitude(self):
        """Return the WGS 84 DD latitude."""
        return self.where.y

    @property
    def longitude(self):
        """Return the WGS 84 DD longitude."""
        return self.where.x

    def card_template(self):
        return "observations/loggerencounter_card.html"


class Observation(PolymorphicModel, LegacySourceMixin, models.Model):
    """The Observation base class for encounter observations.

    Everything happens somewhere, at a time, to someone, and someone records it.
    Therefore, an Observation must happen during an Encounter.
    """

    encounter = models.ForeignKey(
        Encounter,
        on_delete=models.CASCADE,
        verbose_name=_("Encounter"),
        related_name="observations",
        help_text=("The Encounter during which the observation was made"),
    )

    def __str__(self):
        return f"Obs {self.pk} for {self.encounter}"

    @property
    def point(self):
        """Return the encounter location."""
        return self.encounter.where

    @property
    def as_html(self):
        """An HTML representation."""
        t = loader.get_template("popup/{}.html".format(self._meta.model_name))
        return mark_safe(t.render({"original": self}))

    @property
    def as_latex(self):
        """A Latex representation."""
        t = loader.get_template("latex/{}.tex".format(self._meta.model_name))
        return mark_safe(t.render({"original": self}))

    @property
    def observation_name(self):
        """The concrete model name.

        This method will inherit down the polymorphic chain, and always return
        the actual child model's name.

        `observation_name` can be included as field e.g. in API serializers,
        so e.g. a writeable serializer would know which child model to `create`
        or `update`.
        """
        return self.polymorphic_ctype.model

    @property
    def latitude(self):
        """The encounter's latitude."""
        return self.encounter.where.y or ""

    @property
    def longitude(self):
        """The encounter's longitude."""
        return self.encounter.where.x or ""

    def datetime(self):
        """The encounter's timestamp."""
        return self.encounter.when or ""

    @property
    def absolute_admin_url(self):
        """Return the absolute admin change URL.
        """
        return reverse(
            "admin:{0}_{1}_change".format(self._meta.app_label, self._meta.model_name),
            args=[
                self.pk,
            ],
        )


class MediaAttachment(Observation):
    """A media attachment to an Encounter."""

    MEDIA_TYPE_CHOICES = (
        ("data_sheet", _("Data sheet")),
        ("communication", _("Communication record")),
        ("photograph", _("Photograph")),
        ("other", _("Other")),
    )

    media_type = models.CharField(
        max_length=300,
        verbose_name=_("Attachment type"),
        choices=MEDIA_TYPE_CHOICES,
        default="photograph",
        help_text=_("What is the attached file about?"),
    )

    title = models.CharField(
        max_length=300,
        verbose_name=_("Attachment name"),
        blank=True,
        null=True,
        help_text=_("Give the attachment a representative name"),
    )

    attachment = models.FileField(
        upload_to=encounter_media,
        max_length=500,
        verbose_name=_("File attachment"),
        help_text=_("Upload the file"),
    )

    class Meta:
        verbose_name = "Media Attachment"

    def __str__(self):
        return "Media {0} for {1}".format(self.pk, self.encounter.__str__())

    @property
    def filepath(self):
        """The path to attached file."""
        try:
            fpath = force_text(self.attachment.file)
        except BaseException:
            fpath = None
        return fpath

    @property
    def thumbnail(self):
        if self.attachment:
            return mark_safe(
                '<a href="{0}" target="_" rel="nofollow" '
                'title="Click to view full screen in new browser tab">'
                '<img src="{0}" alt="{1} {2}" style="height:100px;"></img>'
                "</a>".format(
                    self.attachment.url, self.get_media_type_display(), self.title
                )
            )
        else:
            return ""


class TagObservation(Observation):
    """An Observation of an identifying tag on an observed entity.

    The identifying tag can be a flipper tag on a turtle, a PIT tag,
    a satellite tag, a barcode on a sample taken off an animal, a whisker ID
    from a picture of a pinniped, a genetic fingerprint or similar.

    The tag has its own life cycle through stages of production, delivery,
    affiliation with an animal, repeated sightings and disposal.

    The life cycle stages will vary between tag types.

    A TagObservation will find the tag in exactly one of the life cycle stages.

    The life history of each tag can be reconstructed from the sum of all of its
    TagObservations.

    As TagObservations can sometimes occur without an Observation of an animal,
    the FK to Observations is optional.

    Flipper Tag Status as per WAMTRAM:

    * # = tag attached new, number NA, need to double-check number
    * P, p: re-sighted as attached to animal, no actions taken or necessary
    * do not use: 0L, A2, M, M1, N
    * AE = A1
    * P_ED = near flipper edge, might fall off soon
    * PX = tag re-sighted, but operator could not read tag ID
      (e.g. turtle running off)
    * RQ = tag re-sighted, tag was "insecure", but no action was recorded

    Recaptured tags: Need to record state (open, closed, tip locked or not)
    as feedback to taggers to improve their tagging technique.

    PIT tag status:

    * applied and did read OK
    * applied and did not read (but still inside and might read later on)

    Sample status:

    * taken off animal
    * handed to lab
    * done science to it
    * handed in report

    Animal Name:
    All TagObservations of one animal are linked by shared encounters or
    shared tag names. The earliest associated flipper tag name is used as the
    animal's name, and transferred onto all related TagObservations.
    """

    tag_type = models.CharField(
        max_length=300,
        verbose_name=_("Tag type"),
        choices=lookups.TAG_TYPE_CHOICES,
        default="flipper-tag",
        help_text=_("What kind of tag is it?"),
    )

    tag_location = models.CharField(
        max_length=300,
        verbose_name=_("Tag position"),
        choices=lookups.TURTLE_BODY_PART_CHOICES,
        default=lookups.BODY_PART_DEFAULT,
        help_text=_("Where is the tag attached, or the sample taken from?"),
    )

    # tag_fix TODO

    name = models.CharField(
        max_length=1000,
        verbose_name=_("Tag ID"),
        help_text=_("The ID of a tag must be unique within the tag type."),
    )

    status = models.CharField(
        max_length=300,
        verbose_name=_("Tag status"),
        choices=lookups.TAG_STATUS_CHOICES,
        default=lookups.TAG_STATUS_DEFAULT,
        help_text=_("The status this tag was after the encounter."),
    )

    handler = models.ForeignKey(
        User,
        on_delete=models.SET_DEFAULT,
        default=settings.ADMIN_USER,
        blank=True,
        null=True,
        verbose_name=_("Handled by"),
        related_name="tag_handler",
        help_text=_("The person in physical contact with the tag or sample"),
    )

    recorder = models.ForeignKey(
        User,
        on_delete=models.SET_DEFAULT,
        default=settings.ADMIN_USER,
        blank=True,
        null=True,
        verbose_name=_("Recorded by"),
        related_name="tag_recorder",
        help_text=_("The person who records the tag observation"),
    )

    comments = models.TextField(
        verbose_name=_("Comments"),
        blank=True,
        null=True,
        help_text=_("Any other comments or notes."),
    )

    class Meta:
        verbose_name = "Turtle Tag Observation"

    def __str__(self):
        return "{0} {1} {2} on {3}".format(
            self.get_tag_type_display(),
            self.name,
            self.get_status_display(),
            self.get_tag_location_display(),
        )

    @classmethod
    def encounter_history(cls, tagname):
        """Return the related encounters of all TagObservations of a given tag name."""
        return list(set([t.encounter for t in cls.objects.filter(name=tagname)]))

    @classmethod
    def encounter_histories(cls, tagname_list, without=[]):
        """Return the related encounters of all tag names.

        TODO double-check performance
        """
        return [
            encounter
            for encounter in list(
                set(
                    itertools.chain.from_iterable(
                        [TagObservation.encounter_history(t.name) for t in tagname_list]
                    )
                )
            )
            if encounter not in without
        ]

    @property
    def is_new(self):
        """Return wheter the TagObservation is the first association with the animal."""
        return self.status == lookups.TAG_STATUS_APPLIED_NEW

    @property
    def is_recapture(self):
        """Return whether the TabObservation is a recapture."""
        return self.status in lookups.TAG_STATUS_RESIGHTED

    @property
    def history_url(self):
        """The list view of all observations of this tag."""
        cl = reverse("admin:observations_tagobservation_changelist")
        return "{0}?q={1}".format(cl, urllib.parse.quote_plus(self.name))


class NestTagObservation(Observation):
    """Turtle Nest Tag Observation.

    TNTs consist of three components, which are all optional:

    * flipper_tag_id: The primary flipper tag ID of the nesting turtle
    * date_nest_laid: The calendar (not turtle) date of nest creation
    * tag_label: Any extra nest label if other two components not available

    Naming scheme:

    * Uppercase and remove whitespace from flipper tag ID
    * date nest laid: YYYY-mm-dd
    * Uppercase and remove whitespace from tag label
    * Join all with "_"

    E.g.: WA1234_2017-12-31_M1
    """

    status = models.CharField(
        max_length=300,
        verbose_name=_("Tag status"),
        choices=lookups.NEST_TAG_STATUS_CHOICES,
        default=lookups.TAG_STATUS_DEFAULT,
        help_text=_("The status this tag was seen in, or brought into."),
    )

    flipper_tag_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Flipper Tag ID"),
        help_text=_(
            "The primary flipper tag ID of the nesting turtle " "if available."
        ),
    )

    date_nest_laid = models.DateField(
        verbose_name=_("Date nest laid"),
        blank=True,
        null=True,
        help_text=_("The calendar (not turtle) date of nest creation."),
    )

    tag_label = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Tag Label"),
        help_text=_(
            "Any extra nest label if other two components are not " "available."
        ),
    )

    comments = models.TextField(
        verbose_name=_("Comments"),
        blank=True,
        null=True,
        help_text=_("Any other comments or notes."),
    )

    class Meta:
        verbose_name = "Turtle Nest Tag Observation"

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def history_url(self):
        """The list view of all observations of this tag."""
        cl = reverse("admin:observations_nesttagobservation_changelist")
        if self.flipper_tag_id:
            return "{0}?q={1}".format(cl, urllib.parse.quote_plus(self.flipper_tag_id))
        else:
            return cl

    @property
    def name(self):
        """Return the nest tag name according to the naming scheme."""
        return "_".join(
            [
                ("" if not self.flipper_tag_id else self.flipper_tag_id)
                .upper()
                .replace(" ", ""),
                "" if not self.date_nest_laid else str(self.date_nest_laid),
                "" if not self.tag_label else self.tag_label.upper().replace(" ", ""),
            ]
        )


class ManagementAction(Observation):
    """
    Management actions following an AnimalEncounter.

    E.g, disposal, rehab, euthanasia.
    """

    management_actions = models.TextField(
        verbose_name=_("Management Actions"),
        blank=True,
        null=True,
        help_text=_("Managment actions taken. Keep updating as appropriate."),
    )

    comments = models.TextField(
        verbose_name=_("Comments"),
        blank=True,
        null=True,
        help_text=_("Any other comments or notes."),
    )

    class Meta:
        verbose_name = "Management Action"

    def __str__(self):
        return "Management Action {0} of {1}".format(self.pk, self.encounter.__str__())


class TurtleMorphometricObservation(Observation):
    """Morphometric measurements of a turtle."""

    curved_carapace_length_mm = models.PositiveIntegerField(
        verbose_name=_("Curved carapace length max (mm)"),
        blank=True,
        null=True,
        help_text=_("The curved carapace length (max) in millimetres."),
    )

    curved_carapace_length_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Curved carapace length (max) accuracy"),
        help_text=_("The expected measurement accuracy."),
    )

    curved_carapace_length_min_mm = models.PositiveIntegerField(
        verbose_name=_("Curved carapace length min (mm)"),
        blank=True,
        null=True,
        help_text=_("The curved carapace length (min) in millimetres."),
    )

    curved_carapace_length_min_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Curved carapace length accuracy"),
        help_text=_("The expected measurement accuracy."),
    )

    straight_carapace_length_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Straight carapace length (mm)"),
        help_text=_("The straight carapace length in millimetres."),
    )

    straight_carapace_length_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Straight carapace length accuracy"),
        help_text=_("The expected measurement accuracy."),
    )

    curved_carapace_width_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Curved carapace width (mm)"),
        help_text=_("Curved carapace width in millimetres."),
    )

    curved_carapace_width_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Curved carapace width (mm)"),
        help_text=_("The expected measurement accuracy."),
    )

    tail_length_carapace_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Tail length from carapace (mm)"),
        help_text=_(
            "The tail length in millimetres, " "measured from carapace to tip."
        ),
    )

    tail_length_carapace_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Tail length from carapace accuracy"),
        help_text=_("The expected measurement accuracy."),
    )

    tail_length_vent_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Tail length from vent (mm)"),
        help_text=_("The tail length in millimetres, " "measured from vent to tip."),
    )

    tail_length_vent_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Tail Length Accuracy"),
        help_text=_("The expected measurement accuracy."),
    )

    tail_length_plastron_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Tail length from plastron (mm)"),
        help_text=_(
            "The tail length in millimetres, " "measured from plastron to tip."
        ),
    )

    tail_length_plastron_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Tail length from plastron accuracy"),
        help_text=_("The expected measurement accuracy."),
    )

    maximum_head_width_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Maximum head width (mm)"),
        help_text=_("The maximum head width in millimetres."),
    )

    maximum_head_width_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Maximum head width accuracy"),
        help_text=_("The expected measurement accuracy."),
    )

    maximum_head_length_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Maximum head length (mm)"),
        help_text=_("The maximum head length in millimetres."),
    )

    maximum_head_length_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Maximum head length accuracy"),
        help_text=_("The expected measurement accuracy."),
    )

    body_depth_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Body depth (mm)"),
        help_text=_("The body depth, plastron to carapace, in millimetres."),
    )

    body_depth_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Body depth accuracy"),
        help_text=_("The expected measurement accuracy."),
    )

    body_weight_g = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Body weight (g)"),
        help_text=_("The body weight in grams (1000 g = 1kg)."),
    )

    body_weight_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        choices=lookups.ACCURACY_CHOICES,
        verbose_name=_("Body weight accuracy"),
        help_text=_("The expected measurement accuracy."),
    )

    handler = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="morphometric_handler",
        verbose_name=_("Measured by"),
        help_text=_("The person conducting the measurements."),
    )

    recorder = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="morphometric_recorder",
        verbose_name=_("Recorded by"),
        help_text=_("The person recording the measurements."),
    )

    class Meta:
        verbose_name = "Turtle Morphometric Observation"

    def __str__(self):
        tpl = "Turtle Morphometrics {0} CCL {1} CCW {2} for Encounter {3}"
        return tpl.format(
            self.pk,
            self.curved_carapace_length_mm,
            self.curved_carapace_width_mm,
            self.encounter.pk,
        )


class HatchlingMorphometricObservation(Observation):
    """Morphometric measurements of a hatchling at a TurtleNestEncounter."""

    straight_carapace_length_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Straight carapace length (mm)"),
        help_text=_("The straight carapace length in millimetres."),
    )

    straight_carapace_width_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Straight carapace width (mm)"),
        help_text=_("The straight carapace width in millimetres."),
    )

    body_weight_g = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Body weight (g)"),
        help_text=_("The body weight in grams (1000 g = 1kg)."),
    )

    class Meta:
        verbose_name = "Turtle Hatchling Morphometric Observation"

    def __str__(self):
        tpl = "{0} Hatchling SCL {1} mm, SCW {2} mm, Wt {3} g"
        return tpl.format(
            self.pk,
            self.straight_carapace_length_mm,
            self.straight_carapace_width_mm,
            self.body_weight_g,
        )


class DugongMorphometricObservation(Observation):
    """Morphometric measurements of a Dugong at an AnimalEncounter."""

    body_length_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Body length (mm)"),
        help_text=_("The body length in millimetres."),
    )

    body_girth_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Body girth (mm)"),
        help_text=_("The body girth at the widest point in millimetres."),
    )

    tail_fluke_width_mm = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Tail fluke width (mm)"),
        help_text=_("The tail fluke width in millimetres."),
    )

    tusks_found = models.CharField(
        max_length=300,
        verbose_name=_("Tusks found"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Did the animal have tusks?"),
    )

    class Meta:
        verbose_name = "Dugong Morphometric Observation"

    def __str__(self):
        tpl = "{0} {1} Hatchling SCL {2} mm, SCW {3} mm, Wt {4} g"
        return tpl.format(
            self.pk,
            self.encounter.species,
            self.body_length_mm,
            self.body_girth_mm,
            self.tail_fluke_width_mm,
        )


class TurtleDamageObservation(Observation):
    """Observation of turtle damages or injuries."""

    body_part = models.CharField(
        max_length=300,
        default="whole-turtle",
        verbose_name=_("Affected body part"),
        choices=lookups.TURTLE_BODY_PART_CHOICES,
        help_text=_("The body part affected by the observed damage."),
    )

    damage_type = models.CharField(
        max_length=300,
        default="minor-trauma",
        verbose_name=_("Damage type"),
        choices=lookups.DAMAGE_TYPE_CHOICES,
        help_text=_("The type of the damage."),
    )

    damage_age = models.CharField(
        max_length=300,
        default="healed-entirely",
        verbose_name=_("Damage age"),
        choices=lookups.DAMAGE_AGE_CHOICES,
        help_text=_("The age of the damage."),
    )

    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
        null=True,
        help_text=_("A description of the damage."),
    )

    class Meta:
        verbose_name = "Turtle Damage Observation"

    def __str__(self):
        return "{0}: {1} {2}".format(
            self.get_body_part_display(),
            self.get_damage_age_display(),
            self.get_damage_type_display(),
        )


class TrackTallyObservation(Observation):
    """Observation of turtle track tallies and signs of predation."""

    species = models.CharField(
        max_length=300,
        verbose_name=_("Species"),
        choices=lookups.TURTLE_SPECIES_CHOICES,
        default=lookups.TURTLE_SPECIES_DEFAULT,
        help_text=_("The species of the animal causing the track."),
    )

    nest_age = models.CharField(
        max_length=300,
        verbose_name=_("Age"),
        choices=lookups.NEST_AGE_CHOICES,
        default=lookups.NEST_AGE_DEFAULT,
        help_text=_("The track or nest age."),
    )

    nest_type = models.CharField(
        max_length=300,
        verbose_name=_("Type"),
        choices=lookups.NEST_TYPE_CHOICES,
        default=lookups.NEST_TYPE_DEFAULT,
        help_text=_("The track or nest type."),
    )

    tally = models.PositiveIntegerField(
        verbose_name=_("Tally"),
        blank=True,
        null=True,
        help_text=_("The sum of encountered tracks."),
    )

    class Meta:
        verbose_name = "Turtle Track Tally Observation"

    def __str__(self):
        t1 = "TrackTally: {0} {1} {2}s of {3}"
        return t1.format(self.tally, self.nest_age, self.nest_type, self.species)


class TurtleNestDisturbanceTallyObservation(Observation):
    """Observation of turtle track tallies and signs of predation."""

    species = models.CharField(
        max_length=300,
        verbose_name=_("Species"),
        choices=lookups.TURTLE_SPECIES_CHOICES,
        default=lookups.TURTLE_SPECIES_DEFAULT,
        help_text=_("The species of the nesting animal."),
    )

    disturbance_cause = models.CharField(
        max_length=300,
        verbose_name=_("Disturbance cause"),
        choices=lookups.NEST_DAMAGE_CHOICES,
        default=lookups.NEST_DAMAGE_DEFAULT,
        help_text=_("The cause of the disturbance."),
    )

    no_nests_disturbed = models.PositiveIntegerField(
        verbose_name=_("Tally of nests disturbed"),
        blank=True,
        null=True,
        help_text=_("The sum of damaged nests."),
    )

    no_tracks_encountered = models.PositiveIntegerField(
        verbose_name=_("Tally of disturbance signs"),
        blank=True,
        null=True,
        help_text=_("The sum of signs, e.g. predator tracks."),
    )

    comments = models.TextField(
        verbose_name=_("Comments"),
        blank=True,
        null=True,
        help_text=_("Any other comments or notes."),
    )

    class Meta:
        verbose_name = "Turtle Nest Disturbance Tally Observation"

    def __str__(self):
        t1 = (
            "Nest Damage Tally: {0} nests of {1} showing disturbance by {2} "
            "({3} disturbance signs sighted)"
        )
        return t1.format(
            self.no_nests_disturbed,
            self.species,
            self.disturbance_cause,
            self.no_tracks_encountered,
        )


class TurtleNestObservation(Observation):
    """Turtle nest observations.

    This model supports data sheets for:

    * Turtle nest observation during tagging
    * Turtle nest excavation after hatching

    Egg count is done as total, plus categories of nest contents following
    "Determining Clutch Size and Hatching Success, Jeffrey D. Miller,
    Research and Management Techniques for the Conservation of Sea Turtles,
    IUCN Marine Turtle Specialist Group, 1999.
    """

    eggs_laid = models.BooleanField(
        verbose_name=_("Did the turtle lay eggs?"),
        default=False,
    )

    egg_count = models.PositiveIntegerField(
        verbose_name=_("Total number of eggs laid"),
        blank=True,
        null=True,
        help_text=_("The total number of eggs laid as observed during tagging."),
    )

    no_egg_shells = models.PositiveIntegerField(
        verbose_name=_("Egg shells (S)"),
        blank=True,
        null=True,
        help_text=_(
            "The number of empty shells counted which were "
            "more than 50 percent complete."
        ),
    )

    no_live_hatchlings_neck_of_nest = models.PositiveIntegerField(
        verbose_name=_("Live hatchlings in neck of nest"),
        blank=True,
        null=True,
        help_text=_("The number of live hatchlings in the neck of the nest."),
    )

    no_live_hatchlings = models.PositiveIntegerField(
        verbose_name=_("Live hatchlings in nest (L)"),
        blank=True,
        null=True,
        help_text=_(
            "The number of live hatchlings left among shells "
            "excluding those in neck of nest."
        ),
    )

    no_dead_hatchlings = models.PositiveIntegerField(
        verbose_name=_("Dead hatchlings (D)"),
        blank=True,
        null=True,
        help_text=_("The number of dead hatchlings that have left" " their shells."),
    )

    no_undeveloped_eggs = models.PositiveIntegerField(
        verbose_name=_("Undeveloped eggs (UD)"),
        blank=True,
        null=True,
        help_text=_("The number of unhatched eggs with no obvious embryo."),
    )

    no_unhatched_eggs = models.PositiveIntegerField(
        verbose_name=_("Unhatched eggs (UH)"),
        blank=True,
        null=True,
        help_text=_(
            "The number of unhatched eggs with obvious, not yet full term, embryo."
        ),
    )

    no_unhatched_term = models.PositiveIntegerField(
        verbose_name=_("Unhatched term (UHT)"),
        blank=True,
        null=True,
        help_text=_(
            "The number of unhatched, apparently full term, embryo"
            " in egg or pipped with small amount of external"
            " yolk material."
        ),
    )

    no_depredated_eggs = models.PositiveIntegerField(
        verbose_name=_("Depredated eggs (P)"),
        blank=True,
        null=True,
        help_text=_(
            "The number of open, nearly complete shells containing egg residue."
        ),
    )

    # end Miller fields
    nest_depth_top = models.PositiveIntegerField(
        verbose_name=_("Nest depth (top) mm"),
        blank=True,
        null=True,
        help_text=_("The depth of sand above the eggs in mm."),
    )

    nest_depth_bottom = models.PositiveIntegerField(
        verbose_name=_("Nest depth (bottom) mm"),
        blank=True,
        null=True,
        help_text=_("The depth of the lowest eggs in mm."),
    )

    sand_temp = models.FloatField(
        verbose_name=_("Sand temperature"),
        blank=True,
        null=True,
        help_text=_("The sand temperature in degree Celsius."),
    )

    air_temp = models.FloatField(
        verbose_name=_("Air temperature"),
        blank=True,
        null=True,
        help_text=_("The air temperature in degree Celsius."),
    )

    water_temp = models.FloatField(
        verbose_name=_("Water temperature"),
        blank=True,
        null=True,
        help_text=_("The water temperature in degree Celsius."),
    )

    egg_temp = models.FloatField(
        verbose_name=_("Egg temperature"),
        blank=True,
        null=True,
        help_text=_("The egg temperature in degree Celsius."),
    )

    comments = models.TextField(
        verbose_name=_("Comments"),
        blank=True,
        null=True,
        help_text=_("Any other comments or notes."),
    )

    class Meta:
        verbose_name = "Turtle Nest Excavation (Egg count)"
        verbose_name_plural = "Turtle Nest Excavations (Egg count)"

    def __str__(self):
        return "Nest Obs {0} eggs, hatching succ {1}, emerg succ {2}".format(
            self.egg_count, self.hatching_success, self.emergence_success
        )

    @property
    def no_emerged(self):
        """The number of hatchlings leaving or departed from nest is S-(L+D)."""
        return (
            (self.no_egg_shells or 0)
            - (self.no_live_hatchlings or 0)
            - (self.no_dead_hatchlings or 0)
        )

    @property
    def egg_count_calculated(self):
        """The calculated egg count from nest excavations.

        Calculated as:

        no_egg_shells + no_undeveloped_eggs + no_unhatched_eggs +
        no_unhatched_term + no_depredated_eggs
        """
        return (
            (self.no_egg_shells or 0)
            + (self.no_undeveloped_eggs or 0)
            + (self.no_unhatched_eggs or 0)
            + (self.no_unhatched_term or 0)
            + (self.no_depredated_eggs or 0)
        )

    @property
    def hatching_success(self):
        """Return the hatching success as percentage [0..100].

        Formula after Miller 1999::

            Hatching success = 100 * no_egg_shells / (
                no_egg_shells + no_undeveloped_eggs + no_unhatched_eggs +
                no_unhatched_term + no_depredated_eggs)
        """
        if self.egg_count_calculated == 0:
            return
        else:
            return round(100 * (self.no_egg_shells or 0) / self.egg_count_calculated, 1)

    @property
    def emergence_success(self):
        """Return the emergence success as percentage [0..100].

        Formula after Miller 1999::

            Emergence success = 100 *
                (no_egg_shells - no_live_hatchlings - no_dead_hatchlings) / (
                no_egg_shells + no_undeveloped_eggs + no_unhatched_eggs +
                no_unhatched_term + no_depredated_eggs)
        """
        if self.egg_count_calculated == 0:
            return
        else:
            return round(
                100
                * (
                    (self.no_egg_shells or 0)
                    - (self.no_live_hatchlings or 0)
                    - (self.no_dead_hatchlings or 0)
                )
                / self.egg_count_calculated,
                1,
            )


class TurtleNestDisturbanceObservation(Observation):
    """Turtle nest disturbance observations.

    Disturbance can be a result of:

    * Predation
    * Disturbance by other turtles
    * Environmental disturbance (cyclones, tides)
    * Anthropogenic disturbance (vehicle damage, poaching, research, harvest)

    Disturbance severity can range from negligible disturbance to total destruction.

    Disturbance cause contains a training category to mark training or test records.
    """

    NEST_VIABILITY_CHOICES = (
        ("negligible", "negligible disturbance"),
        ("partly", "nest partly destroyed"),
        ("completely", "nest completely destroyed"),
        (lookups.NA_VALUE, "nest in indeterminate condition"),
    )

    disturbance_cause = models.CharField(
        max_length=300,
        verbose_name=_("Disturbance cause"),
        choices=lookups.NEST_DAMAGE_CHOICES,
        help_text=_("The cause of the disturbance."),
    )

    disturbance_cause_confidence = models.CharField(
        max_length=300,
        verbose_name=_("Disturbance cause choice confidence"),
        choices=lookups.CONFIDENCE_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("What is the choice of disturbance cause based on?"),
    )

    disturbance_severity = models.CharField(
        max_length=300,
        verbose_name=_("Disturbance severity"),
        choices=NEST_VIABILITY_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("The impact of the disturbance on nest viability."),
    )

    comments = models.TextField(
        verbose_name=_("Comments"),
        blank=True,
        null=True,
        help_text=_("Any other comments or notes."),
    )

    def __str__(self):
        return "Nest Disturbance {0} {1}".format(
            self.disturbance_cause, self.disturbance_severity
        )

    class Meta:
        verbose_name = "Turtle Nest Disturbance Observation"


class PathToSea(models.Model):
    """A Mixin providing code, label and description."""

    code = models.SlugField(
        max_length=500,
        unique=True,
        verbose_name=_("Code"),
        help_text=_("A unique, url-safe code."),
    )

    label = models.CharField(
        blank=True,
        null=True,
        max_length=500,
        verbose_name=_("Label"),
        help_text=_("A human-readable, self-explanatory label."),
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
        help_text=_("A comprehensive description."),
    )

    class Meta:
        ordering = [
            "code",
        ]

    def __str__(self):
        """The full name."""
        return self.label


class TurtleHatchlingEmergenceObservation(Observation):
    """Turtle hatchling emergence observation.

    Hatchling emergence observations can include:

    * Emergence time (if seen directly),
    * Fan angles of hatchling tracks forming a fan from nest to sea,
    * Emergence climate
    * Outliers present (if yes: TurtleHatchlingEmergenceOutlierObservation)
    * Light sources known and present (if yes: LightSourceObservation).

    # TON 0.54+
    "fan_angles": {
        "photo_hatchling_tracks_seawards": "1546836969404.jpg",
        "photo_hatchling_tracks_relief": null,
        "bearing_to_water_manual": "98.0000000000",
        "leftmost_track_manual": "58.0000000000",
        "rightmost_track_manual": "122.0000000000",
        "no_tracks_main_group": "7",
        "no_tracks_main_group_min": "7",
        "no_tracks_main_group_max": "7",
        "outlier_tracks_present": "present",
        "hatchling_path_to_sea": "clear",
        "path_to_sea_comments": null,
        "hatchling_emergence_time_known": "yes",
        "cloud_cover_at_emergence_known": "yes",
        "light_sources_present": "present"
      },
      "outlier_track": {
        "outlier_track_photo": "1546837474680.jpg",
        "outlier_track_bearing_manual": "180.0000000000",
        "outlier_group_size": "1",
        "outlier_track_comment": null
      },
      "hatchling_emergence_time_group": {
        "hatchling_emergence_time": "2019-01-06T23:07:00.000Z",
        "hatchling_emergence_time_source": "plusminus-2h"
      },
      "emergence_climate": {
        "cloud_cover_at_emergence": "3"
      },
      "light_source": [
        {
          "light_source_photo": null,
          "light_bearing_manual": "50.0000000000",
          "light_source_type": "artificial",
          "light_source_description": "Oil rig#5"
        },
        {
          "light_source_photo": null,
          "light_bearing_manual": "190.0000000000",
          "light_source_type": "natural",
          "light_source_description": "Moon"
        }
      ],
      "other_light_sources": {
        "other_light_sources_present": "na"
      }
    """

    # photo_hatchling_tracks_seawards # media
    # photo_hatchling_tracks_relief # media
    bearing_to_water_degrees = models.FloatField(
        verbose_name=_("Bearing to water"),
        blank=True,
        null=True,
        help_text=_("Bearing captured with handheld compass."),
    )

    bearing_leftmost_track_degrees = models.FloatField(
        verbose_name=_("Leftmost track bearing of main fan"),
        blank=True,
        null=True,
        help_text=_(
            "Excluding outlier tracks, 5m from nest or at HWM. Bearing captured with handheld compass."
        ),
    )

    bearing_rightmost_track_degrees = models.FloatField(
        verbose_name=_("Rightmost track bearing of main fan"),
        blank=True,
        null=True,
        help_text=_(
            "Excluding outlier tracks, 5m from nest or at HWM. Bearing captured with handheld compass."
        ),
    )

    no_tracks_main_group = models.PositiveIntegerField(
        verbose_name=_("Number of tracks in main fan"),
        blank=True,
        null=True,
        help_text=_("Exact count or best estimate."),
    )

    no_tracks_main_group_min = models.PositiveIntegerField(
        verbose_name=_("Min number of tracks in main fan"),
        blank=True,
        null=True,
        help_text=_("Lowest estimate."),
    )

    no_tracks_main_group_max = models.PositiveIntegerField(
        verbose_name=_("Max number of tracks in main fan"),
        blank=True,
        null=True,
        help_text=_("Highest estimate."),
    )

    outlier_tracks_present = models.CharField(
        max_length=300,
        verbose_name=_("Outlier tracks present"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_(""),
    )

    hatchling_path_to_sea = models.ManyToManyField(
        PathToSea, blank=True, related_name="path_to_sea"
    )

    path_to_sea_comments = models.TextField(
        verbose_name=_("Hatchling path to sea comments"),
        blank=True,
        null=True,
        help_text=_("Any other comments or notes."),
    )

    hatchling_emergence_time_known = models.CharField(
        max_length=300,
        verbose_name=_("Hatchling emergence time known"),
        choices=(
            (lookups.NA_VALUE, "NA"),
            ("yes", "Yes"),
            ("no", "No"),
        ),
        default=lookups.NA_VALUE,
        help_text=_("."),
    )  # yes no

    cloud_cover_at_emergence_known = models.CharField(
        max_length=300,
        verbose_name=_("Cloud cover at emergence known"),
        choices=(
            (lookups.NA_VALUE, "NA"),
            ("yes", "Yes"),
            ("no", "No"),
        ),
        default=lookups.NA_VALUE,
        help_text=_("."),
    )

    light_sources_present = models.CharField(
        max_length=300,
        verbose_name=_("Light sources present during emergence"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_(""),
    )

    hatchling_emergence_time = models.DateTimeField(
        verbose_name=_("Hatchling emergence time"),
        blank=True,
        null=True,
        help_text=_(
            "The estimated time of hatchling emergence, stored as UTC and "
            "shown in local time."
        ),
    )

    hatchling_emergence_time_accuracy = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        verbose_name=_("Hatchling emergence time estimate accuracy"),
        choices=lookups.TIME_ESTIMATE_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("."),
    )

    cloud_cover_at_emergence = models.PositiveIntegerField(
        verbose_name=_("Cloud cover at emergence"),
        blank=True,
        null=True,
        help_text=_("If known, in eights."),
    )

    class Meta:
        verbose_name = "Turtle Hatchling Emergence Observation (Fan Angle)"
        verbose_name_plural = "Turtle Hatchling Emergence Observations (Fan Angles)"

    def __str__(self):
        """The full name."""
        return "Fan {0} ({1}-{2}) tracks ({3}-{4} deg); water {5} deg".format(
            self.no_tracks_main_group,
            self.no_tracks_main_group_min,
            self.no_tracks_main_group_max,
            self.bearing_leftmost_track_degrees,
            self.bearing_rightmost_track_degrees,
            self.bearing_to_water_degrees,
        )


class LightSourceObservation(Observation):
    """
    Dict of one or list of many
    {
      "light_source_photo": null,
      "light_bearing_manual": "50.0000000000",
      "light_source_type": "artificial"  "natural" CHOICES
      "light_source_description": "Oil rig#5"
    }
    """

    bearing_light_degrees = models.FloatField(
        verbose_name=_("Bearing"),
        blank=True,
        null=True,
        help_text=_("Bearing captured with handheld compass."),
    )

    light_source_type = models.CharField(
        max_length=300,
        verbose_name=_("Light source type"),
        choices=(
            (lookups.NA_VALUE, "NA"),
            ("natural", "Natural"),
            ("artificial", "Artificial"),
        ),
        default=lookups.NA_VALUE,
        help_text=_("."),
    )

    light_source_description = models.TextField(
        verbose_name=_("Comments"),
        blank=True,
        null=True,
        help_text=_("Any other comments or notes."),
    )

    class Meta:
        verbose_name = "Turtle Hatchling Light Source Observation (Fan Angle)"
        verbose_name_plural = "Turtle Hatchling Light Source Observations (Fan Angles)"

    def __str__(self):
        """The full name."""
        return "Light Source {0} at {1} deg: {2}".format(
            self.get_light_source_type_display(),
            self.bearing_light_degrees,
            self.light_source_description or "",
        )


class TurtleHatchlingEmergenceOutlierObservation(Observation):
    """
    Dict of one or list of many
    "outlier_track": {
    "outlier_track_photo": "1546837474680.jpg",
    "outlier_track_bearing_manual": "180.0000000000",
    "outlier_group_size": "1",
    "outlier_track_comment": null
    }
    """

    # outlier_track_photo # media
    bearing_outlier_track_degrees = models.FloatField(
        verbose_name=_("Bearing"),
        blank=True,
        null=True,
        help_text=_(
            "Aim at track 5m from nest or high water mark. Bearing captured with handheld compass."
        ),
    )

    outlier_group_size = models.PositiveIntegerField(
        verbose_name=_("Number of tracks in outlier group"),
        blank=True,
        null=True,
        help_text=_(""),
    )

    outlier_track_comment = models.TextField(
        verbose_name=_("Comments"),
        blank=True,
        null=True,
        help_text=_("Any other comments or notes."),
    )

    class Meta:
        verbose_name = "Turtle Hatchling Emergence Outlier Observation (Fan Angle)"
        verbose_name_plural = (
            "Turtle Hatchling Emergence Outlier Observations (Fan Angles)"
        )

    def __str__(self):
        """The full name."""
        return "Outlier: {0} tracks at {1} deg. {2}".format(
            self.outlier_group_size,
            self.bearing_outlier_track_degrees,
            self.outlier_track_comment or "",
        )


class LoggerObservation(Observation):
    """A logger is observed during an Encounter."""

    LOGGER_TYPE_DEFAULT = "temperature-logger"
    LOGGER_TYPE_CHOICES = (
        (LOGGER_TYPE_DEFAULT, "Temperature Logger"),
        ("data-logger", "Data Logger"),
        ("ctd-data-logger", "Conductivity, Temperature, Depth SR Data Logger"),
    )

    LOGGER_STATUS_DEFAULT = "resighted"
    LOGGER_STATUS_NEW = "programmed"
    LOGGER_STATUS_CHOICES = (
        (LOGGER_STATUS_NEW, "programmed"),
        ("posted", "posted to field team"),
        ("deployed", "deployed in situ"),
        ("resighted", "resighted in situ"),
        ("retrieved", "retrieved in situ"),
        ("downloaded", "downloaded"),
    )

    logger_type = models.CharField(
        max_length=300,
        default=LOGGER_TYPE_DEFAULT,
        verbose_name=_("Type"),
        choices=LOGGER_TYPE_CHOICES,
        help_text=_("The logger type."),
    )

    deployment_status = models.CharField(
        max_length=300,
        default=LOGGER_STATUS_DEFAULT,
        verbose_name=_("Status"),
        choices=LOGGER_STATUS_CHOICES,
        help_text=_("The logger life cycle status."),
    )

    logger_id = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Logger ID"),
        help_text=_("The ID of a logger must be unique within the tag type."),
    )

    comments = models.TextField(
        verbose_name=_("Comment"),
        blank=True,
        null=True,
        help_text=_("Comments"),
    )

    class Meta:
        verbose_name = "Logger Observation"

    def __str__(self):
        if self.logger_id:
            return f'{self.logger_id} ({self.get_logger_type_display()})'
        else:
            return f'{self.get_logger_type_display()}'


# Unused models (TBC)
class TemperatureLoggerSettings(Observation):
    """Temperature Logger Settings."""

    logging_interval = DurationField(
        verbose_name=_("Logging interval"),
        blank=True,
        null=True,
        help_text=_(
            "The time between individual readings as python timedelta "
            "string. E.g, 1h is `01:00:00`; 1 day is `1 00:00:00`."
        ),
    )

    recording_start = models.DateTimeField(
        verbose_name=_("Recording start"),
        blank=True,
        null=True,
        help_text=_(
            "The preset start of recording, stored as UTC and " "shown in local time."
        ),
    )

    tested = models.CharField(
        max_length=300,
        verbose_name=_("Tested"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Was the logger tested after programming?"),
    )

    class Meta:
        verbose_name = "Temperature Logger Setting"

    def __str__(self):
        return "Sampling starting on {0} with rate {1}".format(
            self.recording_start, self.logging_interval
        )


class DispatchRecord(Observation):
    """A record of dispatching the subject of the encounter."""

    sent_to = models.ForeignKey(
        User,
        on_delete=models.SET_DEFAULT,
        default=settings.ADMIN_USER,
        verbose_name=_("Sent to"),
        related_name="receiver",
        blank=True,
        null=True,
        help_text=_("The receiver of the dispatch."),
    )

    class Meta:
        verbose_name = "Dispatch Record"

    def __str__(self):
        return "Sent on {0} to {1}".format(self.encounter.when, self.sent_to)


class TemperatureLoggerDeployment(Observation):
    """A record of deploying a temperature logger."""

    depth_mm = models.PositiveIntegerField(
        verbose_name=_("Logger depth (mm)"),
        blank=True,
        null=True,
        help_text=_("The depth of the buried logger in mm."),
    )

    marker1_present = models.CharField(
        max_length=300,
        verbose_name=_("Marker 1 present"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Is the first marker in place?"),
    )

    distance_to_marker1_mm = models.PositiveIntegerField(
        verbose_name=_("Distance to marker 1 (mm)"),
        blank=True,
        null=True,
        help_text=_("The distance to the first marker in mm."),
    )

    marker2_present = models.CharField(
        max_length=300,
        verbose_name=_("Marker 2 present"),
        choices=lookups.OBSERVATION_CHOICES,
        default=lookups.NA_VALUE,
        help_text=_("Is the second marker in place?"),
    )

    distance_to_marker2_mm = models.PositiveIntegerField(
        verbose_name=_("Distance to marker 2 (mm)"),
        blank=True,
        null=True,
        help_text=_("The distance to the second marker in mm."),
    )

    habitat = models.CharField(
        max_length=500,
        verbose_name=_("Habitat"),
        choices=lookups.HABITAT_CHOICES,
        default="na",
        help_text=_("The habitat in which the nest was encountered."),
    )

    distance_to_vegetation_mm = models.PositiveIntegerField(
        verbose_name=_("Distance to vegetation (mm)"),
        blank=True,
        null=True,
        help_text=_(
            "The distance to the beach-vegetation border in mm. "
            "Positive values if logger is located on beach, "
            "negative values if in vegetation."
        ),
    )

    class Meta:
        verbose_name = "Temperature Logger Deployment"

    def __str__(self):
        return "Logger at {0} mm depth".format(self.depth_mm)
