# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
from django.db import models
from django.utils import timezone
from django.contrib import admin

# Create your models here.


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')

    def __str__(self):
        return self.question_text

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text


class Word(models.Model):
    word = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.word


class Domain(models.Model):
    name = models.CharField(max_length=12, unique=True)
    is_checked = models.BooleanField(default=False)
    is_available = models.BooleanField(default=False)

    def __str__(self):
        if not self.is_checked:
            return self.name + ' is not checked yet.'
        elif self.is_available:
            return self.name + ' is available to register.'
        else:
            return self.name + ' is NOT available to register.'

