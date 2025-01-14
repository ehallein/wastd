from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.admin import register, ModelAdmin, StackedInline, SimpleListFilter
from django.contrib.admin.filters import RelatedFieldListFilter
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django_select2.forms import ModelSelect2Widget
from easy_select2 import select2_modelform as s2form
from fsm_admin.mixins import FSMTransitionMixin
from import_export.admin import ExportActionMixin
from reversion.admin import VersionAdmin

from wastd.utils import FORMFIELD_OVERRIDES, S2ATTRS, CustomStateLogInline
from users.widgets import UserWidget
from .models import (
    Campaign,
    AnimalEncounter,
    Area,
    Encounter,
    HatchlingMorphometricObservation,
    LineTransectEncounter,
    ManagementAction,
    MediaAttachment,
    NestTagObservation,
    Survey,
    SurveyMediaAttachment,
    TagObservation,
    TrackTallyObservation,
    TurtleDamageObservation,
    TurtleMorphometricObservation,
    TurtleNestDisturbanceObservation,
    TurtleNestDisturbanceTallyObservation,
    TurtleNestEncounter,
    TurtleNestObservation,
    TurtleTrackObservation,
    TurtleHatchlingEmergenceObservation,
    TurtleHatchlingEmergenceOutlierObservation,
    LightSourceObservation,
    LoggerObservation
)
from .resources import (
    SurveyResource,
    AnimalEncounterResource,
    TurtleNestEncounterResource,
    LineTransectEncounterResource,
)


class AreaFilter(RelatedFieldListFilter):
    def field_choices(self, field, request, model_admin):
        ordering = self.field_admin_ordering(field, request, model_admin)
        return field.get_choices(
            include_blank=False, limit_choices_to={"area_type": Area.AREATYPE_LOCALITY}, ordering=ordering
        )


class SiteFilter(RelatedFieldListFilter):
    def field_choices(self, field, request, model_admin):
        ordering = self.field_admin_ordering(field, request, model_admin)
        return field.get_choices(
            include_blank=False, limit_choices_to={"area_type": Area.AREATYPE_SITE}, ordering=ordering
        )


class MediaAttachmentInline(admin.TabularInline):
    """TabularInlineAdmin for MediaAttachment."""

    extra = 0
    model = MediaAttachment
    classes = ("grp-collapse grp-open",)
    formfield_overrides = FORMFIELD_OVERRIDES


class TagObservationInline(admin.TabularInline):
    """TabularInlineAdmin for TagObservation."""

    extra = 0
    model = TagObservation
    classes = ("grp-collapse grp-open",)
    # DO NOT ENABLE s2form or else EncounterAdmin will time out
    # form = s2form(TagObservation, attrs=S2ATTRS)


class NestTagObservationInline(StackedInline):
    """TabularInlineAdmin for NestTagObservation."""

    extra = 0
    model = NestTagObservation
    classes = ("grp-collapse grp-open",)


class TurtleMorphometricObservationInline(StackedInline):
    """Admin for TurtleMorphometricObservation."""

    extra = 0
    model = TurtleMorphometricObservation
    classes = ("grp-collapse grp-open",)


class HatchlingMorphometricObservationInline(admin.TabularInline):
    """Admin for HatchlingMorphometricObservation."""

    extra = 0
    model = HatchlingMorphometricObservation
    classes = ("grp-collapse grp-open",)


class ManagementActionInline(admin.TabularInline):
    """TabularInlineAdmin for ManagementAction."""

    extra = 0
    model = ManagementAction
    classes = ("grp-collapse grp-open",)


class TurtleDamageObservationInline(admin.TabularInline):
    """Admin for TurtleDamageObservation."""

    extra = 0
    model = TurtleDamageObservation
    classes = ("grp-collapse grp-open",)


class TrackTallyObservationInline(admin.TabularInline):
    """Admin for TrackTallyObservation."""

    extra = 0
    model = TrackTallyObservation
    classes = ("grp-collapse grp-open",)


class TurtleNestDisturbanceTallyObservationInline(admin.TabularInline):
    """Admin for TurtleNestDisturbanceTallyObservation."""

    extra = 0
    model = TurtleNestDisturbanceTallyObservation
    classes = ("grp-collapse grp-open",)


