import logging
import pprint
from typing import Any, Dict, List, Optional
from django.core.exceptions import ObjectDoesNotExist, ValidationError, ViewDoesNotExist
from django.db.models.fields import PositiveIntegerRelDbTypeMixin
from django.db.models.query import QuerySet
from django.views.generic.base import RedirectView
from django.db import transaction
from django.forms.models import BaseModelForm
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.urls import reverse_lazy
from django.urls.base import reverse
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic import TemplateView
from django.views.generic.edit import (
    CreateView, FormView, UpdateView, DeleteView)
from extra_views.formsets import ModelFormSetMixin, ModelFormSetView

from .models import CostReference, EcrCost, EcrFuzzy, FctAttribute, FctMembership, Feature, FeatureAttribute, Halbzeug, Result
from .models import Item, ReferenceSystem, Technology, Tool, ToolAttribute
from .models import Volume
from .forms import AddTechnologyToReferenceSystemForm, ItemUploadForm, ReferenceItemUploadForm
from .utils import create_features_from_df, remove_umlaut

log = logging.getLogger(__name__)


class IndexView(TemplateView):
    '''
    Startseite
    '''

    def get_template_names(self) -> List[str]:
        return ['main/index.html']


class ReferenceList(ListView):
    '''
    Liste aller Referenzsysteme
    '''
    model = ReferenceSystem
    template_name = 'main/reference/list.html'


class ReferenceDetail(DetailView):
    '''
    Detailansicht eines Referenzsystems
    Buttons für Technologien hinzufügen
    '''
    model = ReferenceSystem
    template_name = 'main/reference/detail.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        fea = Feature.objects.filter(
            item__reference_id=self.kwargs.get('pk'))
        tech = FctMembership.objects.filter(
            reference=self.kwargs.get('pk'))

        # Buttons für Volumenberechnung nur Anzeigen, wenn WERTE in FCT-Tabelle
        length = 0
        for f in fea:
            length += len(f.featureattribute_set.all())
        context['features'] = fea

        if tech:
            show_get_volume = True
        else:
            show_get_volume = False
        for t in tech:
            if length != len(t.fctattribute_set.all()):
                show_get_volume = False

        context['technologies'] = tech
        context['show'] = show_get_volume
        ref = Item.objects.filter(compare_reference=self.kwargs.get('pk'))
        if ref:
            context['add_to_fct'] = ref[0].feature_set.filter(
                add_to_fct=True).all()
        return context


class ReferenceSystemCreate(CreateView):
    '''
    Referenzsystem erstellen
    '''
    model = ReferenceSystem
    fields = ['name', 'laufzeit_jahr', 'betrachtungszeitraum',
              'produktpreis', 'lohnnebenkostenanteil', 'dichte', 'kilopreis']
    template_name = 'main/reference/form.html'


class ReferenceModelUpdate(UpdateView):
    '''
    Referenzsystem ändern
    '''
    model = ReferenceSystem
    fields = ['name', 'laufzeit_jahr', 'betrachtungszeitraum',
              'produktpreis', 'lohnnebenkostenanteil', 'dichte', 'kilopreis']
    template_name = 'main/reference/form.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        self.reference = ReferenceSystem.objects.get(pk=self.kwargs.get('pk'))
        context['reference'] = self.reference
        return context


class ReferenceModelTechnologyUpdate(FormView):
    '''
    Technologie in Fertigungsprozessfolge hinzufügen damit
    FCT-Tabelle generiert werden kann
    '''
    form_class = AddTechnologyToReferenceSystemForm
    template_name = 'main/reference/add_technology_form.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['membership'] = FctMembership.objects.filter(
            reference_id=self.kwargs.get('pk'))
        return context

    def get_success_url(self) -> str:
        # access model from form_valid to generate complete url
        return reverse('referencemodel-detail', args=[str(self.model.id)])

    def form_valid(self, form: AddTechnologyToReferenceSystemForm) -> HttpResponse:
        # add attribute to instance to access it in get_success_url
        self.model = ReferenceSystem.objects.get(pk=self.kwargs.get('pk'))

        # save new membership with model and cleaned_data
        member = FctMembership(
            reference=self.model,
            tool=form.cleaned_data['technology'],
            hauptzeit=form.cleaned_data['hauptzeit'],
            losgroesse=form.cleaned_data['losgroesse'],
            standmenge=form.cleaned_data['standmenge']
        )
        member.set_position()
        member.save()
        return super().form_valid(form)


class ReferenceModelTechnologyDelete(DeleteView):
    '''
    Technologie aus Fertigungsprozessfolge löschen
    '''
    template_name = 'main/reference/delete_technology.html'
    model = FctMembership

    def delete(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        # reference model
        model = self.get_object()
        # delete all models with higher position
        FctMembership.objects.filter(
            position__gt=model.position, reference=model.reference).delete()
        return super().delete(request, *args, **kwargs)

    def get_success_url(self) -> str:
        return reverse('referencemodel-detail', args=[str(self.kwargs.get('ref'))])


class ReferenceSystemDelete(DeleteView):
    '''
    Referenzsystem löschen mit Button für zurück
    '''
    model = ReferenceSystem
    template_name = 'main/reference/delete.html'
    success_url = reverse_lazy('referencemodel-list')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        self.reference = ReferenceSystem.objects.get(pk=self.kwargs.get('pk'))
        context['reference'] = self.reference
        return context


class ReferenceUpload(FormView):
    '''
    Hochladen eines Referenzsystems mit Button für zurück
    '''
    form_class = ReferenceItemUploadForm
    template_name = 'main/reference/features_upload.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        # Button
        context = super().get_context_data(**kwargs)
        self.reference = ReferenceSystem.objects.get(pk=self.kwargs.get('pk'))
        context['reference'] = self.reference
        return context

    def get_success_url(self) -> str:
        # access model from form_valid to generate complete url
        return reverse('refupload', args=[str(self.model.id)])

    def form_valid(self, form: ReferenceItemUploadForm) -> HttpResponse:
        try:

            # add attribute to instance to access it in get_success_url
            # kwargs ist keyword und zieht die Informationen aus der url
            self.model = ReferenceSystem.objects.get(pk=self.kwargs.get('pk'))

            # create item for reference system
            item = Item(reference=self.model,
                        name=form.cleaned_data.get('name'))

            # start transaction to save df to db as features and attrs
            with transaction.atomic():
                item.save()

                # create features and merkmale
                create_features_from_df(
                    form.process_dataframe, item)

                # return form is valid and saved
                return super().form_valid(form)

        # raise exception if transaction failed
        except Exception as err:
            log.exception(err)
            form.add_error(
                None, error='Database INSERT failed => Transaction ROLLBACK')
            # return form with errors
            return super().form_invalid(form)


class TechnologyList(ListView):
    '''
    Liste aller Technologien in der Datenbank
    '''
    model = Technology
    template_name = 'main/technology/list.html'


class TechnologyDetail(DetailView):
    '''
    Technologieansicht mit Buttons zum anlegen von Werkzeugen und
    Leistungsfähigkeitsprofilen
    '''
    model = Technology
    template_name = 'main/technology/detail.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['tools'] = Tool.objects.filter(
            technology_id=self.kwargs.get('pk'))
        return context


