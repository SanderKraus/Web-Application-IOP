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
python MyProject/manage.py runserver
```

## Requirements

- Django - Backend-Framework für das Kostentool
- Django-Extra-View - Open Source Plugin für eine Erweiterung der klassenbasierten Views
- Pandas - Für das Bearbeiten der Excel-Dateien

## Motivation

Das Web-Kostentool ermöglicht das Benutzen der entwickelten Methode über einen Webbrowser und die Speicherung der Daten in einer SQLite-Datenbank.