class TurtleNestObservationInline(StackedInline):
    """Admin for TurtleNestObservation."""

    extra = 0
    model = TurtleNestObservation
    classes = ("grp-collapse grp-open",)

class TurtleTrackObservationInline(admin.TabularInline):
    extra = 0
    model = TurtleTrackObservation
    classes = ("grp-collapse grp-open",)

class TurtleNestDisturbanceObservationInline(admin.TabularInline):
    """Admin for TurtleNestDisturbanceObservation."""

    extra = 0
    model = TurtleNestDisturbanceObservation
    classes = ("grp-collapse grp-open",)


class TurtleHatchlingEmergenceObservationInline(StackedInline):
    """Admin for TurtleHatchlingEmergenceObservation."""

    extra = 0
    model = TurtleHatchlingEmergenceObservation
    classes = ("grp-collapse grp-open",)


class TurtleHatchlingEmergenceOutlierObservationInline(admin.TabularInline):
    """Admin for TurtleHatchlingEmergenceOutlierObservation."""

    extra = 0
    model = TurtleHatchlingEmergenceOutlierObservation
    classes = ("grp-collapse grp-open",)


class LightSourceObservationObservationInline(admin.TabularInline):
    """Admin for LightSourceObservation."""

    extra = 0
    model = LightSourceObservation
    classes = ("grp-collapse grp-open",)


class LoggerObservationInline(admin.TabularInline):
    """Admin for LoggerObservation."""

    extra = 0
    model = LoggerObservation
    classes = ("grp-collapse grp-open",)


class SurveyMediaAttachmentInline(admin.TabularInline):
    """Admin for SurveyMediaAttachment."""

    extra = 0
    model = SurveyMediaAttachment
    classes = ("grp-collapse grp-open",)
    formfield_overrides = FORMFIELD_OVERRIDES


class ObservationAdminMixin(VersionAdmin, ModelAdmin):

    save_on_top = True
    date_hierarchy = "encounter__when"
    LIST_FIRST = (
        "pk",
        "area",
        "site",
        "latitude",
        "longitude",
        "date",
    )
    LIST_LAST = (
        "encounter_link",
        "encounter_status",
    )
    LIST_FILTER = (
        ("encounter__area", AreaFilter),
        ("encounter__site", SiteFilter),
        "encounter__status",
        "encounter__encounter_type",
    )
    search_fields = ("comments",)
    readonly_fields = ("encounter",)
    area = forms.ChoiceField(
        widget=ModelSelect2Widget(
            model=Area,
            search_fields=[
                "name__icontains",
            ],
        )
    )
    site = forms.ChoiceField(
        widget=ModelSelect2Widget(
            model=Area,
            search_fields=[
                "name__icontains",
            ],
        )
    )
    formfield_overrides = FORMFIELD_OVERRIDES

    def area(self, obj):
        """Make data source readable."""
        return obj.encounter.area

    area.short_description = "Area"

    def site(self, obj):
        """Make data source readable."""
        return obj.encounter.site

    site.short_description = "Site"

    def status(self, obj):
        """Make health status human readable."""
        return obj.encounter.get_status_display()

    status.short_description = "Status"

    def latitude(self, obj):
        """Make data source readable."""
        return obj.encounter.latitude

    latitude.short_description = "Latitude"

    def longitude(self, obj):
        """Make data source readable."""
        return obj.encounter.longitude

    longitude.short_description = "Longitude"

    def date(self, obj):
        """Make data source readable."""
        return obj.encounter.when

    date.short_description = "Date"

    def encounter_link(self, obj):
        """A link to the encounter."""
        return mark_safe(
            '<a href="{0}">{1}</a>'.format(
                obj.encounter.absolute_admin_url, obj.encounter.__str__()
            )
        )

    encounter_link.short_description = "Encounter"
    encounter_link.allow_tags = True

    def encounter_status(self, obj):
        """A link to the encounter."""
        return obj.encounter.get_status_display()

    encounter_status.short_description = "QA status"