class TechnologyCreate(CreateView):
    '''
    Maschine anlegen
    '''
    model = Technology
    fields = '__all__'
    template_name = 'main/technology/technology_form.html'


class TechnologyUpdate(UpdateView):
    '''
    Maschine updaten/ändern
    '''
    model = Technology
    fields = '__all__'
    template_name = 'main/technology/technology_form.html'


class TechnologyDelete(DeleteView):
    '''
    Maschine löschen
    '''
    model = Technology
    template_name = 'main/technology/technology_delete.html'
    success_url = reverse_lazy('technology-list')


class ToolCreate(CreateView):
    '''
    Werkzeug erstellen
    '''
    model = Tool
    template_name = 'main/technology/tool_form.html'
    fields = ['name', 'verteilzeit', 'ruestzeit', 'erholungszeit', 'werkzeugwechselzeit',
              'werkstueckwechselzeit', 'betriebsstoffkosten', 'werkzeugpreis']

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        self.technology = Technology.objects.get(
            pk=self.kwargs.get('pk'))
        context['technology'] = self.technology
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        # add foreignkey to save model to database correctly
        form.instance.technology_id = self.kwargs.get('pk')
        return super().form_valid(form)


class ToolUpdate(UpdateView):
    '''
    Werkzeug updaten/ändern
    '''
    model = Tool
    template_name = 'main/technology/tool_form.html'
    fields = ['name']

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['tool'] = self.model.objects.get(
            pk=self.kwargs.get('pk'))
        return context


class ToolDelete(DeleteView):
    '''
    Werkzeug löschen
    '''
    model = Tool
    template_name = 'main/technology/tool_delete.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        self.technology = Technology.objects.get(
            pk=self.kwargs.get('technology_id'))
        context['technology'] = self.technology
        return context

    def get_success_url(self) -> str:
        return reverse('technology-detail',
                       args=[str(self.kwargs.get('technology_id'))])


class ToolAttributeCreate(CreateView):
    '''
    Leistungsfähigkeitsprofil erstellen
    '''
    model = ToolAttribute
    template_name = 'main/technology/attribute_form.html'
    fields = ['name', 'a', 'b', 'c', 'd', 'einheit']

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        self.tool = Tool.objects.get(pk=self.kwargs.get('pk'))
        context['tool'] = self.tool
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        # add foreignkey to save model to database correctly
        form.instance.tool_id = self.kwargs.get('pk')
        return super().form_valid(form)


class ToolAttributeUpdate(UpdateView):
    '''
    Leistungsfähigkeitsprofil updaten/ändern
    '''
    model = ToolAttribute
    template_name = 'main/technology/attribute_update.html'
    fields = ['name', 'a', 'b', 'c', 'd', 'einheit']

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['attr'] = self.model.objects.get(
            pk=self.kwargs.get('pk'))
        return context


class ToolAttributeDelete(DeleteView):
    '''
    Leistungsfähigkeitsprofil löschen
    '''
    model = ToolAttribute
    template_name = 'main/technology/attribute_delete.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        self.technology = Technology.objects.get(
            pk=self.kwargs.get('technology_id'))
        context['technology'] = self.technology
        return context

    def get_success_url(self) -> str:
        return reverse('technology-detail', args=[str(self.kwargs.get('technology_id'))])


