import math
import decimal
from typing import List
from django.db import models
from django.db.models.base import Model
from django.db.models.fields import BooleanField, CharField,  FloatField, PositiveIntegerField
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.core.exceptions import ValidationError
from django.urls import reverse

'''
Tabelle für die Technologien
Unterteilung in: 
    Technology, Tool und ToolAttriute
'''


class Technology(models.Model):
    # Maschine
    name = models.CharField(max_length=255)

    # wirtschaftliche Parameter
    restfertigungsgemeinkosten = FloatField()
    anschaffungswert = FloatField()
    verkaufserlös = FloatField()
    abschreibungsdauer = FloatField()
    platzbedarf = FloatField()
    mittlere_leistung = FloatField()
    instandhaltungsfaktor = FloatField()
    quadratmeterpreis = FloatField()
    strompreis = FloatField()
    zinsatz = FloatField()
    stundenlohn = FloatField()
    fertigungsmittelanzahl = FloatField()
    bediehnverhaeltnis = FloatField()

    def get_absolute_url(self):
        return reverse('technology-detail', args=[str(self.id)])

    def __str__(self):
        return f"{self.name}"


class Tool(models.Model):
    # Werkzeug
    name = CharField(max_length=255)
    technology = ForeignKey(Technology, on_delete=models.CASCADE)

    # wirtschaftliche Parameter
    verteilzeit = FloatField()
    ruestzeit = FloatField()
    erholungszeit = FloatField()
    werkzeugwechselzeit = FloatField()
    werkstueckwechselzeit = FloatField()
    betriebsstoffkosten = FloatField()
    werkzeugpreis = FloatField()

    def get_absolute_url(self):
        return reverse('technology-detail', args=[str(self.technology.id)])

    def __str__(self):
        return f"{self.technology.name.upper()} {self.name.upper()}"


class ToolAttribute(models.Model):
    # Leistungsfähigkeitsprofil
    name = CharField(max_length=255)
    tool = ForeignKey(Tool, on_delete=models.CASCADE)
    a = FloatField()
    b = FloatField()
    c = FloatField()
    d = FloatField()
    einheit = CharField(max_length=255, null=True)

    def clean(self) -> None:
        self.clean_fields(exclude=['tool'])

        # validate if values are ascending or descending
        # Fehler falls Fuzzy springt (bsp. 1, 5, 3, 6)
        if not (self.a <= self.b <= self.c <= self.d or
                self.a >= self.b >= self.c >= self.d):
            raise ValidationError('''A,B,C und D muessen in ab- oder
             aufsteigender Reihenfolge initialisiert werden''')

    def fuzzy_check(self, value: float) -> str:
        # simple fuzzy check

        # range from b to c -> Is possible
        if self.b <= value <= self.c:
            return 'technologisch Machbar'

        # range from a to d -> Is experimental
        elif self.a <= value <= self.d:
            return 'technologische Machbarkeit mit Unsicherheiten'

        # if value out of bounds -> not possible
        else:
            return 'technologisch NICHT umsetzbar'

    def get_absolute_url(self):
        return reverse('technology-detail', args=[str(self.tool.technology.id)])

    def __str__(self):
        return f"{self.name} {self.tool.name}"


'''
Referenzsystem, Bauteil und Volumentabellen
ReferenzSystem, Item, Feature, FeatureAttribute, FeatureAttributeText, Volume,
Halbzeug
'''


class ReferenceSystem(models.Model):
    # Referenzsystem mit Referenzbauteil
    name = CharField(max_length=255)
    technologies = ManyToManyField(
        Tool, through='FctMembership')

    # wirtschaftliche Parameter
    laufzeit_jahr = FloatField()
    betrachtungszeitraum = FloatField()
    produktpreis = FloatField()
    lohnnebenkostenanteil = FloatField()
    dichte = FloatField()
    kilopreis = FloatField()

    def get_absolute_url(self):
        return reverse('referencemodel-detail', args=[str(self.id)])

    def __str__(self):
        return f"{self.name}"


class Item(models.Model):
    # Bauteile
    name = CharField(max_length=255)
    # Bauteil hat Referenz zum Referenzsystem
    # --> Bauteil ist Referenzsystem
    reference = models.OneToOneField(
        ReferenceSystem,
        on_delete=models.CASCADE,
        null=True,
        blank=True)
    # Bauteil hat Abhängigkeit zum Referenzsystem
    # --> Bauteil ist Vergleichssystem
    compare_reference = ForeignKey(
        ReferenceSystem,
        related_name='compare_reference',
        on_delete=models.CASCADE,
        null=True,
        blank=True)

    def get_absolute_url(self):
        return reverse('item-detail', args=[str(self.id)])

    def __str__(self):
        return f"Bauteil: {self.name}"


