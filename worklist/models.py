from django.db import models
from viewer.models import Facility as _Facility, WorklistEntry as _WorklistEntry

# Note: All models for the worklist functionality are defined in the viewer app
# This includes WorklistEntry, Facility, Report, etc.
# This is done to avoid circular imports and keep related models together

# Expose these models via the worklist namespace for backwards compatibility
Facility = _Facility
WorklistEntry = _WorklistEntry