class FctTableForm(ModelFormSetView):
    '''
    Darstellung der FCT-Tabelle
    ModelFormSetView ist eine Extension und kombiniert
    '''
    template_name = 'main/reference/fct_table_form.html'
    model = FctAttribute
    exclude = ['difference', 'input_possible', 'output_possible']

    # Informationen und Aktionen die auf der Seite Angezeigt/Durchgeführt
    # werden sollen
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context['merkmal'] = self.merkmal

        # get next and previous merkmal
        context['next'] = FeatureAttribute.objects.filter(
            feature__item__reference=self.kwargs.get('pk'), id__gt=self.merkmal.id,
        ).first()

        context['back'] = FeatureAttribute.objects.filter(
            feature__item__reference=self.kwargs.get('pk'),
            id__lt=self.merkmal.id).order_by('-id').first()

        # get reference system
        context['reference'] = ReferenceSystem.objects.get(
            pk=self.kwargs.get('pk'))

        print(context['next'])

        # print(Feature.objects.filter(item__reference=self.kwargs.get('pk')).all())
        return context

    def get_factory_kwargs(self):
        # get current merkmal
        self.merkmal = FeatureAttribute.objects.get(
            pk=self.kwargs.get('merkmal'))

        # die Anzahl der Spalten wird an formset übergeben
        # generate arguments for formset_factory
        kwargs = super().get_factory_kwargs()
        self.members = FctMembership.objects.filter(
            reference=self.kwargs.get('pk'))
        kwargs['max_num'] = len(self.members)
        kwargs['min_num'] = len(self.members)
        print(len(self.members))
        return kwargs

    def get_queryset(self) -> QuerySet:
        # get all fctattribute for update
        reference_pk = self.kwargs.get('pk')
        queryset = super(FctTableForm, self).get_queryset().filter(
            membership__reference__id=reference_pk,
            feature_attribute__id=self.kwargs.get('merkmal')).order_by('membership')
        return queryset

    def get_initial(self):
        # initialize empty forms
        attribute = FeatureAttribute.objects.get(pk=self.kwargs.get('merkmal'))
        initial_data = [{'feature_attribute': attribute.id,
                         'membership': member.id} for member in self.members]
        return initial_data

    def construct_formset(self):
        formset = super().construct_formset()
        # add choices filtered by fctmembership
        for index, form in enumerate(formset):
            if not form.fields.get('tool_attribute').queryset:
                form.fields.get(
                    'tool_attribute').queryset = self.members[index] \
                    .tool.toolattribute_set.all()
        return formset

    def formset_valid(self, formset):
        # validate in- and outputs then save forms
        self.object_list = formset.save(commit=False)
        try:
            # start saving models with transaction
            with transaction.atomic():
                for index, form in enumerate(formset):

                    # check for misaligned in and output
                    if index < len(formset) - 1 and \
                        form.cleaned_data['output'] != \
                            formset[index + 1].cleaned_data['input']:
                        form.add_error(
                            'output', error='ouput checken')
                        formset[index + 1].add_error(
                            'input', error='input checken')
                        raise ValidationError(f'Form-{index}: Input != Output')

                    # check if output matches target from merkmal
                    elif index == len(formset) - 1 and \
                            form.cleaned_data['output'] != self.merkmal.value:
                        form.add_error(
                            'output', error='stimmt nicht mit Zielwert überein')
                        raise ValidationError(
                            f'Form-{index}: Output != Zielwert')

                    # wenn kein fehler auftritt, werden die FCT In- und Outputs in
                    # die Tabelle FCT-Attribute abgespeichert
                    form.save()
            return super(ModelFormSetMixin, self).formset_valid(formset)

        # consume exception and render form with error
        except Exception as err:
            log.exception(err)
            return super().formset_invalid(formset)

    def get_success_url(self) -> str:
        next_merkmal = FeatureAttribute.objects.filter(
            feature__item__reference=self.kwargs.get('pk'),
            id__gt=self.merkmal.id).first()
        # got to next fct-table row if there is next_merkmal
        if next_merkmal:
            return reverse('fct-table', args=[str(self.kwargs.get('pk')),
                                              str(next_merkmal.id)])
        # else go back to reference-system overview
        else:
            return reverse('referencemodel-detail',
                           args=[str(self.kwargs.get('pk'))])


class CalculateFctTableVolumes(RedirectView):
    '''
    Button für die Berechnung der Änderungsvolumina für Referenzbauteil
    Volumen und abspeichern
    '''
    # TODO: set messages for errors

    def dispatch(self, request, *args, **kwargs):
        # get all technologies
        members = FctMembership.objects.filter(
            reference=self.kwargs.get('pk')).all()
        # get all features
        features = Feature.objects.filter(
            item__reference_id=self.kwargs.get('pk'))

        # beschreibt die volumenbeschreibenden Merkmale
        # wird für die Bestimmung der benötigten Merkmale für die Berechnung der
        # Volumen verwendet
        possible_volume_fields = ['länge', 'breite', 'höhe', 'tiefe', 'durchmesser',
                                  'breite_fuss', 'tiefe_fuss', 'winkel']

        try:
            with transaction.atomic():
                # set volumes for every technology
                # durch die Spalten jeder Technologie in der Fertigungsprozessfolge
                # FCT_Member

                for technology in members:

                    volume_input_num = 0
                    volume_output_num = 0
                    # itereate over features and create dict to hold values for volume
                    # jedes Feature nehmen und in Abhängigkeit des Classifiers in ein
                    # dict speichern (für In- und Output)
                    for feature in features:
                        # zwei Dictionarys werden instanziirt für Input und Output
                        # der erste Key ist volume_type und wird mit dem Classifier des Features gefüllt
                        volume_input = {
                            'volume_type': feature.classifier.lower()}
                        volume_output = {
                            'volume_type': feature.classifier.lower()}
                        # iterate over merkmale and save value in corresponding dicts
                        # alle Merkmale des betrachteten Features werden genommen und einzelnt
                        # durchiteriert
                        merkmale = feature.featureattribute_set.all()
                        for merkmal in merkmale:
                            # in diesem Schritt werden die volumenbeschreibenden Merkmale eines Features ausgewählt
                            # falls ein Merkmal in der Iteration ist, wird die Schleife von vorne begonnen mit dem nächsten
                            # Merkmal
                            if merkmal.name not in possible_volume_fields:
                                continue
                            # ist ein Merkmal in der Liste der volumenbeschreibden Feature,
                            # so wird der Input und der Output aus FCT-Attribute des Merkmals
                            # für das zugehörenden FCT-Member Spalte in die Dicts für Vol_in und Vol_out gespeichert
                            volume_input[remove_umlaut(merkmal.name)] = merkmal \
                                .fctattribute_set.filter(
                                membership=technology.id).first().input
                            volume_output[remove_umlaut(merkmal.name)] = merkmal. \
                                fctattribute_set.filter(
                                membership=technology.id).first().output

                       # calculate volumes
                       # Volumenberechnung in Abhängigkeit des Vorzeichens
                       # (is_positive True oder False)
                       # in diesem Punkt wird das Dict mit den In- und Outputs alles volumenbeschreibender
                       # Merkmale des Features zu einem Volumen berechnet
                       # hierbei wird unterschieden, ob es ein positives oder negatives Formelement ist (is_positive)
                        if feature.is_positive:
                            # wenn positive += addieren
                            # das dict vol_input für ein Feature der ausgewählten Spalte (FCT-Member) wird an die Klasse Volume
                            # übergeben. hier werden die Volumenfunktionen in Abhängigkeit des volume_types aufgerufen und berechnet
                            volume_input_num += Volume(
                                **volume_input).calculate_volume()
                            volume_output_num += Volume(
                                **volume_output).calculate_volume()

                        else:
                            # wenn nicht positive -= subtrahieren
                            # analog wie bei oben bei if is_positive
                            volume_input_num -= Volume(
                                **volume_input).calculate_volume()
                            volume_output_num -= Volume(
                                **volume_output).calculate_volume()

                    # die Ergebnisse für jedes Feature im gleichen FCT-Member werden auf vol_in_num und vol_out_num draufaddiert
                    # sodass nach dem letzte Feature das Gesamtvolumen für die Technologie (FCT-Member) in die Tabelle FCT-Member
                    # Abgespeichert werden kann
                    # pro feature in und output sind somit berechnet für eine FCT-Member-Spalte und haben ein
                    # positives oder negative Forzeichen (is_positive = True or False)

                    # ist eine Technologie (Spalte FCT-Member) durchlaufe wird die nächste Technologie durchiteriert.
                    # Damit nicht die Werte aus der vorherigen Technologie für vol_in_num und vol_out_num verwendet werden wird zu beginn
                    # dieser immer auf 0 gesetzt (siehe oben)

                    # an Technologie anhängen und in FCT-Membership abspeichern
                    # Input und Outputvolumen pro Technologie in FCT
                    technology.input_volume = volume_input_num
                    technology.output_volume = volume_output_num
                    technology.difference_volume = abs(
                        volume_output_num - volume_input_num)
                    technology.save()

        # consume errors and TODO: send messsage
        # Fehlermeldungen
        except AttributeError as err:
            log.exception(err)
            log.debug('//Es sind nicht alle In- und Outputs eingetragen//')

        except Exception as err:
            log.exception(err)
            log.debug('jeder andere error')

        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs) -> Optional[str]:
        return reverse('referencemodel-detail',
                       args=[str(self.kwargs.get('pk'))])


