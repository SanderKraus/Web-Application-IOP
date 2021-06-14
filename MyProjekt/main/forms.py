import logging
from typing import Any, Dict
from django import forms
from django.core.exceptions import ValidationError
from django.forms.fields import FloatField
from django.forms.formsets import formset_factory
from django.forms.models import ModelChoiceField


from .utils import processing_excel_file_buffer
from .models import FctMembership, ReferenceSystem, Tool

log = logging.getLogger(__name__)


class ReferenceItemUploadForm(forms.Form):
    '''
    Eingabefelder und Logik nach dem hochladen des Referenzbauteils
    '''
    name = forms.CharField(max_length=255)
    file = forms.FileField()
    prismatic = forms.BooleanField(initial=True)
    laenge = forms.FloatField(required=False)
    breite = forms.FloatField(required=False)
    hoehe = forms.FloatField(required=False)
    durchmesser = forms.FloatField(required=False)

    def clean(self) -> Dict[str, Any]:
        # beim hochladen cleanen und säubern
        # get buffer from cleaned_data form
        super().clean()
        file_buffer = self.cleaned_data.get('file')
        try:
            # process buffer and create datafame
            df = processing_excel_file_buffer(self, file_buffer)
            self.process_dataframe = df

            # simple verification
            verification_names = [
                'name', 'classifier', 'prismatic', 'positive']
            if not all(item in df.columns.tolist()
                       for item in verification_names):
                raise ValidationError('Excel-Format stimmt nicht.')

        # consume error generate by processing buffer or validation
        except Exception as err:
            log.exception(err)
            raise ValidationError('Fehler beim lesen der Excel')


class ItemUploadForm(forms.Form):
    '''
    Eingabefelder und Logik nach dem hochladen des Vergleichsbauteil
    ähnliches Vorgehen wie bei Referenzupload mit zusätlicher 
    compare_referenz Instanz
    '''
    name = forms.CharField(max_length=255)
    compare_reference = forms.ModelChoiceField(
        queryset=ReferenceSystem.objects.all())
    file = forms.FileField()
    prismatic = forms.BooleanField(initial=True)
    laenge = forms.FloatField(required=False)
    breite = forms.FloatField(required=False)
    hoehe = forms.FloatField(required=False)
    durchmesser = forms.FloatField(required=False)

    def clean(self) -> Dict[str, Any]:
        # get buffer from cleaned_data form
        super().clean()
        file_buffer = self.cleaned_data.get('file')
        try:
            # process buffer and create datafame
            df = processing_excel_file_buffer(self, file_buffer)
            self.process_dataframe = df

            # simple verification
            verification_names = [
                'name', 'classifier', 'prismatic', 'positive']
            if not all(item in df.columns.tolist()
                       for item in verification_names):
                raise ValidationError('Excel-Format stimmt nicht.')

        # consume error generate by processing buffer or validation
        except Exception as err:
            log.exception(err)
            raise ValidationError('Fehler beim lesen der Excel')


class AddTechnologyToReferenceSystemForm(forms.Form):
    '''
    Eingabefelder für das Hinzufügen von Technologien in die 
    Fertigungsprozessfolge
    '''
    technology = forms.ModelChoiceField(queryset=Tool.objects.all())
    hauptzeit = FloatField()
    standmenge = FloatField()
    losgroesse = FloatField()


class FctTableRowForm(forms.Form):
    '''
    Eingabefelder für das Füllen der FCT-Tabelle
    '''
    tool_attribute = ModelChoiceField(queryset=Tool.objects.all())
    input = FloatField()
    output = FloatField()