class Feature(models.Model):
    # Feature Name, Klassifier, Bauteil
    name = models.CharField(max_length=255)
    classifier = models.CharField(max_length=255)
    item = ForeignKey(Item, on_delete=models.CASCADE)
    # is_positive gibt an, ob bei der Volumenberechnung einer
    # Technologiespalte in der das Volumen abgezogen oder addiert wird
    is_positive = BooleanField()
    #
    add_to_fct = BooleanField(null=True, blank=True)

    def __str__(self):
        return f"{self.id} {self.name} {self.classifier} "


class FeatureAttribute(models.Model):
    # Merkmale numerisch
    name = CharField(max_length=255)
    value = FloatField()
    feature = ForeignKey(Feature, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id} {self.name} {self.value}"


class FeatureAttributeText(models.Model):
    # Merkmale text
    name = CharField(max_length=255)
    value = CharField(max_length=255, null=True, blank=True)
    feature = ForeignKey(Feature, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id} {self.name} {self.value}"


class Volume(models.Model):
    # Volumenabspeicherung der Feature in Abhängigkeit
    # der volumenbeschreibenden Merkmale
    # benötigt für die Berechnung der In- und Outputvolumen
    PRISMATISCH = 'prismatisch'
    ROTATIONSSYMMETRISCH = 'rotationssymmetrisch'
    INITIAL_FEATURE = 'initial_feature'
    ABSATZ = 'absatz'
    T_NUT = 't-nut'
    NUT = 'nut'
    TASCHE = 'tasche'
    PASSFEDER = 'passfeder'
    BOHRUNG = 'bohrung'
    ZYLINDERSENKUNG = 'zylindersenkung'
    KEGELSENKUNG = 'kegelsenkung'
    WELLENABSATZ_ZYLINDRISCH = 'wellenabsatz-zylindrisch'
    WELLENABSATZ_KONISCH = 'wellenabsatz-konisch'
    INNENGEWINDE = 'innengewinde'
    VOLUME_FORM = [
        (PRISMATISCH, 'Prismatisch'),
        (ROTATIONSSYMMETRISCH, 'Rotationssymmetrisch'),
        (INITIAL_FEATURE, 'Initial Feature'),
        (ABSATZ, 'Absatz'),
        (T_NUT, 'T-Nut'),
        (NUT, 'Nut'),
        (TASCHE, 'Tasche'),
        (PASSFEDER, 'Passfeder'),
        (BOHRUNG, 'Bohrung'),
        (ZYLINDERSENKUNG, 'Zylindersenkung'),
        (KEGELSENKUNG, 'Kegelsenkung'),
        (WELLENABSATZ_ZYLINDRISCH, 'Wellenabsatz-Zylindrisch'),
        (WELLENABSATZ_KONISCH, 'Wellenabsatz-Konisch'),
        (INNENGEWINDE, 'Innengewinde')
    ]

    # alle vorkommenden volumenbesschreibenden Merkmale für alle
    # betrachteten Features
    volume_type = CharField(max_length=255, choices=VOLUME_FORM)
    hoehe = FloatField(null=True, blank=True)
    breite = FloatField(null=True, blank=True)
    laenge = FloatField(null=True, blank=True)
    tiefe = FloatField(null=True, blank=True)
    durchmesser = FloatField(null=True, blank=True)
    breite_fuss = FloatField(null=True, blank=True)
    tiefe_fuss = FloatField(null=True, blank=True)
    winkel = FloatField(null=True, blank=True)
    volume = FloatField(null=True, blank=True)
    # one to many nicht erforderlich
    feature = ForeignKey(Feature, on_delete=models.CASCADE, null=True)

    def validating_attributes(self, attributes: List[decimal.Decimal]) -> None:
        # generic validation
        if None in attributes:
            raise ValidationError(
                f''' Typ "{self.volume_type}" hat folgende Werte erhalten:
                {", ".join(map(str,attributes))}''')

    # Zuordnung in Abhängigkeit der Classifier welche Merkmale benötigt werden
    # Abhängig vom Feature
    def clean(self) -> None:
        self.clean_fields()
        # bei Absatz und Prismatisch (Initialfeature/Kontur)
        if self.volume_type in [self.PRISMATISCH, self.ABSATZ]:
            self.validating_attributes([self.hoehe, self.breite, self.laenge])

        # bei Wellenabsatz, Bohrung und Rotationssymme (Initialfeature/Kontur)
        elif self.volume_type in [self.ROTATIONSSYMMETRISCH,
                                  self.WELLENABSATZ_ZYLINDRISCH, self.BOHRUNG]:
            self.validating_attributes([self.durchmesser, self.laenge])

        # T-Nut
        elif self.volume_type == self.T_NUT:
            self.validating_attributes([self.breite, self.laenge, self.tiefe,
                                        self.breite_fuss, self.tiefe_fuss])

        # Nut, Tasche, Passfeder
        elif self.volume_type in [self.NUT, self.TASCHE, self.PASSFEDER]:
            self.validating_attributes([self.breite, self.laenge, self.tiefe])

        # Zylindersenkung Kegelsenkung
        elif self.volume_type in [self.ZYLINDERSENKUNG, self.KEGELSENKUNG]:
            self.validating_attributes([self.durchmesser, self.tiefe])

        # konischer Wellenabsatz
        elif self.volume_type == self.WELLENABSATZ_KONISCH:
            self.validating_attributes(
                [self.durchmesser, self.laenge, self.winkel])
        # Innengewinde (in diesem Fall nicht berechnet)
        elif self.volume_type == self.INNENGEWINDE:
            pass

        # Falls Feature keins dieser ausgewählten ist
        # --> Feature hat unbekanntes Volumen, keine Berücksichtigung in Berechnung
        else:
            assert False, f'In "clean()": Unbekannts Volumen "{self.volume_type}"'

    # Berechnungsformeln in Abhängigkeit der Zuordnung
    def calculate_volume(self) -> float:
        # Initialfeature prismatisch und Absatz
        if self.volume_type in [self.PRISMATISCH, self.ABSATZ]:
            return self.laenge * self.breite * self.hoehe
        # Initialfeature rotationssymmetrisch, Bohrung und zyl.Wellenabsatz
        elif self.volume_type in [self.ROTATIONSSYMMETRISCH,
                                  self.BOHRUNG, self.WELLENABSATZ_ZYLINDRISCH]:
            return math.pi * pow(self.durchmesser/2, 2) * self.laenge
        # T-Nut
        elif self.volume_type == self.T_NUT:
            return self.laenge * (self.tiefe * self.breite +
                                  self.breite_fuss * self.tiefe_fuss)
        # Nut, Tasche und Passfeder
        elif self.volume_type in [self.NUT, self.TASCHE, self.PASSFEDER]:
            return self.breite * self.laenge * self.tiefe
        # Zylindersenkung
        elif self.volume_type == self.ZYLINDERSENKUNG:
            return math.pi * pow(self.durchmesser, 2) * self.tiefe
        # Kegelsenkung
        elif self.volume_type == self.KEGELSENKUNG:
            return (math.pi * pow(self.durchmesser, 2) * self.tiefe) / 3
        # Wellenabsatz konisch
        elif self.volume_type == self.WELLENABSATZ_KONISCH:
            d2 = self.durchmesser - math.tan(self.winkel) * self.laenge
            laenge_kegel = self.durchmesser / math.tan(self.winkel)
            l2 = laenge_kegel - self.laenge
            return (math.pi * pow((self.durchmesser / 2), 2) * self.laenge
                    - pow((d2/2), 2) * l2) / 3
        # innengewinde
        elif self.volume_type == self.INNENGEWINDE:
            # no impact on volume
            return 0

        else:
            assert False, f'''In "calculate_volume()": Unbekanntes Volumen
             "{self.volume_type}"'''

    # in Datenbank abspeichern
    def save(self, *args, **kwargs) -> None:
        self.volume = self.calculate_volume()
        super(Volume, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('referencemodel-detail', args=[str(self.feature.id)])

    def __str__(self):
        return f"{self.pk} {self.volume_type} {self.volume}"


class Halbzeug(models.Model):
    # Halbzeug für die Berechnung des Rohmaterialvolumens
    item = ForeignKey(Item, on_delete=models.CASCADE)
    hoehe = FloatField(null=True)
    laenge = FloatField(null=True)
    breite = FloatField(null=True)
    durchmesser = FloatField(null=True)
    volume = FloatField(null=True)

    def calculate_volume(self):
        # TODO: add rotationssymmetrisch to calculation
        # TODO: handle exception if volume calculation fails
        # Volumenberechnung prismatisches Halbzeug
        vol_model = Volume(
            volume_type='prismatisch',
            hoehe=self.hoehe,
            breite=self.breite,
            laenge=self.laenge
        ).calculate_volume()
        self.volume = vol_model

    # in Datenbank abspeichern
    def save(self, *args, **kwargs) -> None:
        self.calculate_volume()
        super(Halbzeug, self).save(*args, **kwargs)


'''
FCT-Tabelle
FctMembership und FctAttribute
'''


class FctMembership(models.Model):
    '''
    Technologie und Änderungsvolumina sowie
    bauteilabhängigen Fertigungsprozessparameter
    '''
    reference = ForeignKey(ReferenceSystem, on_delete=models.CASCADE)
    tool = ForeignKey(Tool, on_delete=models.CASCADE)
    position = PositiveIntegerField(default=1)
    input_volume = FloatField(null=True)
    output_volume = FloatField(null=True)
    difference_volume = FloatField(null=True)

    # wirtschaftliche Parameter
    hauptzeit = FloatField()
    standmenge = FloatField()
    losgroesse = FloatField()

    # set position of new technology_member
    def set_position(self) -> None:
        all_technologies = FctMembership.objects.filter(
            reference=self.reference)
        self.position = len(all_technologies) + 1

    def delete_self_and_above_position(self) -> None:
        FctMembership.objects.filter(
            position__gte=self.position, reference=self.reference).delete()


class FctAttribute(models.Model):
    '''
    Tabelle für das Abspeichern der Zwischenzustände und der technologischen 
    Machbarkeit
    '''
    POSSIBLE = 'technologisch machbar'
    EXPERIMENTAL = 'technologische Machbarkeit mit Unsicherheiten'
    NOT_POSSIBLE = 'technologisch NICHT umsetzbar'
    ALL_OUTCOMES = [
        (POSSIBLE, 'Machbar'),
        (EXPERIMENTAL, 'technologische Machbarkeit mit Unsicherheiten'),
        (POSSIBLE, 'technologisch NICHT umsetzbar'),
    ]
    input = FloatField()
    output = FloatField()
    difference = FloatField()
    input_possible = CharField(
        max_length=255, choices=ALL_OUTCOMES)
    output_possible = CharField(
        max_length=255, choices=ALL_OUTCOMES)
    membership = ForeignKey(
        FctMembership, on_delete=models.CASCADE)
    tool_attribute = ForeignKey(
        ToolAttribute, on_delete=models.CASCADE)
    feature_attribute = ForeignKey(
        FeatureAttribute, on_delete=models.CASCADE)

    def calculate_difference_and_fuzzy_logic(self):
        # simple difference calculation
        self.difference = self.output - self.input

        # start fuzzy-logic
        if self.difference != 0:

            # check input and set value accordingly
            # delte tool_attribute
            self.input_possible = self.tool_attribute.fuzzy_check(self.input)

            # check output and set value accordingly
            self.output_possible = self.tool_attribute.fuzzy_check(self.output)

        else:
            # if "no difference" set in- and outputs as "possible"
            self.input_possible = self.POSSIBLE
            self.output_possible = self.POSSIBLE

    def save(self, *args, **kwargs) -> None:

        # before we save the model get difference and fuzzy results
        self.calculate_difference_and_fuzzy_logic()

        super(FctAttribute, self).save(*args, **kwargs)


class CostReference(models.Model):
    '''
    Ergebniss der Fertigungskosten Referenzbauteil
    '''
    Gpf = FloatField()
    Kf_fpf = FloatField()
    Kh = FloatField()
    Kh_npf = FloatField()
    Kma = FloatField()
    Krm = FloatField()
    npf_max = FloatField()
    reference = ForeignKey(ReferenceSystem, on_delete=models.CASCADE)


class Result(models.Model):
    '''
    Ergebniss der Fertigungskosten Vergleichsbauteil
    '''
    Gpf = FloatField()
    Kf_fpf = FloatField()
    Kh = FloatField()
    Kh_npf = FloatField()
    Kma = FloatField()
    Krm = FloatField()
    npf_max = FloatField()
    item = ForeignKey(Item, on_delete=models.CASCADE)


class EcrCost(models.Model):
    '''
    Ergebnis der Änderungskostenbestimmung
    '''
    G = FloatField()
    Kh = FloatField()
    npf = FloatField()
    Kma = FloatField()
    Krm = FloatField()
    item = ForeignKey(Item, on_delete=models.CASCADE)


class EcrFuzzy(models.Model):
    '''
    Abspeicherung des Ergebnisses der technologischen Machbarkeitsprüfung
    für das Vergleichsbauteil
    '''
    f_name = CharField(max_length=255)
    m_name = CharField(max_length=255)
    tool_name = CharField(max_length=255)
    value = FloatField()
    fuzzy = CharField(max_length=255)
    result = ForeignKey(Result, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.f_name} {self.m_name} {self.value} {self.tool_name}"