class CustomerItems(ListView):
    '''
    Zusammenfassung der Vergleichsbauteile
    '''
    template_name = 'main/item/item_list.html'
    model = Item

    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(reference=None)


class CustomerItem(DetailView):
    '''
    Ergebnisseite für Kunden
    Button für Bauteilvergleich
    Button um FCT-Tabelle zu erweitern falls neue Feature oder
    Merkmale hinzukommen
    Button für Änderungskosten
    '''
    template_name = 'main/item/item_detail.html'
    model = Item

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        item = Item.objects.get(pk=self.kwargs.get('pk'))
        cost_ecr = EcrCost.objects.filter(item=self.kwargs.get('pk')).last()
        ecr = Result.objects.filter(item=self.kwargs.get('pk')).last()
        ref = CostReference.objects.filter(
            reference=item.compare_reference).last()

        # Anzeigen des Ergebnisses der technologische Machbarkeit
        if ecr:
            fuzzy_possible = EcrFuzzy.objects.filter(
                result=ecr.pk, fuzzy="technologisch Machbar")

            fuzzy_maybe = EcrFuzzy.objects.filter(
                result=ecr.pk, fuzzy="technologische Machbarkeit mit Unsicherheiten")

            fuzzy_not = EcrFuzzy.objects.filter(
                result=ecr.pk, fuzzy="technologisch NICHT umsetzbar")
        else:
            fuzzy_possible = []
            fuzzy_maybe = []
            fuzzy_not = []

        context['ref'] = ref
        context['ecr'] = ecr
        context['cost_ecr'] = cost_ecr
        context['fuzzy_possible'] = fuzzy_possible
        context['fuzzy_maybe'] = fuzzy_maybe
        context['fuzzy_not'] = fuzzy_not

        # Referenzsystem
        system = item.compare_reference

        # Features des Referenzbauteils
        s = system.item.feature_set.all()

        # Features des Vergleichsbauteils
        i = item.feature_set.all()

        # Bauteilvergleich auf Featureebene
        s_name = set([si.name for si in s])
        i_name = set([si.name for si in i])
        duplicates = s_name & i_name
        only_s = s_name.difference(i_name)
        only_i = i_name.difference(s_name)

        if only_i or only_s:
            # true if ungleich
            print(only_s)
            print(only_i)

        # Bauteilvergleich auf Merkmalsebene
        # alle Feature die im Referenzbauteil als auch im Vergleichsbauteil
        # sind werden hinsichtlich ihrer Merkmale verglichen
        for name in duplicates:
            # Feature des Vergleichsbauteils mit dem betrachteten Namen in
            # Iteration
            f_i = i.filter(name=name).first()
            # alle Merkmale des Features des Vergleichsbauteils
            f_att_i = f_i.featureattribute_set.all()
            # Feature des Referenzbauteils mit dem betrachteten Namen in
            # der Iteration
            f_s = s.filter(name=name).first()
            # alle Merkmale des Features des Referenzbauteils
            f_att_s = f_s.featureattribute_set.all()

            fs_name = set([si.name for si in f_att_s])
            fi_name = set([si.name for si in f_att_i])
            duplicates = fs_name & fi_name

            only_fs_name = fs_name.difference(fi_name)
            # alle Merkmale des betrachteten Features die ausschließlich im
            # Vergleichsbauteil sind
            only_fi_name = fi_name.difference(fs_name)

            if only_fi_name or only_fs_name:
                # true if ungleich
                print('nur im vergleich')
                print(only_fi_name)
                print('nur im ref')
                print(only_fs_name)

        context['only_item_merkmale'] = only_fi_name
        context['only_item'] = only_i

        return context


class ItemAddFeatureToReference(RedirectView):
    '''
    FCT-Tabelle erweitern für Referenzbauteil falls Vergleichbauteil neue
    Features oder Merkmale besitzt
    '''

    def dispatch(self, request, *args, **kwargs):

        system = ReferenceSystem.objects.get(pk=self.kwargs.get('reference'))
        item = Item.objects.get(pk=self.kwargs.get('pk'))

        s = system.item.feature_set.all()
        i = item.feature_set.all()

        # neue Features des Vergleichsbauteils ans Referenzbauteil hängen
        s_name = set([si.name for si in s])
        i_name = set([si.name for si in i])
        duplicates = s_name & i_name
        only_i = i_name.difference(s_name)

        # Abspeicherung des Features zum Referenzbauteil
        for f in i:
            if f.name in only_i:
                new_attrs = f.featureattribute_set.all()
                f.add_to_fct = True
                f.pk = None
                f.item = system.item
                f.save()
                for attr in new_attrs:
                    attr.feature = f.pk
                    attr.pk = None
                    attr.save()

        # neue Merkmale bekannter Features des Vergleichsbauteils ans
        # Referenzbauteils hängen
        for name in duplicates:
            f_i = i.filter(name=name).first()
            f_att_i = f_i.featureattribute_set.all()
            f_s = s.filter(name=name).first()
            f_att_s = f_s.featureattribute_set.all()

            fs_name = set([si.name for si in f_att_s])
            fi_name = set([si.name for si in f_att_i])
            duplicates = fs_name & fi_name

            only_fi_name = fi_name.difference(fs_name)

            # Abspeicherung des Merkmals zum Features des Referenzbauteils
            for ofi in only_fi_name:
                new_att = f_att_i.filter(name=ofi).first()
                new_att.pk = None
                new_att.feature = f_s
                new_att.save()

        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url(self, *args: Any, **kwargs: Any) -> Optional[str]:
        return reverse('item-detail', args=[str(self.kwargs.get('pk'))])


