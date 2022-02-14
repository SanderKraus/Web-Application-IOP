# RWTH-Kostentool-Masterarbeit-Sander-Kraus

## Installation

Python muss installiert und im PATH eingetragen sein.

1. Das Repository in den gewünschten Zielordner klonen

```
git clone <LINK>
cd <PROJEKT>
```

2. Die Requirements(Abhängigkeiten) installieren

```
pip install -r requirements.txt
```

2. (Optional) Virtual-Environment benutzen

```
python -m venv venv

UNIX: source venv/bin/activate
WINDOWS: venv/scripts/activate

pip install -r requirements.txt
```

3. Das Kostentool starten

```
python MyProjekt/manage.py runserver
```

## Requirements

- Django - Backend-Framework für das Kostentool
- Django-Extra-View - Open Source Plugin für eine Erweiterung der klassenbasierten Views
- Pandas - Für das Bearbeiten der Excel-Dateien

## Motivation

Das Web-Kostentool ermöglicht das Benutzen der entwickelten Methode über einen Webbrowser und die Speicherung der Daten in einer SQLite-Datenbank.

## Durchführung
### Initialisierung Referenzsystem
1. Technologien anlgegen
2. Neues Referenzsystem anlegen
3. Excel-Datei im Referenzsystem hochladen
4. Technologiekette auswaählen
5. FCT-Tabelle für jedes Merkmal ausfüllen
6. Nachdem alle FCT-Werte eingetragen sind muss der BUTTO #Volumenberechnen auf der Detailseite des Referenzsystems gedrückt werden (danach ist das Bauteilvolumen innerhalb der Fertigungskette berechnet und abgespeichert)
7. Referenzsystem ist angelegt und steht für einen Vergleich mit eingehenden Produktänderungen zur Verfügung

### Vergleich
1. Neues Vergelichssystem anlegen
2. Excel-Datei mit Produktänderungen hochladen
3. Referenzsystem auswählen mit dem die Produktänderung verglichen werden soll
4. Wenn neue Merkmale oder Feature hinzu kommen - Button # FCT-Erweitern drücken und alle neuen Merkmal und Feature werden dem Referenzsystem hinzugefügt
5. Anschließend muss im Referenzsystem die FCT-Tabelle erweitert werden. Wenn alle neuen Werte eingetragen und abgespeichert sich muss wieder der Button # Volumenberechnen gedrückt werden
6. Danach findet als erstes die technologische Überprüfung statt. Wenn Merkmale technologisch nicht Machbar oder nur mit Unsicherheiten wird auf der Seite des Vergelichsbauteils eine Meldung angezeigt
7. Wenn keine Meldung nach dem Hochladen erscheint, sind alle Feature und Merkmale technologisch Machbar und für die wirtschaftliche Überprüfung muss der Button # Änderungskosten gedrückt werden
8. Das Ergebnis wird auf der Seite angezeigt
