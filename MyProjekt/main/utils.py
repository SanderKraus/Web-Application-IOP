from typing import Dict, List
from django.core.exceptions import ValidationError
import pandas as pd
from .models import (FeatureAttribute, Item, Feature, Volume,
                     FeatureAttributeText, Halbzeug)


def processing_excel_file_buffer(form, xlsx_buffer) -> pd.DataFrame:
    '''
    Nach dem hochladen der Ecxel:
    in DataFrame umwandeln 
    Initialfeature an DataFrame anhängen
    Datan-Typen zuweisen und Einheiten sowie Komma mit Punkt ersetzen
    Spaltennamen kürzen, sodass nur noch Merkmalsname bleibt
    alle leeren Zeilen und Spalten werden verworfen
    '''
    df = pd.read_excel(xlsx_buffer, header=1)

    # append initialfeature an FCT-Tabelle anhängen
    # TODO: add non-prismatic check and if-clause
    if form.cleaned_data.get('prismatic'):
        df = df.append({
            'Name': 'kontur',
            'Classifier': 'prismatisch',
            'Länge : length[millimetre]': f"{form.cleaned_data.get('laenge')} mm",
            'Höhe : length[millimetre]': f"{form.cleaned_data.get('hoehe')} mm",
            'Breite : length[millimetre]': f"{form.cleaned_data.get('breite')} mm",
        }, ignore_index=True)
    else:
        df = df.append({
            'Name': 'kontur',
            'Classifier': 'rotationssymmetrisch',
            'Länge : length[millimetre]': f"{form.cleaned_data.get('laenge')} mm",
            'Durchmesser : length[millimetre]': f"{form.cleaned_data.get('durchmesser')} mm",
        }, ignore_index=True)
    # Datentypen zuweisen
    for col in df.columns.tolist():
        if 'Boolean' in col:
            df[col] = df[col].astype('bool')
        elif 'length' in col:
            df[col] = df[col].apply(str).str.replace('mm', '')
            df[col] = df[col].str.replace(',', '.')
            df[col] = df[col].astype('float64')
        else:
            df[col] = df[col].astype('string')
    # Spaltenname vereinfachen
    df.columns = [col.split(':')[0].strip().lower()
                  for col in df.columns.tolist()]
    # Alle NaN-Spalten und NaN-Zeilen droppen
    df = df.dropna(how='all')
    df = df.dropna(axis=1, how='all')
    return df


def create_features_from_df(df: pd.DataFrame, model: Item) -> None:
    for index, row in df.iterrows():

        # create feature
        if row['name'] == 'halbzeug_prismatisch':
            # hier Halbzeug abspeichern
            # TODO: unterscheidung prismatisch
            # TODO: validate that only one halbzeug is created
            Halbzeug(
                item=model,
                laenge=row['länge'],
                hoehe=row['höhe'],
                breite=row['breite'],
            ).save()
        elif row['name'] == 'halbzeug_rotatorisch':
            Halbzeug(
                item=model,
                laenge=row['länge'],
                durchmesser=row['durchmesser'],
            ).save()
        else:
            # hier Feature abspeichern
            feature = Feature(
                name=row['name'],
                classifier=row['classifier'],
                item=model,
                is_positive=row['positive']
            )
            feature.clean()
            feature.save()

            # create attribute with filtered indices (only values)
            # Merkmale bestimmen
            filtered_indices = row.iloc[5:].dropna().index.tolist()
            data_dict = create_attributes(row, filtered_indices, feature)

            # if volume data then create volume and reference feature
            if data_dict:
                data_dict['feature'] = feature
                data_dict['volume_type'] = row['classifier'].lower()
                create_feature_volume(data_dict)


def create_attributes(row: pd.Series, indices: List[str],
                      model: Feature) -> Dict:
    # Merkmale sortieren und abspeichern
    # add possible volume_fields to dict
    data_dict = {}
    possible_volume_fields = ['länge', 'breite', 'höhe', 'tiefe', 'durchmesser',
                              'breite_fuss', 'tiefe_fuss', 'winkel']
    for column_name in indices:
        # ignore tolerance (for now)
        if not '+' in column_name and not '-' in column_name:
            if isinstance(row[column_name], str):
                # save TextAttribute
                attr = FeatureAttributeText(
                    name=column_name,
                    value=row[column_name],
                    feature=model)
            elif isinstance(row[column_name], float):
                # save NumericAttribute
                attr = FeatureAttribute(
                    name=column_name,
                    value=row[column_name],
                    feature=model)
                # add attribute to data_dict for volume calculation
                if column_name in possible_volume_fields:
                    data_dict[remove_umlaut(column_name)] = row[column_name]

            else:
                # should be string or float -> reduce ambiguity
                raise ValidationError('Spalten-Typ nicht definiert.')
            attr.clean()
            attr.save()
            print(attr)

    return data_dict


def create_feature_volume(data_dict: Dict) -> None:
    # Volumen aller Feature der Excel-Datei
    # create feature volume from dict
    volume = Volume(**data_dict)
    volume.clean()
    volume.save()


def remove_umlaut(string: str):
    # Umlaute ersetzen für Programmierung notwendig
    u = 'ü'.encode()
    U = 'Ü'.encode()
    a = 'ä'.encode()
    A = 'Ä'.encode()
    o = 'ö'.encode()
    O = 'Ö'.encode()
    ss = 'ß'.encode()

    string = string.encode()
    string = string.replace(u, b'ue')
    string = string.replace(U, b'Ue')
    string = string.replace(a, b'ae')
    string = string.replace(A, b'Ae')
    string = string.replace(o, b'oe')
    string = string.replace(O, b'Oe')
    string = string.replace(ss, b'ss')

    string = string.decode('utf-8')
    return string