class ItemUpload(FormView):
    '''
    Vergleichsbauteil hochladen
    '''
    form_class = ItemUploadForm
    template_name = 'main/item/features_upload.html'

    def get_success_url(self) -> str:
        # access model from form_valid to generate complete url
        return reverse('item-list')

    def form_valid(self, form: ItemUploadForm) -> HttpResponse:
        try:
            # create item for reference system
            item = Item(compare_reference=form.cleaned_data.get('compare_reference'),
                        name=form.cleaned_data.get('name'))

            # start transaction to save df to db as features and attrs
            with transaction.atomic():
                self.model = item.save()
                create_features_from_df(
                    form.process_dataframe, item)
                return super().form_valid(form)

        # raise exception if transaction failed
        except Exception as err:
            log.exception(err)
            form.add_error(
                None, error='Database INSERT failed => Transaction ROLLBACK')
            # return form with errors
            return super().form_invalid(form)


class CustomerItemDelete(DeleteView):
    template_name = 'main/item/delete.html'
    model = Item

    def get_success_url(self) -> str:
        return reverse('item-list')


class ItemFctBackwards(RedirectView):
    '''
    FCT-Tabelle automatisch füllen durch Anpassung der Zeilen durch die Differenz
    Volumen berechnen
    Volumenänderung bestimmen und Hauptzeiten, Standmenge und Losgrößen für Vergleichsbauteil berechnen
    Gewinnkostenberechnung für das Referenzbauteil und das Vergleichsbauteil
    '''

    def dispatch(self, request, *args, **kwargs):
        new_fct_table = {}

        # alle Feature des Referenzbauteils
        feature = Feature.objects.filter(
            item__reference_id=self.kwargs.get('reference'))

        # Alle FCT-Member des Referenzbauteils
        members = FctMembership.objects.filter(
            reference=self.kwargs.get('reference'))

        # Liste aller Merkmale die für die Berechnung der Volumen genutzt werden
        possible_volume_fields = ['laenge', 'breite', 'hoehe', 'tiefe', 'durchmesser',
                                  'breite_fuss', 'tiefe_fuss', 'winkel']
        # create dict template for fct table
        for f in feature:
            # Dictionary für jedes Feature worin der Volumentype (classifier),
            # das Formelement (is_positive) und das Volumen gespeichert werden
            new_fct_table[f.name] = {
                'volume_type': f.classifier.lower(),
                'positive': f.is_positive,
                'volumes': [],
                't_id': {}}
            # für jedes Feature werden die Merkmale (Featureattributes) einzeln betrachtet
            for m in f.featureattribute_set.all():
                # Umlaute werden entfernt
                m_name = remove_umlaut(m.name)
                # eine Liste wird instanziert für jedes Merkmal
                new_fct_table[f.name]['t_id'][m_name] = []
                new_fct_table[f.name][m_name] = []
                for c in m.fctattribute_set.all():
                    # Leistungsfähigkeitsprofile für das betrachtete Merkmal ins Dict abspeichern
                    new_fct_table[f.name]['t_id'][m_name].append(
                        c.tool_attribute)

                    if c.input == 0 and c.output != 0:
                        new_fct_table[f.name][m_name].append('Zero')
                    else:
                        new_fct_table[f.name][m_name].append(c.difference)
                # nach diesem Schritt ist die Liste new_fct_table mit den Differenzen aus der In- und
                # Outputs für ein Merkmal gefüllt
                # das heißt sind drei Technologien in der FCT so sind 3 Differenzen vorhanden
            # nach dieser Schleife ist das Dictionary (ein Feature) mit allen Merkmalen gefüllt
            # jedes Merkmal besitzt die Differenzen in der FCT-Tabelle
        # add target value to the end of value array
        ecr_fuzzy_models = []
        item = Item.objects.get(pk=self.kwargs.get('pk'))
        for f in item.feature_set.all():
            # feature des Vergleichsbauteils
            for m in f.featureattribute_set.all():
                # Merkmale eines Features des Vergleichsbauteils
                new_fct_table[f.name][remove_umlaut(m.name)].append(m.value)
                # an die Differenzen aus der Referenz FCT-Tabelle werden die Bauteilanforderungen des
                # Vergleichsbauteils angehängt (u.a. die veränderten Merkmalsanforderungen)
                # eine Liste mit den Merkmalsdifferenzen sowie der neuen Merkmalsanforderung
                for index, diff in reversed(list(enumerate(new_fct_table[f.name][remove_umlaut(m.name)]))):
                    # diese Liste wird von hinten nach vorne durchiteriert sowie mit jedem Durchlauf von 0 aufwärts mitgezählt
                    if m.value == diff:
                        # wenn der Eintrag = der Merkmalsanforderung des Vergleichbauteil
                        # ist, so wird die nächste
                        # Differenz genomme --> Startwert
                        continue
                    if isinstance(diff, str):
                        # Falls Differenz Sting = Zero
                        new_fct_table[f.name][remove_umlaut(
                            m.name)][index] = new_fct_table[f.name][remove_umlaut(
                                m.name)][index + 1] - new_fct_table[f.name][remove_umlaut(
                                    m.name)][index + 1]
                        # Zeilen für die technologische Überprüfung, wenn ein Input = 0 ist
                        # also ein Zero-Wert in der Zeile
                        new_value_diff_null = new_fct_table[f.name][remove_umlaut(
                            m.name)][index + 1] - new_fct_table[f.name][remove_umlaut(
                                m.name)][index + 1]
                        t_id_diff_null = new_fct_table[f.name]['t_id'][remove_umlaut(
                            m.name)][index]
                        # übergeben an die Funktion fuzzy_check() für die technologische Machbarkeit
                        tech_check = t_id_diff_null.fuzzy_check(new_value_diff_null + new_fct_table[f.name][remove_umlaut(
                            m.name)][index + 1])
                        # abspeichern in der Liste ecr_fuzzy_models
                        ecr_fuzzy_models.append(EcrFuzzy(f_name=f.name, m_name=m.name, tool_name=t_id_diff_null,
                                                         value=new_value_diff_null + new_fct_table[f.name][remove_umlaut(
                                                             m.name)][index + 1], fuzzy=tech_check))

                    else:
                        new_value = new_fct_table[f.name][remove_umlaut(
                            m.name)][index + 1] - diff
                        t_id = new_fct_table[f.name]['t_id'][remove_umlaut(
                            m.name)][index]

                        # technologische Bewertung und abspeicherung in der Liste ecr_fuzzy_models
                        tech_check = t_id.fuzzy_check(new_value + diff)
                        ecr_fuzzy_models.append(EcrFuzzy(f_name=f.name, m_name=m.name, tool_name=t_id,
                                                         value=new_value + diff, fuzzy=tech_check))

                        # für alle anderen Differenzen
                        new_fct_table[f.name][remove_umlaut(
                            m.name)][index] = new_fct_table[f.name][remove_umlaut(
                                m.name)][index + 1] - diff

        # save length
        # die Anzahl der Technologien in der Fertigungsprozessfolge
        length_diff = len(
            new_fct_table[f.name][remove_umlaut(f.featureattribute_set.first().name)])

        # calculate feature volume for every technology
        # an dieser Stelle wird das Volumen der In - und Outputs aller Features für
        # eine Technologie berechnet
        for f in new_fct_table:
            # dict wird instanziiert
            # es wird durch das oben instanziierte FCT-Dict durchiteriirt
            # ein Dict vol_dict wird neu instanziiert in das für jedes Feature der
            # Classifier abgespeichert wird
            vol_dict = {'volume_type': new_fct_table[f]['volume_type']}
            # diese Iteration wird genau so oft Durchlaufen, wie es Features/Zwischenergebniss
            #  im Vergleichsbauteil gibt
            for counter in range(length_diff):
                # jeder Eintage (value) eines Feature im Dict new_fct_table wird durchiteriert
                for m in new_fct_table[f]:

                    # wenn der Eintrag ein Merkmal in der Liste possible_volume_fields (s.o)
                    if m in possible_volume_fields:
                        # if isinstance(new_fct_table[f][m], list):
                        vol_dict[m] = new_fct_table[f][m][counter]
                        # else:
                        #     vol_dict[m] = new_fct_table[f][m]

                vol = Volume(**vol_dict).calculate_volume()
                new_fct_table[f]['volumes'].append(vol)

        # pprint.pprint(new_fct_table)
        # calculate volume per input for every technology
        # dictionary mit so vielen Eintragen wie Technologien in Fertigungsprozessfolge sind
        item_vols = {}
        for i, m in enumerate(members):
            item_vols[i] = []

        # iterieren durch die Technologien FCT-membership
        for index, member in enumerate(members):
            # instanziiren leere Liste
            member_volumes = []
            # iterrieren für jedes Feature die new fct tabele durch
            for f in new_fct_table:
                if new_fct_table[f]['positive']:
                    member_volumes.append(
                        new_fct_table[f]['volumes'][index + 1] - new_fct_table[f]['volumes'][index])
                else:
                    member_volumes.append(
                        - (new_fct_table[f]['volumes'][index + 1] - new_fct_table[f]['volumes'][index]))

            item_vols[index].append(sum(member_volumes))
            # berechung der outputvolumen
            # erst in der letzte iterationsschleife
            if index == len(members) - 1:
                item_vols[index + 1] = []
                item_vols[index + 1].append(member.output_volume)
        pprint.pprint(new_fct_table)
        print('------------item_vol-----------')
        print(item_vols)
        # cost Referenszbauteil
        # in diesem Abschnitt werden die Kostenberechnungen für das Referenzabauteil durchgeführt
        cost_overview = {
            "cost_fct_column": {},
            "cost_general": {}
        }

        cost_parameter = cost_overview['cost_fct_column']
        cost_fpf = cost_overview['cost_general']

        system = ReferenceSystem.objects.get(pk=self.kwargs.get('reference'))
        hz = system.item.halbzeug_set.first()
        hz: Halbzeug
        print('Halbezug1111111')
        print(hz.pk)

        # für jede Technologie der Fertigungsprozessfolge werden die KOSTEN berechnet
        for ref in members:
            '''
            Alle Kosten die bestimmt werden können ohne Npf_gesamt der Fertigungsprozessfolge
            '''
            tool = ref.tool
            machine = ref.tool.technology

            cost_parameter[tool.name] = {}

            cost_parameter[tool.name]['mittlere_leistung'] = machine.mittlere_leistung
            cost_parameter[tool.name]['betrachtungszeitraum'] = system.betrachtungszeitraum
            cost_parameter[tool.name]['strompreis'] = machine.strompreis
            cost_parameter[tool.name]['laufzeit_jahr'] = system.laufzeit_jahr

            cost_parameter[tool.name]['tn'] = (tool.ruestzeit / ref.losgroesse) + \
                (tool.werkzeugwechselzeit / ref.standmenge) +  \
                tool.werkstueckwechselzeit
            cost_parameter[tool.name]['tg'] = ref.hauptzeit + \
                cost_parameter[tool.name]['tn']
            cost_parameter[tool.name]['te'] = cost_parameter[tool.name]['tg'] + \
                tool.verteilzeit + tool.erholungszeit

            cost_parameter[tool.name]['npf'] = (
                system.laufzeit_jahr * system.betrachtungszeitraum) / (cost_parameter[tool.name]['te'] / (60 * 60))

            cost_parameter[tool.name]['betriebsstoffkosten'] = tool.betriebsstoffkosten
            cost_parameter[tool.name]['restfertigungsgemeinkosten'] = machine.restfertigungsgemeinkosten
            cost_parameter[tool.name]['Ka'] = (
                machine.anschaffungswert - machine.verkaufserlös) / machine.abschreibungsdauer
            cost_parameter[tool.name]['Kr'] = machine.quadratmeterpreis * \
                machine.platzbedarf
            cost_parameter[tool.name]['Ki'] = machine.anschaffungswert * \
                machine.instandhaltungsfaktor
            cost_parameter[tool.name]['Kz'] = 0.5 * \
                (machine.anschaffungswert + machine.verkaufserlös) * machine.zinsatz
            cost_parameter[tool.name]['Kw'] = tool.werkzeugpreis / \
                ref.standmenge
            cost_parameter[tool.name]['Kl'] = machine.stundenlohn * (1 + system.lohnnebenkostenanteil) * (
                cost_parameter[tool.name]['te'] / (60 * 60)) * machine.bediehnverhaeltnis * machine.fertigungsmittelanzahl

        cost_fpf['npf_max'] = min([v['npf']
                                   for k, v in cost_parameter.items()])

        # Berechnung aller Kostenbestandteile die Abhängig von der Stückzahl sind
        for name in cost_parameter:
            cost_parameter[name]['npa'] = cost_overview['cost_general']['npf_max'] / \
                cost_parameter[name]['betrachtungszeitraum']
            cost_parameter[name]['Ke'] = cost_parameter[name]['mittlere_leistung'] * (cost_parameter[name]['te'] / (
                60 * 60)) * cost_parameter[name]['npa'] * cost_parameter[name]['strompreis']

            cost_parameter[name]['Kmh'] = (cost_parameter[name]['Ka'] + cost_parameter[name]['Kr'] + cost_parameter[name]
                                           ['Ki'] + cost_parameter[name]['Ke'] + cost_parameter[name]['Kz']) / cost_parameter[name]['laufzeit_jahr']
            cost_parameter[name]['Km'] = cost_parameter[name]['Kmh'] * \
                (cost_parameter[name]['te'] / (60 * 60))

            cost_parameter[name]['Kf'] = cost_parameter[name]['Kl'] + \
                cost_parameter[name]['Km'] + \
                cost_parameter[name]['Kw'] + \
                cost_parameter[name]['restfertigungsgemeinkosten']
            cost_parameter[name]['Khb'] = cost_parameter[name]['betriebsstoffkosten'] / \
                cost_overview['cost_general']['npf_max']

        cost_fpf['Kf_fpf'] = sum([v['Kf'] for k, v in cost_parameter.items()])

        cost_fpf['Krm'] = hz.volume * system.dichte * \
            system.kilopreis * pow(10, -3)
        cost_fpf['Kma'] = cost_fpf['Krm'] + \
            sum([v['Khb'] for k, v in cost_parameter.items()])

        cost_fpf['Kh'] = cost_fpf['Kf_fpf'] + cost_fpf['Kma']
        cost_fpf['Kh_npf'] = cost_fpf['Kh'] * cost_fpf['npf_max']

        cost_fpf['Gpf'] = system.produktpreis * \
            cost_fpf['npf_max'] - cost_fpf['Kh_npf']

        cost_fpf['reference'] = system
        res = system.costreference_set.first()
        CostReference(**cost_fpf).save()

        print('------------Kosten Referenzbauteil-------------')
        pprint.pprint(cost_overview)

        # mit diesem Schritt wird immer nur einmal ein Ergebnis gespeichert
        # der obere Schritt speichert immer wieder einen neuen Datensatz in die Tabelle CostReference
        '''
        if not res:
            Result(**cost_fpf).save()
        else:
            print('ergebnis schon vorhanden')
        '''

        # Bestimmung der bauteilabhängigen Parameter Hauptzei, Standmenge und Losgröße
        # in Abhängigkeit der Änderungsvolumina der Technoloien für Referenzbauteil und Vergelichsbauteil
        hauptzeit_item = []
        standmenge_item = []
        losgroesse_item = []

        for index, ref in enumerate(members):
            vol_ref = ref.difference_volume
            vol_item = item_vols[index][0]

            relation = abs(vol_item / vol_ref)

            th_ref = ref.hauptzeit
            nwz_ref = ref.standmenge
            nl_ref = ref.losgroesse

            hauptzeit_item.append(relation * th_ref)
            standmenge_item.append(nwz_ref * (1 / relation))
            losgroesse_item.append(nl_ref * (1 / relation))

        # Berechnung der KOSTEN des Vergleichsbauteil
        cost_overview = {
            "cost_fct_column": {},
            "cost_general": {}
        }

        cost_parameter = cost_overview['cost_fct_column']
        cost_fpf = cost_overview['cost_general']

        refs = system.fctmembership_set.all()
        hz = item.halbzeug_set.first()

        for index, ref in enumerate(members):
            '''
            Alle Kosten die bestimmt werden können ohne Npf_gesamt der Fertigungsprozessfolge
            '''
            tool = ref.tool
            machine = Technology.objects.get(pk=tool.technology.id)

            cost_parameter[tool.name] = {}

            cost_parameter[tool.name]['mittlere_leistung'] = machine.mittlere_leistung
            cost_parameter[tool.name]['betrachtungszeitraum'] = system.betrachtungszeitraum
            cost_parameter[tool.name]['strompreis'] = machine.strompreis
            cost_parameter[tool.name]['laufzeit_jahr'] = system.laufzeit_jahr
            cost_parameter[tool.name]['tn'] = (
                tool.ruestzeit / losgroesse_item[index]) + (tool.werkzeugwechselzeit / standmenge_item[index]) + tool.werkstueckwechselzeit
            cost_parameter[tool.name]['tg'] = hauptzeit_item[index] + \
                cost_parameter[tool.name]['tn']
            cost_parameter[tool.name]['te'] = cost_parameter[tool.name]['tg'] + \
                tool.verteilzeit + tool.erholungszeit

            cost_parameter[tool.name]['npf'] = (
                system.laufzeit_jahr * system.betrachtungszeitraum) / (cost_parameter[tool.name]['te'] / (60 * 60))

            cost_parameter[tool.name]['betriebsstoffkosten'] = tool.betriebsstoffkosten
            cost_parameter[tool.name]['restfertigungsgemeinkosten'] = machine.restfertigungsgemeinkosten
            cost_parameter[tool.name]['Ka'] = (
                machine.anschaffungswert - machine.verkaufserlös) / machine.abschreibungsdauer
            cost_parameter[tool.name]['Kr'] = machine.quadratmeterpreis * \
                machine.platzbedarf
            cost_parameter[tool.name]['Ki'] = machine.anschaffungswert * \
                machine.instandhaltungsfaktor
            cost_parameter[tool.name]['Kz'] = 0.5 * \
                (machine.anschaffungswert + machine.verkaufserlös) * machine.zinsatz
            cost_parameter[tool.name]['Kw'] = tool.werkzeugpreis / \
                standmenge_item[index]
            cost_parameter[tool.name]['Kl'] = machine.stundenlohn * (1 + system.lohnnebenkostenanteil) * (
                cost_parameter[tool.name]['te'] / (60 * 60)) * machine.bediehnverhaeltnis * machine.fertigungsmittelanzahl

        cost_fpf['npf_max'] = min([v['npf']
                                   for k, v in cost_parameter.items()])

        for name in cost_parameter:

            cost_parameter[name]['npa'] = cost_overview['cost_general']['npf_max'] / \
                cost_parameter[name]['betrachtungszeitraum']
            cost_parameter[name]['Ke'] = cost_parameter[name]['mittlere_leistung'] * (cost_parameter[name]['te'] / (
                60 * 60)) * cost_parameter[name]['npa'] * cost_parameter[name]['strompreis']

            cost_parameter[name]['Kmh'] = (cost_parameter[name]['Ka'] + cost_parameter[name]['Kr'] + cost_parameter[name]
                                           ['Ki'] + cost_parameter[name]['Ke'] + cost_parameter[name]['Kz']) / cost_parameter[name]['laufzeit_jahr']
            cost_parameter[name]['Km'] = cost_parameter[name]['Kmh'] * \
                (cost_parameter[name]['te'] / (60 * 60))

            cost_parameter[name]['Kf'] = cost_parameter[name]['Kl'] + \
                cost_parameter[name]['Km'] + \
                cost_parameter[name]['Kw'] + \
                cost_parameter[name]['restfertigungsgemeinkosten']
            cost_parameter[name]['Khb'] = cost_parameter[name]['betriebsstoffkosten'] / \
                cost_overview['cost_general']['npf_max']

        cost_fpf['Kf_fpf'] = sum([v['Kf'] for k, v in cost_parameter.items()])

        cost_fpf['Krm'] = hz.volume * system.dichte * \
            system.kilopreis * pow(10, -3)
        cost_fpf['Kma'] = cost_fpf['Krm'] + \
            sum([v['Khb'] for k, v in cost_parameter.items()])

        cost_fpf['Kh'] = cost_fpf['Kf_fpf'] + cost_fpf['Kma']
        cost_fpf['Kh_npf'] = cost_fpf['Kh'] * cost_fpf['npf_max']

        cost_fpf['Gpf'] = system.produktpreis * \
            cost_fpf['npf_max'] - cost_fpf['Kh_npf']

        cost_fpf['item'] = item
        res = item.result_set.first()
        result = Result(**cost_fpf)
        result.save()
        print('------------Kosten Vergleichsbauteil-------------')
        pprint.pprint(cost_overview)
        # abspeichern der Ergebnisse der technologischen Machbarkeit für das Vergleichsbauteil
        for ecrfuzzy in ecr_fuzzy_models:
            ecrfuzzy.result = result
            ecrfuzzy.save()
        # if not res:
        #     Result(**cost_fpf).save()
        # else:
        #     print('ergebnis schon vorhanden')

        # Änderungskostenbestimung
        ref_cost = CostReference.objects.filter(reference=system.id).last()

        gewinn_ecr = ref_cost.Gpf - cost_fpf['Gpf']
        npf_ecr = cost_fpf['npf_max'] - ref_cost.npf_max
        kh_ecr = cost_fpf['Kh'] - ref_cost.Kh
        kh_npf_ecr = cost_fpf['Kh_npf'] - ref_cost.Kh_npf
        kma_ecr = cost_fpf['Kma'] - ref_cost.Kma
        krm_ecr = cost_fpf['Krm'] - ref_cost.Krm

        ecrcost = EcrCost(G=gewinn_ecr, Kh=kh_npf_ecr,
                          npf=npf_ecr, Kma=kma_ecr, Krm=krm_ecr, item=item)
        ecrcost.save()

        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url(self, *args: Any, **kwargs: Any) -> str:
        return reverse('item-detail', args=[str(self.kwargs.get('pk'))])


# nur wenn man sich die Daten nicht anzeigen lassen will
# oder man schickt die Daten per django message
# oder man speicher daten im model
class ItemComparison(RedirectView):
    '''
    Bauteilvergleich
    '''

    def dispatch(self, request, *args, **kwargs):
        system = ReferenceSystem.objects.get(pk=self.kwargs.get('reference'))
        item = Item.objects.get(pk=self.kwargs.get('pk'))

        # feature arrays
        s = system.item.feature_set.all()
        i = item.feature_set.all()

        # python zip // simultane for schleife

        s_name = set([si.name for si in s])
        i_name = set([si.name for si in i])
        duplicates = s_name & i_name
        only_s = s_name.difference(i_name)
        only_i = i_name.difference(s_name)

        member_only_s = len(only_s)
        member_only_i = len(only_i)

        if only_i or only_s:
            # true if ungleich
            # exit point
            print('fdf')
        print(member_only_i)
        print(member_only_s)
        # else:
        # tue das wenn alles richtig ist

        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url(self, *args: Any, **kwargs: Any) -> Optional[str]:
        return reverse('item-detail', args=[str(self.kwargs.get('pk'))])