@register(ManagementAction)
class ManagementActionAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "management_actions",
            "comments",
        )
        + ObservationAdminMixin.LIST_LAST
    )

    list_filter = ObservationAdminMixin.LIST_FILTER + ()
    search_fields = (
        "management_actions",
        "comments",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(MediaAttachment)
class MediaAttachmentAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "media_type",
            "title",
            "thumbnail",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + ("media_type",)
    search_fields = ("title",)
    formfield_overrides = FORMFIELD_OVERRIDES

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )

    def thumbnail(self, obj):
        return obj.thumbnail

    thumbnail.short_description = "Preview"
    thumbnail.allow_tags = True


@register(TurtleMorphometricObservation)
class TurtleMorphometricObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "curved_carapace_length_mm",
            "curved_carapace_length_min_mm",
            "straight_carapace_length_mm",
            "curved_carapace_width_mm",
            "tail_length_carapace_mm",
            "tail_length_vent_mm",
            "tail_length_plastron_mm",
            "maximum_head_width_mm",
            "maximum_head_length_mm",
            "body_depth_mm",
            "body_weight_g",
            "handler",
            "recorder",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + ()
    search_fields = ()

    handler = forms.ChoiceField(widget=UserWidget())
    recorder = forms.ChoiceField(widget=UserWidget())

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "handler",
                "recorder",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(TagObservation)
class TagObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "type_display",
            "name",
            "tag_location_display",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + (
        "tag_type",
        "tag_location",
    )
    search_fields = ("name", "comments")
    form = s2form(TagObservation, attrs=S2ATTRS)

    def type_display(self, obj):
        """Make tag type human readable."""
        return obj.get_tag_type_display()

    type_display.short_description = "Tag Type"

    def tag_location_display(self, obj):
        """Make tag side human readable."""
        return obj.get_tag_location_display()

    tag_location_display.short_description = "Tag Location"

    def animal_name(self, obj):
        """Animal name."""
        return obj.encounter.name

    animal_name.short_description = "Animal Name"


@register(TurtleDamageObservation)
class TurtleDamageObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "body_part",
            "damage_type",
            "damage_age",
            "description",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + (
        "body_part",
        "damage_type",
        "damage_age",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )

@register(TurtleTrackObservation)
class TurtleTrackObservationAdmin(ObservationAdminMixin):
    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "max_track_width_front",
            "max_track_width_rear",
            "carapace_drag_width",
            "step_length",
        )
        + ObservationAdminMixin.LIST_LAST
    )


    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )

