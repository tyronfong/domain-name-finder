# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

# Register your models here.
from .models import Word
from .models import Domain

admin.site.register(Word)

admin.site.register(Domain)
