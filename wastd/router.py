from django.urls import path
from rest_framework.routers import DefaultRouter
from users import api as users_api
from observations import api as observations_api

from observations.api_v2 import EncounterListResource, EncounterDetailResource


# V2 API URL patterns
urlpatterns = [
    path('encounters/', EncounterListResource.as_view(), name='encounter_list_resource'),
    path('encounters/<int:pk>/', EncounterDetailResource.as_view(), name='encouter_detail_resource'),
]

# V1 API router
router = DefaultRouter()

router.register("users", users_api.UserViewSet)
router.register("area", observations_api.AreaViewSet)
router.register("campaigns", observations_api.CampaignViewSet)
router.register("surveys", observations_api.SurveyViewSet)
router.register("survey-media-attachments", observations_api.SurveyMediaAttachmentViewSet)

# Encounters
router.register("encounters", observations_api.EncounterViewSet, basename="encounters_full")
router.register("encounters-fast", observations_api.FastEncounterViewSet, basename="encounters_fast")
router.register("encounters-src", observations_api.SourceIdEncounterViewSet, basename="encounters_src")
router.register("animal-encounters", observations_api.AnimalEncounterViewSet)
router.register("turtle-nest-encounters", observations_api.TurtleNestEncounterViewSet)
#router.register("logger-encounters", observations_api.LoggerEncounterViewSet)
router.register("line-transect-encounters", observations_api.LineTransectEncounterViewSet)

# General Observations
router.register("observations", observations_api.ObservationViewSet)
router.register("media-attachments", observations_api.MediaAttachmentViewSet)

# Animal Observations
router.register("management-actions", observations_api.ManagementActionViewSet)
router.register("tag-observations", observations_api.TagObservationViewSet)
router.register("turtle-morphometrics", observations_api.TurtleMorphometricObservationViewSet)
router.register("turtle-damage-observations", observations_api.TurtleDamageObservationViewSet)

# Turtle Nest Observations
router.register("turtle-nest-disturbance-observations", observations_api.TurtleNestDisturbanceObservationViewSet)
router.register("nest-tag-observations", observations_api.NestTagObservationViewSet)
router.register("turtle-nest-excavations", observations_api.TurtleNestObservationViewSet)
router.register("turtle-hatchling-morphometrics", observations_api.HatchlingMorphometricObservationViewSet)
router.register("turtle-nest-hatchling-emergences", observations_api.TurtleHatchlingEmergenceObservationViewSet)
router.register("turtle-nest-hatchling-emergence-outliers", observations_api.TurtleHatchlingEmergenceOutlierObservationViewSet)
router.register("turtle-nest-hatchling-emergence-light-sources", observations_api.LightSourceObservationViewSet)
router.register("logger-observations", observations_api.LoggerObservationViewSet)

# Track Tally Obs
router.register("track-tally", observations_api.TrackTallyObservationViewSet)
router.register("turtle-nest-disturbance-tally", observations_api.TurtleNestDisturbanceTallyObservationViewSet)