@register(TurtleNestDisturbanceObservation)
class TurtleNestDisturbanceObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "disturbance_cause",
            "disturbance_cause_confidence",
            "disturbance_severity",
            "comments",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + (
        "disturbance_cause_confidence",
        "disturbance_severity",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(TurtleNestObservation)
class TurtleNestObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "eggs_laid",
            "egg_count",
            "egg_count_calculated",
            "hatching_success",
            "emergence_success",
            "no_egg_shells",
            "no_live_hatchlings_neck_of_nest",
            "no_live_hatchlings",
            "no_dead_hatchlings",
            "no_undeveloped_eggs",
            "no_unhatched_eggs",
            "no_unhatched_term",
            "no_depredated_eggs",
            "nest_depth_top",
            "nest_depth_bottom",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + ("eggs_laid",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(NestTagObservation)
class NestTagObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "tag_name",
            "flipper_tag_id",
            "date_nest_laid",
            "tag_label",
            "comments",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + (
        "flipper_tag_id",
        "tag_label",
    )
    search_fields = ("flipper_tag_id", "date_nest_laid", "tag_label", "comments")

    def tag_name(self, obj):
        """Nest tag name."""
        return obj.name

    tag_name.short_description = "Complete Nest Tag"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(HatchlingMorphometricObservation)
class HatchlingMorphometricObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + ("straight_carapace_length_mm", "straight_carapace_width_mm", "body_weight_g")
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + ()
    search_fields = ()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(TurtleHatchlingEmergenceObservation)
class TurtleHatchlingEmergenceObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "bearing_to_water_degrees",
            "bearing_leftmost_track_degrees",
            "bearing_rightmost_track_degrees",
            "no_tracks_main_group",
            "no_tracks_main_group_min",
            "no_tracks_main_group_max",
            "outlier_tracks_present",
            "path_to_sea_comments",
            "hatchling_emergence_time_known",
            "cloud_cover_at_emergence_known",
            "light_sources_present",
            "hatchling_emergence_time",
            "hatchling_emergence_time_accuracy",
            "cloud_cover_at_emergence",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + ()
    search_fields = ()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(TurtleHatchlingEmergenceOutlierObservation)
class TurtleHatchlingEmergenceOutlierObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "bearing_outlier_track_degrees",
            "outlier_group_size",
            "outlier_track_comment",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + ()
    search_fields = ()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(LightSourceObservation)
class LightSourceObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "bearing_light_degrees",
            "light_source_type",
            "light_source_description",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + ()
    search_fields = ()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(TrackTallyObservation)
class TrackTallyObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "species",
            "nest_age",
            "nest_type",
            "tally",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + (
        "species",
        "nest_age",
        "nest_type",
    )
    search_fields = ()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(TurtleNestDisturbanceTallyObservation)
class TurtleNestDisturbanceTallyObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + (
            "species",
            "disturbance_cause",
            "no_nests_disturbed",
            "no_tracks_encountered",
            "comments",
        )
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + (
        "species",
        "disturbance_cause",
    )
    search_fields = ("comments",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(LoggerObservation)
class LoggerObservationAdmin(ObservationAdminMixin):

    list_display = (
        ObservationAdminMixin.LIST_FIRST
        + ("logger_type", "deployment_status", "logger_id", "comments")
        + ObservationAdminMixin.LIST_LAST
    )
    list_filter = ObservationAdminMixin.LIST_FILTER + (
        "logger_type",
        "deployment_status",
    )
    search_fields = (
        "logger_id",
        "comments",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "encounter",
                "encounter__reporter",
                "encounter__observer",
                "encounter__area",
                "encounter__site",
            )
        )


@register(Survey)
class SurveyAdmin(ExportActionMixin, FSMTransitionMixin, VersionAdmin):

    date_hierarchy = "start_time"
    list_select_related = (
        "area",
        "site",
        "reporter",
    )
    list_display = (
        "__str__",
        "source",
        "device_id",
        "end_device_id",
        "area",
        "site",
        "start_time",
        "end_time",
        "reporter",
        "start_comments",
        "end_comments",
        "status",
        "production",
        "owner",
    )
    list_filter = (
        "campaign__owner",
        ("area", AreaFilter),
        ("site", SiteFilter),
        "reporter",
        "status",
        "production",
        "device_id",
    )
    search_fields = (
        "area__name",
        "site__name",
        "start_comments",
        "end_comments",
        "reporter__name",
        "reporter__username",
    )

    form = s2form(Survey, attrs=S2ATTRS)
    formfield_overrides = FORMFIELD_OVERRIDES
    fsm_field = ["status"]
    actions = ["merge_user"]
    resource_classes = [SurveyResource]
    fieldsets = (
        (
            _("Device"),
            {
                "classes": ("grp-collapse", "grp-open", "wide", "extrapretty"),
                "fields": (
                    "source",
                    "source_id",
                    "device_id",
                    "end_source_id",
                    "end_device_id",
                    "production",
                ),
            },
        ),
        (
            _("Location"),
            {
                "classes": ("grp-collapse", "grp-open", "wide", "extrapretty"),
                "fields": (
                    "transect",
                    "start_location",
                    "end_location",
                    "area",
                    "site",
                ),
            },
        ),
        (
            _("Time"),
            {
                "classes": ("grp-collapse", "grp-open", "wide", "extrapretty"),
                "fields": (
                    "start_time",
                    "end_time",
                ),
            },
        ),
        (
            _("Campaign"),
            {
                "classes": ("grp-collapse", "grp-open", "wide", "extrapretty"),
                "fields": ("campaign",),
            },
        ),
        (
            _("Team"),
            {
                "classes": ("grp-collapse", "grp-open", "wide", "extrapretty"),
                "fields": (
                    "start_comments",
                    "end_comments",
                    "reporter",
                    "team",
                    "start_photo",
                    "end_photo",
                ),
            },
        ),
    )
    inlines = [
        SurveyMediaAttachmentInline,
        CustomStateLogInline,
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "area":
            kwargs["queryset"] = Area.objects.filter(area_type=Area.AREATYPE_LOCALITY)
        if db_field.name == "site":
            kwargs["queryset"] = Area.objects.filter(area_type=Area.AREATYPE_SITE)
        if db_field.name == "reporter":
            kwargs["queryset"] = get_user_model().objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def owner(self, obj):
        """Resolve owner."""
        if obj.campaign:
            return obj.campaign.owner
        else:
            return "-"

    owner.short_description = "Data Owner"


@register(Area)
class AreaAdmin(ModelAdmin):

    list_display = (
        "area_type",
        "name",
        "w2_location_code",
        "w2_place_code",
        "northern_extent",
        "centroid",
    )
    list_filter = ("area_type",)
    search_fields = (
        "name__icontains",
        "w2_location_code__iexact",
        "w2_place_code__iexact",
    )
    form = s2form(Area, attrs=S2ATTRS)
    formfield_overrides = FORMFIELD_OVERRIDES


@register(Campaign)
class CampaignAdmin(ModelAdmin):

    list_display = (
        "destination",
        "start_time",
        "end_time",
        "owner",
    )
    list_filter = (
        ("destination", AreaFilter),
        "owner",
        "viewers",
    )
    search_fields = (
        "owner__code__icontains",
        "owner__label__icontains",
        "owner__description__icontains",
        "comments__icontains",
    )
    date_hierarchy = "start_time"
    form = s2form(Campaign, attrs=S2ATTRS)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "destination",
                "owner",
            )
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Restrict destination to Localities.

        Plug in customisations for other FK fields here as needed.

        Args:
            db_field (str): The name of the FK field as defined in the Model.
            request (request): The request

        Returns:
            _type_: The modified method ``formfield_for_foreignkey``.
        """
        if db_field.name == "destination":
            kwargs["queryset"] = Area.objects.filter(area_type=Area.AREATYPE_LOCALITY)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@register(Encounter)
class EncounterAdmin(FSMTransitionMixin, VersionAdmin):
    """Admin for Encounter with inlines for all Observations.
    This admin can be extended by other Encounter Admin classes.
    """
    class QAStatusFilter(SimpleListFilter):
        title = 'QA status'
        parameter_name = 'qa_status'

        def lookups(self, request, model_admin):
            return (
                (Encounter.STATUS_NEW, _("New")),
                (Encounter.STATUS_IMPORTED, _("Imported")),
                (Encounter.STATUS_MANUAL_INPUT, _("Manual input")),
                (Encounter.STATUS_CURATED, _("Curated")),
                (Encounter.STATUS_FLAGGED, _("Flagged")),
                (Encounter.STATUS_REJECTED, _("Rejected")),
            )

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(status=self.value())

    date_hierarchy = "when"
    list_filter = (
        #"campaign__owner",
        ("area", AreaFilter),
        ("site", SiteFilter),
        QAStatusFilter,
        "observer",
        "reporter",
        #"location_accuracy",
        "encounter_type",
        "source",
    )
    FIRST_COLS = (
        "when",
        "area",
        "site",
        "encounter_type",
        "latitude",
        "longitude",
        #"location_accuracy",
        #"location_accuracy_m",
        #"name_link",
    )
    LAST_COLS = (
        "observer",
        "reporter",
        "source_display",
        "source_id",
        "status",
    )
    list_display = FIRST_COLS + LAST_COLS
    search_fields = (
        "observer__name",
        "observer__username",
        "name",
        "reporter__name",
        "reporter__username",
        "source_id",
    )
    list_select_related = ("area", "site", "survey", "observer", "reporter", "campaign")

    form = s2form(Encounter, attrs=S2ATTRS)
    formfield_overrides = FORMFIELD_OVERRIDES
    autocomplete_fields = ["area", "site", "survey", "campaign"]
    # UserWidget excludes inactive users
    observer = forms.ChoiceField(widget=UserWidget())
    reporter = forms.ChoiceField(widget=UserWidget())
    readonly_fields = ("name",)

    # Django-fsm transitions config
    fsm_field = ["status"]

    # Change_view form layout
    fieldsets = (
        (
            "Encounter",
            {
                "classes": ("grp-collapse", "grp-open", "wide", "extrapretty"),
                "fields": (
                    "area",
                    "site",
                    "campaign",
                    "survey",
                    "where",
                    "location_accuracy",
                    "location_accuracy_m",
                    "when",
                    "observer",
                    "reporter",
                    "encounter_type",
                    "source",
                    "source_id",
                    #"name",
                ),
            },
        ),
    )

    # Change_view inlines
    inlines = [
        MediaAttachmentInline,
        TagObservationInline,
        TurtleDamageObservationInline,
        TurtleMorphometricObservationInline,
        TrackTallyObservationInline,
        TurtleNestDisturbanceTallyObservationInline,
        ManagementActionInline,
        NestTagObservationInline,
        TurtleNestObservationInline,
        TurtleNestDisturbanceObservationInline,
        HatchlingMorphometricObservationInline,
        TurtleHatchlingEmergenceObservationInline,
        TurtleHatchlingEmergenceOutlierObservationInline,
        LightSourceObservationObservationInline,
        LoggerObservationInline,
        CustomStateLogInline,
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "observer", "reporter", "area", "site", "survey", "campaign"
            )
        )

    def name_link(self, obj):
        """List other encounters with the same subject."""
        return mark_safe(
            '<a href="{0}?name={1}" target="_" rel="nofollow" '
            'title="List all encounters with the same subject">{1}</a>'.format(
                reverse("admin:observations_encounter_changelist"), obj.name
            )
        )

    name_link.short_description = "Encounter History"
    name_link.allow_tags = True

    def source_display(self, obj):
        """Make data source readable."""
        return obj.get_source_display()

    source_display.short_description = "Data Source"

    def latitude(self, obj):
        """Make data source readable."""
        return obj.latitude

    latitude.short_description = "Latitude"

    def longitude(self, obj):
        """Make data source readable."""
        return obj.longitude

    longitude.short_description = "Longitude"

    def encounter_type_display(self, obj):
        """Make encounter type readable."""
        return obj.get_encounter_type_display()

    encounter_type_display.short_description = "Encounter Type"

    def owner(self, obj):
        """Resolve owner."""
        if obj.campaign:
            return obj.campaign.owner
        else:
            return "-"

    owner.short_description = "Data Owner"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Restrict Area and Site options to Localities and Sites,
        and Users to active profiles."""
        if db_field.name == "area":
            kwargs["queryset"] = Area.objects.filter(area_type=Area.AREATYPE_LOCALITY)
        if db_field.name == "site":
            kwargs["queryset"] = Area.objects.filter(area_type=Area.AREATYPE_SITE)
        if db_field.name == "observer":
            kwargs["queryset"] = get_user_model().objects.filter(is_active=True)
        if db_field.name == "reporter":
            kwargs["queryset"] = get_user_model().objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


def curate_encounter(modeladmin, request, queryset):
    """A custom action to allow record status to be marked as curated.
    """
    for obj in queryset:
        obj.curate(by=request.user, description="Curated record as trustworthy")
        obj.save()
    messages.success(request, f"Curated selected encounter(s) as trustworthy")


curate_encounter.short_description = "Curate selected encounter records as trustworthy"


def flag_encounter(modeladmin, request, queryset):
    """A custom action to allow record status to be marked as flagged.
    """
    for obj in queryset:
        obj.flag(by=request.user, description="Flagged record as untrustworthy")
        obj.save()
    messages.warning(request, f"Flagged selected encounter(s) as untrustworthy")


flag_encounter.short_description = "Flag selected encounter records as untrustworthy"


def reject_encounter(modeladmin, request, queryset):
    """A custom action to allow record status to be marked as rejected.
    """
    for obj in queryset:
        obj.reject(by=request.user, description="Reject record as unusable")
        obj.save()
    messages.warning(request, f"Rejected selected encounter(s) as unusable")


reject_encounter.short_description = "Reject selected encounter records as unusable"


@register(AnimalEncounter)
class AnimalEncounterAdmin(ExportActionMixin, EncounterAdmin):
    actions = [curate_encounter, flag_encounter]
    resource_classes = [AnimalEncounterResource]

    form = s2form(AnimalEncounter, attrs=S2ATTRS)
    list_display = (
        EncounterAdmin.FIRST_COLS
        + (
            "taxon",
            "species",
            "health_display",
            "cause_of_death",
            "cause_of_death_confidence",
            "maturity_display",
            "sex_display",
            "behaviour",
            "habitat_display",
            "sighting_status",
            "sighting_status_reason",
            "identifiers",
            "site_of_first_sighting",
            "datetime_of_last_sighting",
            "site_of_last_sighting",
            "nesting_event",
            "nesting_disturbed",
            "checked_for_injuries",
            "scanned_for_pit_tags",
            "checked_for_flipper_tags",
        )
        + EncounterAdmin.LAST_COLS
    )
    list_select_related = (
        "area",
        "site",
        "survey",
        "observer",
        "reporter",
        "site_of_first_sighting",
        "site_of_last_sighting",
    )
    list_filter = EncounterAdmin.list_filter + (
        "taxon",
        "species",
        "health",
        "cause_of_death",
        "cause_of_death_confidence",
        "maturity",
        "sex",
        "habitat",
        "sighting_status",
        "datetime_of_last_sighting",
        "site_of_first_sighting",
        "site_of_last_sighting",
        "nesting_event",
        "nesting_disturbed",
        "checked_for_injuries",
        "scanned_for_pit_tags",
        "checked_for_flipper_tags",
        "laparoscopy",
    )
    search_fields = EncounterAdmin.search_fields + (
        "sighting_status_reason",
        "identifiers",
    )
    readonly_fields = (
        "name",
        "sighting_status",
        "sighting_status_reason",
        "identifiers",
        "datetime_of_last_sighting",
        "site_of_first_sighting",
        "site_of_last_sighting",
    )
    fieldsets = EncounterAdmin.fieldsets + (
        (
            "Animal",
            {
                "classes": ("grp-collapse", "grp-open", "wide", "extrapretty"),
                "fields": (
                    "taxon",
                    "species",
                    "maturity",
                    "sex",
                    "activity",
                    "behaviour",
                    "habitat",
                    "health",
                    "cause_of_death",
                    "cause_of_death_confidence",
                    "nesting_event",
                    "nesting_disturbed",
                    "checked_for_injuries",
                    "scanned_for_pit_tags",
                    "checked_for_flipper_tags",
                    "laparoscopy",
                ),
            },
        ),
        (
            "Recapture Status",
            {
                "classes": ("grp-collapse", "grp-open", "wide", "extrapretty"),
                "fields": (
                    "sighting_status",
                    "datetime_of_last_sighting",
                    "site_of_first_sighting",
                    "site_of_last_sighting",
                ),
            },
        ),
    )
    inlines = [
        MediaAttachmentInline,
        TagObservationInline,
        TurtleDamageObservationInline,
        TurtleMorphometricObservationInline,
        TurtleNestObservationInline,
        NestTagObservationInline,
        ManagementActionInline,
        CustomStateLogInline,
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "observer",
                "reporter",
                "area",
                "site",
                "survey",
                "campaign",
                "site_of_first_sighting",
                "site_of_last_sighting",
            )
        )

    def sighting_status_display(self, obj):
        """Make sighting status human readable."""
        return obj.get_sighting_status_display()

    sighting_status_display.short_description = "Sighting Status"

    def health_display(self, obj):
        """Make health status human readable."""
        return obj.get_health_display()

    health_display.short_description = "Health"

    def maturity_display(self, obj):
        """Make maturity human readable."""
        return obj.get_maturity_display()

    maturity_display.short_description = "Maturity"

    def sex_display(self, obj):
        """Make sex human readable."""
        return obj.get_sex_display()

    sex_display.short_description = "Sex"

    def status_display(self, obj):
        """Make QA status human readable."""
        return obj.get_status_display()

    status_display.short_description = "QA Status"

    def habitat_display(self, obj):
        """Make habitat human readable."""
        return obj.get_habitat_display()

    habitat_display.short_description = "Habitat"


@register(TurtleNestEncounter)
class TurtleNestEncounterAdmin(ExportActionMixin, EncounterAdmin):

    class TurtleNestEncounterTypeFilter(SimpleListFilter):
        title = 'Encounter type'
        parameter_name = 'encounter_type'

        def lookups(self, request, model_admin):
            return (
                (Encounter.ENCOUNTER_NEST, "Nest"),
                (Encounter.ENCOUNTER_TRACKS, "Tracks"),
            )

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(encounter_type=self.value())

    actions = [curate_encounter, flag_encounter, reject_encounter]
    form = s2form(TurtleNestEncounter, attrs=S2ATTRS)
    list_display = (
        EncounterAdmin.FIRST_COLS
        + (
            "age_display",
            "type_display",
            "species",
            "habitat_display",
            "disturbance",
            "comments",
        )
        + EncounterAdmin.LAST_COLS
    )
    list_select_related = True
    list_filter = (
        ('when', admin.DateFieldListFilter),
        "campaign__owner",
        ("area", AreaFilter),
        ("site", SiteFilter),
        EncounterAdmin.QAStatusFilter,
        "observer",
        "reporter",
        #"location_accuracy",
        TurtleNestEncounterTypeFilter,
        "source",
        "nest_age",
        "nest_type",
        "species",
        "habitat",
        "disturbance",
        "nest_tagged",
        "logger_found",
        "eggs_counted",
        "hatchlings_measured",
        "fan_angles_measured",
    )
    fieldsets = EncounterAdmin.fieldsets + (
        (
            "Nest",
            {
                "classes": ("grp-collapse", "grp-open", "wide", "extrapretty"),
                "fields": (
                    "nest_age",
                    "nest_type",
                    "species",
                    "habitat",
                    "disturbance",
                    "nest_tagged",
                    "logger_found",
                    "eggs_counted",
                    "hatchlings_measured",
                    "fan_angles_measured",
                    "comments",
                ),
            },
        ),
    )
    inlines = [
        MediaAttachmentInline,
        NestTagObservationInline,
        TurtleNestObservationInline,
        TurtleNestDisturbanceObservationInline,
        TurtleTrackObservationInline,
        HatchlingMorphometricObservationInline,
        TurtleHatchlingEmergenceObservationInline,
        TurtleHatchlingEmergenceOutlierObservationInline,
        LightSourceObservationObservationInline,
        LoggerObservationInline,
        CustomStateLogInline,
    ]
    resource_classes = [TurtleNestEncounterResource]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("observer", "reporter", "area", "site")

    def habitat_display(self, obj):
        """Make habitat human readable."""
        return obj.get_habitat_display()

    habitat_display.short_description = "Habitat"

    def age_display(self, obj):
        """Make nest age human readable."""
        return obj.get_nest_age_display()

    age_display.short_description = "Nest age"

    def type_display(self, obj):
        """Make nest type human readable."""
        return obj.get_nest_type_display()

    type_display.short_description = "Nest type"


@register(LineTransectEncounter)
class LineTransectEncounterAdmin(ExportActionMixin, EncounterAdmin):

    form = s2form(LineTransectEncounter, attrs=S2ATTRS)
    list_display = EncounterAdmin.FIRST_COLS + ("transect",) + EncounterAdmin.LAST_COLS
    list_select_related = (
        "area",
        "site",
        "survey",
    )
    fieldsets = EncounterAdmin.fieldsets + (
        (
            "Location",
            {
                "classes": ("grp-collapse", "grp-open", "wide", "extrapretty"),
                "fields": ("transect",),
            },
        ),
    )
    inlines = [
        MediaAttachmentInline,
        TrackTallyObservationInline,
        TurtleNestDisturbanceTallyObservationInline,
        CustomStateLogInline,
    ]
    resource_classes = [LineTransectEncounterResource]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "observer",
                "reporter",
                "area",
                "site",
            )
        )
