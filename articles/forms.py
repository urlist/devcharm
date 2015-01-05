# -*- coding: utf-8 -*-
from django import forms
from articles.models import Article


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['raw_content', 'author']

    def clean(self):
        data = self.cleaned_data
        data.update(Article.process_raw_content(data['raw_content']))
        return data

    def save(self, commit=True):
        # We need to add the fields that were generated during the process_raw_content step.
        obj = super(ArticleForm, self).save(commit=False)
        obj.title = self.cleaned_data['title']
        obj.punchline = self.cleaned_data['punchline']
        obj.description = self.cleaned_data['description']
        if commit:
            obj.save()
        return obj