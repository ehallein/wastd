# -*- coding: utf-8 -*-
"""User views."""
from __future__ import absolute_import, unicode_literals
import logging
from export_download.views import ResourceDownloadMixin

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView, FormView
from django.http import HttpResponseRedirect
from .models import User
from .forms import MergeForm
from .filters import UserFilter
from .utils import transfer_user
from shared.views import (
    ListViewBreadcrumbMixin,
    DetailViewBreadcrumbMixin
)

logger = logging.getLogger(__name__)


class UserListView(ListViewBreadcrumbMixin, ResourceDownloadMixin, LoginRequiredMixin, ListView):
    """User list view."""

    model = User
    template_name = 'pages/default_list.html'
    paginate_by = 20
    filter_class = UserFilter
    # resource_class = SurveyResource

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        context['collapse_details'] = True
        context['list_filter'] = UserFilter(
            self.request.GET, queryset=self.get_queryset()
        )
        return context

    def get_queryset(self):
        qs = super(UserListView, self).get_queryset().order_by('username')
        return UserFilter(self.request.GET, queryset=qs).qs


class UserDetailView(DetailViewBreadcrumbMixin, LoginRequiredMixin, DetailView):
    """User detail view."""

    model = User
    # These next two lines tell the view to index lookups by username
    # slug_field = "username"
    # slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        from wastd.observations.models import Survey, Encounter, Observation
        context = super(UserDetailView, self).get_context_data(**kwargs)
        context['collapse_details'] = False
        context['surveys'] = Survey.objects.filter(
            reporter_id=self.kwargs["pk"]
        ).prefetch_related(
            "encounter_set",
            "reporter",
            "area",
            "site",
            "encounter_set__observations"
        )
        context['encounters'] = Encounter.objects.filter(
            reporter_id=self.kwargs["pk"]
        ).prefetch_related(
            "observer",
            "reporter",
            "area",
            "site",
            "observations"
        )
        return context

    def get_object(self):
        """Get Object by pk."""
        obj = User.objects.filter(
            pk=self.kwargs.get("pk")
        ).prefetch_related(
            # "reported_surveys",
            # "encounters_observed",
            # "encounters_observed__reporter",
            # "encounters_observed__observer",
            # "encounters_reported",
            # "encounters_reported__reporter",
            # "encounters_reported__observer",
            # "encounters_reported__area",
            # "encounters_reported__site",

        ).first()
        if not obj:
            raise Http404  # pragma: no cover
        return obj


class UserRedirectView(LoginRequiredMixin, RedirectView):
    """User redirect view."""

    permanent = False

    def get_redirect_url(self):
        """Get redirect url: user detail."""
        return reverse("users:user-detail", kwargs={"pk": self.request.user.pk})


class UserUpdateView(LoginRequiredMixin, UpdateView):
    """User update view."""

    fields = ["name", "nickname", "aliases", "role", "email", "phone"]

    # we already imported User in the view code above, remember?
    model = User

    # send the user back to their own page after a successful update
    def get_success_url(self):
        """Success url: user detail."""
        return reverse("users:user-detail",
                       kwargs={"pk": self.request.user.pk}
                       )

    def get_object(self):
        """Only get the User record for the user making the request."""
        return User.objects.get(pk=self.request.user.pk)


class MergeView(FormView):
    """Merge any two User profiles."""
    template_name = 'pages/default_form.html'
    form_class = MergeForm

    def get_initial(self):
        """
        Set initial user choices to old or new user if provided.

        This View can be used and populated from three URLs,
        providing no User PK, only the old, or both User PKs.
        """
        initial = super().get_initial()
        if "old_pk" in self.kwargs:
            initial['old'] = User.objects.get(pk=self.kwargs["old_pk"])
        if "new_pk" in self.kwargs:
            initial['new'] = User.objects.get(pk=self.kwargs["new_pk"])
        return initial

    def form_valid(self, form):
        """Transfer user, show result as success message, return to new user's detail."""
        old = form.cleaned_data["old"]
        new = form.cleaned_data["new"]
        msg = transfer_user(old, new)
        messages.success(self.request, msg)
        self.success_url = reverse("users:user-detail", kwargs={"pk": new.pk})
        return super().form_valid(form)


def merge_users(request, old_pk, new_pk):
    """Merge two users."""
    try:
        old = User.objects.get(pk=old_pk)
    except:
        messages.error(request, "User with PK {0} not found.".format(old_pk))
        return HttpResponseRedirect("/")
    try:
        new = User.objects.get(pk=new_pk)
    except:
        messages.error(request, "User with PK {0} not found.".format(new_pk))
        return HttpResponseRedirect("/")

    msg = transfer_user(old, new)
    messages.success(request, msg)

    return HttpResponseRedirect(reverse("users:user-detail", kwargs={"pk": new.pk}))
