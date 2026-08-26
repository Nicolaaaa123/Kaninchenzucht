"""Einmalige Migration: importiert die alten Excel/Supabase-Tierdaten in den
Zuchtbetrieb 'Nicola Rauchenstein'.

Liest DATABASE_URL aus backend/.env.production (nicht aus der normalen
.env), damit dies unabhaengig von der lokalen Dev-Datenbank direkt gegen
die Produktions-DB (Neon) laeuft.

Ausfuehren (Vorschau, schreibt nichts):
    venv\\Scripts\\python.exe -m app.import_legacy_animals

Ausfuehren (schreibt wirklich):
    venv\\Scripts\\python.exe -m app.import_legacy_animals --commit
"""

import re
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Animal,
    AnimalStatus,
    Breed,
    BreedingCategory,
    Sex,
    Tenant,
    User,
    WeightEntry,
)

TARGET_TENANT_NAME = "Nicola Rauchenstein"

COLUMNS = [
    "chip_nummer", "name", "geschlecht", "rasse", "farbenschlag", "info",
    "geburtsdatum", "gewicht_gramm", "mutter_nr", "mutter_name",
    "vater_nr", "vater_name", "eingegeben_am", "aktiv",
]

# Roh-Daten 1:1 aus dem vom Nutzer gelieferten SQL-INSERT uebernommen.
RAW_VALUES = r"""
  ('6 041', NULL, 'm', 'Kleinwidder', 'Schwarz-Schecke', NULL, '2026-04-19', 2000, '982 691', 'Doro 4 20 ZN4', '621 867', 'Caro  5 41 ZN0', '2026-07-12T05:50:31.874000', TRUE),
  ('6 042', NULL, 'm', 'Kleinwidder', 'Schwarz', NULL, '2026-04-19', 2009, '982 691', 'Doro 4 20 ZN4', '621 867', 'Caro  5 41 ZN0', '2026-07-12T05:48:42.043000', TRUE),
  ('6 043', NULL, 'f', 'Kleinwidder', 'Schwarz-Schecke', NULL, '2026-04-19', 1930, '982 691', 'Doro 4 20 ZN4', '621 867', 'Caro  5 41 ZN0', '2026-07-12T05:46:42.234000', TRUE),
  ('6  154', NULL, 'f', 'Kleinwidder', 'Blau', NULL, NULL, 2235, '355 673 4', 'Lorli ZN5', '3 612', 'Louis ZN1', '2026-07-12T05:38:21.493000', TRUE),
  ('6 153', NULL, 'f', 'Kleinwidder', 'Blau', NULL, NULL, 2130, '355 673 4', 'Lorli ZN5', '3 612', 'Louis ZN1', '2026-07-12T05:38:06.660000', TRUE),
  ('6 152', NULL, 'f', 'Kleinwidder', 'Blau', NULL, NULL, 2090, '355 673 4', 'Lorli ZN5', '3 612', 'Louis ZN1', '2026-07-12T05:37:57.174000', TRUE),
  ('6 151', NULL, 'f', 'Kleinwidder', 'Blau', NULL, NULL, 1910, '355 673 4', 'Lorli ZN5', '3 612', 'Louis ZN1', '2026-07-12T05:37:48.914000', TRUE),
  ('621 867', 'Caro  5 41 ZN0', 'm', 'Kleinwidder', 'Schwarz-Schecke', NULL, '2025-03-07', NULL, NULL, NULL, NULL, NULL, '2026-03-31T18:45:17.203000', TRUE),
  (NULL, 'Paddy ZN0', 'm', 'Kleinwidder', 'Blau', NULL, '2019-01-01', NULL, NULL, NULL, NULL, NULL, '2026-03-16T20:56:15.418000', FALSE),
  ('6 842', NULL, 'f', 'Alaska/Sachsengold', NULL, NULL, '2026-01-06', NULL, '900223000188766', 'Emelie, ZN14', NULL, '5 071 James ZN18', '2026-03-09T19:44:10.539000', FALSE),
  ('6 841', NULL, 'f', 'Sachsengold', NULL, NULL, '2026-01-06', NULL, '900223000188766', 'Emelie, ZN14', NULL, '5 071 James ZN18', '2026-03-09T19:43:30.789000', TRUE),
  ('6 894', NULL, 'f', 'Alaska/Sachsengold', NULL, NULL, '2026-01-05', NULL, '4723', 'Liora, ZN19', NULL, '5 071 James ZN18', '2026-03-09T19:41:54.741000', TRUE),
  ('6 893', NULL, 'm', 'Sachsengold', NULL, NULL, '2026-01-05', NULL, '4723', 'Liora, ZN19', NULL, '5 071 James ZN18', '2026-03-09T19:41:12.280000', TRUE),
  ('6 892', NULL, 'f', 'Sachsengold', NULL, NULL, '2026-01-05', NULL, '4723', 'Liora, ZN19', NULL, '5 071 James ZN18', '2026-03-09T19:41:00.024000', TRUE),
  ('6 891', NULL, 'f', 'Sachsengold', NULL, NULL, '2026-01-05', NULL, '4723', 'Liora, ZN19', NULL, '5 071 James ZN18', '2026-03-09T19:40:47.137000', TRUE),
  (NULL, NULL, 'm', 'Farbenzwerg', 'Japaner', NULL, '2025-04-22', NULL, '282 573', 'Alea ZN4', NULL, 'Rammler Urech', '2026-03-09T19:35:05.282000', FALSE),
  (NULL, 'Amila ZN6', 'f', 'Farbenzwerg', 'Japaner', NULL, '2025-04-22', NULL, '282 573', 'Alea ZN4', NULL, 'Rammler Urech', '2026-03-09T19:34:42.266000', TRUE),
  (NULL, 'Rammler Urech', 'm', 'Farbenzwerg', 'Schwarz', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2026-03-09T19:33:42.988000', FALSE),
  ('6 145', NULL, 'f', 'Kleinwidder', 'Schwarz', NULL, '2026-01-05', 2660, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2026-03-09T19:13:42.281000', TRUE),
  ('6 144', NULL, 'f', 'Kleinwidder', 'Schwarz', NULL, '2026-01-05', 2720, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2026-03-09T19:13:34.030000', TRUE),
  ('6 143', NULL, 'f', 'Kleinwidder', 'Schwarz', NULL, '2026-01-05', 2640, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2026-03-09T19:13:25.250000', TRUE),
  ('6 142', NULL, 'f', 'Kleinwidder', 'Schwarz', NULL, '2026-01-05', 2060, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2026-03-09T19:13:18.391000', FALSE),
  ('6 141', NULL, 'f', 'Kleinwidder', 'Schwarz', NULL, '2026-01-05', 2160, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2026-03-09T19:13:11.818000', TRUE),
  ('355 673 4', 'Lorli ZN5', 'f', 'Kleinwidder', 'Blau', NULL, '2024-03-06', 3030, '1 610', 'Luna 1 610', '0 280', 'Schorschi 0 280', '2026-01-04T19:12:04.734000', TRUE),
  ('1 610', 'Luna 1 610', 'f', 'Kleinwidder', 'Blau', NULL, '2021-01-01', NULL, NULL, NULL, NULL, NULL, '2026-01-04T19:10:30.831000', FALSE),
  ('0 280', 'Schorschi 0 280', 'm', 'Kleinwidder', 'Blau', NULL, '2020-01-01', NULL, NULL, NULL, NULL, NULL, '2026-01-04T19:09:00.354000', FALSE),
  ('282 588', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-05-17', NULL, '4042', 'Enya, ZN18', NULL, 'Champion Tschugg ZN0', '2025-09-18T06:55:02.869000', FALSE),
  ('282 593', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-05-17', NULL, '4042', 'Enya, ZN18', NULL, 'Champion Tschugg ZN0', '2025-09-18T06:54:50.328000', FALSE),
  ('282 585', 'Emma ZN21', 'f', 'Sachsengold', NULL, NULL, '2025-05-17', NULL, '4042', 'Enya, ZN18', NULL, 'Champion Tschugg ZN0', '2025-09-18T06:54:37.007000', TRUE),
  ('282 594', NULL, 'm', 'Sachsengold', NULL, NULL, '2025-05-17', NULL, '4042', 'Enya, ZN18', NULL, 'Champion Tschugg ZN0', '2025-09-18T06:54:24.646000', FALSE),
  ('282 595', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-05-17', NULL, '4042', 'Enya, ZN18', NULL, 'Champion Tschugg ZN0', '2025-09-18T06:54:11.512000', FALSE),
  ('282 590', NULL, 'm', 'Sachsengold', NULL, NULL, '2025-05-17', NULL, '4042', 'Enya, ZN18', NULL, 'Champion Tschugg ZN0', '2025-09-18T06:53:57.798000', FALSE),
  ('282 592', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-05-16', NULL, '1091', 'Leila, ZN12', '901001000009109', 'Galino, ZN17', '2025-09-18T06:53:34.730000', FALSE),
  ('480 416', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-05-16', NULL, '1091', 'Leila, ZN12', '901001000009109', 'Galino, ZN17', '2025-09-18T06:53:21.524000', FALSE),
  ('5 129', NULL, 'f', 'Kleinwidder', 'Blau', NULL, '2025-04-13', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-06-20T08:41:16.377000', FALSE),
  ('282 587', NULL, 'm', 'Kleinwidder', 'Blau', NULL, '2025-04-13', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-06-20T08:41:10.056000', FALSE),
  ('282 589', NULL, 'm', 'Kleinwidder', 'Blau', NULL, '2025-04-13', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-06-20T08:39:50.895000', FALSE),
  ('5 126', NULL, 'f', 'Kleinwidder', 'Blau', NULL, '2025-04-13', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-06-20T08:39:45.268000', FALSE),
  ('5 125', NULL, 'f', 'Kleinwidder', 'Blau', NULL, '2025-04-13', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-06-20T08:39:19.755000', FALSE),
  ('282 583', NULL, 'f', 'Kleinwidder', 'Blau', NULL, '2025-04-13', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-06-20T08:39:11.739000', FALSE),
  ('5 123', NULL, 'f', 'Kleinwidder', 'Blau', NULL, '2025-04-13', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-06-20T08:39:01.844000', FALSE),
  ('282 591', NULL, 'm', 'Kleinwidder', 'Blau', NULL, '2025-04-13', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-06-20T08:38:55.749000', FALSE),
  ('5 146', NULL, 'f', 'Kleinwidder', 'Schwarz', NULL, '2025-04-09', NULL, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2025-06-20T08:37:43.551000', FALSE),
  ('5 145', NULL, 'f', 'Kleinwidder', 'Schwarz', NULL, '2025-04-09', NULL, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2025-06-20T08:37:20.936000', FALSE),
  ('5 144', NULL, 'm', 'Kleinwidder', 'Schwarz', NULL, '2025-04-09', NULL, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2025-06-20T08:37:12.707000', FALSE),
  ('282 599', NULL, 'f', 'Kleinwidder', 'Schwarz', NULL, '2025-04-09', NULL, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2025-06-20T08:37:05.170000', FALSE),
  ('282 580', 'Daisy 5 142 ZN6', 'f', 'Kleinwidder', 'Schwarz', NULL, '2025-04-09', NULL, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2025-06-20T08:36:55.423000', FALSE),
  ('282 582', NULL, 'f', 'Kleinwidder', 'Schwarz', NULL, '2025-04-09', NULL, '982 691', 'Doro 4 20 ZN4', '3 612', 'Louis ZN1', '2025-06-20T08:36:42.554000', FALSE),
  (NULL, 'Champion Tschugg ZN0', 'm', 'Sachsengold', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'Gatschet, ZN6', '2025-05-17T20:21:12.378000', TRUE),
  ('480 434', 'Winy ZN19', 'm', 'Sachsengold', NULL, NULL, '2025-04-20', NULL, '4723', 'Liora, ZN19', '118269', 'Champion Winterthur, ZN0', '2025-05-05T17:28:48.920000', TRUE),
  ('5 092', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-04-20', NULL, '4723', 'Liora, ZN19', '118269', 'Champion Winterthur, ZN0', '2025-05-05T17:28:46.863000', FALSE),
  ('5 094', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-04-20', NULL, '4723', 'Liora, ZN19', '118269', 'Champion Winterthur, ZN0', '2025-05-05T17:28:45.341000', FALSE),
  ('5 095', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-04-20', NULL, '4723', 'Liora, ZN19', '118269', 'Champion Winterthur, ZN0', '2025-05-05T17:28:43.381000', FALSE),
  ('5 091', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-04-20', NULL, '4723', 'Liora, ZN19', '118269', 'Champion Winterthur, ZN0', '2025-05-05T17:28:41.350000', FALSE),
  ('282 581', NULL, 'm', 'Sachsengold', NULL, NULL, '2025-04-11', NULL, NULL, 'Mila, ZN17', '901001000009109', 'Galino, ZN17', '2025-05-05T17:23:31.048000', FALSE),
  ('5 772', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-04-11', NULL, NULL, 'Mila, ZN17', '901001000009109', 'Galino, ZN17', '2025-05-05T17:23:29.077000', FALSE),
  ('5 044', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-04-14', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2025-05-05T17:23:15.344000', FALSE),
  ('5 043', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-04-14', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2025-05-05T17:23:13.439000', FALSE),
  ('5 042', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-04-14', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2025-05-05T17:23:11.348000', FALSE),
  ('282 596', NULL, 'f', 'Sachsengold', NULL, NULL, '2025-04-14', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2025-05-05T17:23:06.826000', FALSE),
  ('5 072', NULL, 'f', 'Alaska/Sachsengold', NULL, NULL, '2025-01-23', 1000, NULL, 'Mila, ZN17', NULL, 'Jonas', '2025-03-13T19:06:27.213000', FALSE),
  (NULL, '5 071 James ZN18', 'm', 'Alaska/Sachsengold', NULL, NULL, '2025-01-23', 1660, NULL, 'Mila, ZN17', NULL, 'Jonas', '2025-03-13T19:05:58.980000', TRUE),
  ('118269', 'Champion Winterthur, ZN0', 'm', 'Sachsengold', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2025-03-13T12:13:22.719000', TRUE),
  ('5 126', NULL, 'm', 'Kleinwidder', 'Blau', NULL, '2025-01-22', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-03-10T14:22:56.675000', FALSE),
  ('5 125', NULL, 'f', 'Kleinwidder', 'Blau', NULL, '2025-01-22', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-03-10T14:22:47.574000', FALSE),
  ('5 124', NULL, 'm', 'Kleinwidder', 'Blau', NULL, '2025-01-22', 1665, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-03-10T14:22:38.564000', FALSE),
  ('5 123', 'Rina', 'f', 'Kleinwidder', 'Blau', NULL, '2025-01-22', 2150, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-03-10T14:22:33.238000', FALSE),
  ('282 586', 'Rina 5 122', 'f', 'Kleinwidder', 'Blau', NULL, '2025-01-22', 2865, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-03-10T14:22:27.646000', FALSE),
  ('5 121', NULL, 'f', 'Kleinwidder', 'Blau', NULL, '2025-01-22', 2200, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2025-03-10T14:22:20.854000', FALSE),
  ('982 691', 'Doro 4 20 ZN4', 'f', 'Kleinwidder', 'Schwarz', 'Von Roli Lüthi am 19.1.2025 gekauft. Vater madagaskar von Martin Urech', '2024-01-01', 3200, NULL, NULL, NULL, NULL, '2025-01-20T06:30:20.490000', TRUE),
  ('282 584', NULL, 'f', 'Kleinwidder', 'Blau', NULL, '2024-04-07', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2024-12-16T19:30:48.228000', FALSE),
  ('(4 112)', 'Tiara ZN 3', 'f', 'Kleinwidder', 'Blauschecke', 'Maske erfasst Unterlippe nicht, zu grosse und verspritzte weisse Farbfelder', '2024-05-19', NULL, '3 631', 'Thea ZN1', '3 612', 'Louis ZN1', '2024-12-16T19:23:56.061000', FALSE),
  ('4 111', NULL, 'm', 'Kleinwidder', 'Blau', NULL, '2024-05-19', NULL, '3 631', 'Thea ZN1', '3 612', 'Louis ZN1', '2024-12-16T19:23:17.930000', FALSE),
  ('282 576', NULL, 'm', 'Kleinwidder', 'Blau', NULL, '2024-04-07', NULL, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2024-12-16T19:20:11.094000', FALSE),
  ('282 598', 'Laro 4 121 ZN2', 'm', 'Kleinwidder', 'Blau', NULL, '2024-04-07', 2950, '3 604', 'Ruby ZN2', '3 612', 'Louis ZN1', '2024-12-16T19:19:34.377000', FALSE),
  (NULL, 'Mila, ZN17', 'f', 'Sachsengold', NULL, 'Von Grosspapi gekauft', '2024-04-01', NULL, NULL, NULL, NULL, 'Fribourg', '2024-12-16T14:16:17.176000', FALSE),
  (NULL, 'Dexter', 'm', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2024-08-04T08:58:29.315000', FALSE),
  (NULL, 'Dexter', 'm', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2024-08-04T08:58:29.304000', FALSE),
  (NULL, 'Dexter', 'm', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2024-08-04T08:58:29.260000', FALSE),
  (NULL, 'Dexter', 'm', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2024-08-04T08:58:29.216000', FALSE),
  ('282 578', 'Diago', 'm', 'Farbenzwerg', 'Rhön', NULL, '2024-03-25', NULL, NULL, 'Zellia ZN5', NULL, 'Dexter', '2024-07-31T10:49:41.536000', FALSE),
  ('282 571', 'Django', 'm', 'Farbenzwerg', 'Rhön', NULL, '2024-03-26', NULL, NULL, 'Aila', NULL, 'Dexter', '2024-07-31T10:47:44.499000', FALSE),
  ('282 573', 'Alea ZN4', 'f', 'Farbenzwerg', 'Rhön', NULL, '2024-03-26', NULL, NULL, 'Aila', NULL, 'Dexter', '2024-07-31T10:45:16.059000', TRUE),
  ('4045', 'Galileo', 'm', 'Sachsengold', NULL, NULL, '2024-03-12', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2024-05-13T14:27:01.456000', FALSE),
  ('4041', 'Eileen', 'f', 'Sachsengold', NULL, NULL, '2024-03-12', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2024-05-13T14:26:59.136000', FALSE),
  ('4044', 'Elena', 'f', 'Sachsengold', NULL, NULL, '2024-03-12', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2024-05-13T14:26:56.951000', FALSE),
  ('4042', 'Enya, ZN18', 'f', 'Sachsengold', NULL, NULL, '2024-03-12', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2024-05-13T14:26:54.696000', TRUE),
  ('4043', 'Emira', 'f', 'Sachsengold', NULL, NULL, '2024-03-12', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2024-05-13T14:26:52.698000', FALSE),
  (NULL, NULL, 'f', 'Sachsengold', NULL, NULL, '2024-03-13', NULL, NULL, 'Mila, ZN17', NULL, 'Gatschet, ZN6', '2024-05-13T14:26:45.088000', FALSE),
  ('4651', 'Mia', 'f', 'Sachsengold', NULL, NULL, '2024-03-13', NULL, NULL, 'Mila, ZN17', NULL, 'Gatschet, ZN6', '2024-05-13T14:26:43.060000', FALSE),
  ('4613', 'Linnea', 'f', 'Sachsengold', NULL, NULL, '2024-03-15', NULL, '0564', 'Luna, ZN11', NULL, 'Gatschet, ZN6', '2024-05-13T14:26:22.660000', FALSE),
  ('4612', 'Lavinia', 'f', 'Sachsengold', NULL, NULL, '2024-03-15', NULL, '0564', 'Luna, ZN11', NULL, 'Gatschet, ZN6', '2024-05-13T14:26:20.774000', FALSE),
  ('4611', 'Gavin', 'm', 'Sachsengold', NULL, NULL, '2024-03-15', NULL, '0564', 'Luna, ZN11', NULL, 'Gatschet, ZN6', '2024-05-13T14:26:18.412000', FALSE),
  ('4723', 'Liora, ZN19', 'f', 'Sachsengold', NULL, NULL, '2024-03-22', NULL, '1091', 'Leila, ZN12', '901001000009109', 'Galino, ZN17', '2024-05-13T14:24:41.422000', TRUE),
  ('4722', 'Lyla', 'f', 'Sachsengold', NULL, NULL, '2024-03-22', NULL, '1091', 'Leila, ZN12', '901001000009109', 'Galino, ZN17', '2024-05-13T14:24:38.646000', FALSE),
  ('4725', 'Livia', 'f', 'Sachsengold', NULL, NULL, '2024-03-22', NULL, '1091', 'Leila, ZN12', '901001000009109', 'Galino, ZN17', '2024-05-13T14:24:36.409000', FALSE),
  ('4726', 'Giulio', 'm', 'Sachsengold', NULL, NULL, '2024-03-22', NULL, '1091', 'Leila, ZN12', '901001000009109', 'Galino, ZN17', '2024-05-13T14:24:34.211000', FALSE),
  ('4724', 'Liana', 'f', 'Sachsengold', NULL, NULL, '2024-03-22', NULL, '1091', 'Leila, ZN12', '901001000009109', 'Galino, ZN17', '2024-05-13T14:24:32.084000', FALSE),
  ('4721', 'Gil', 'm', 'Sachsengold', NULL, NULL, '2024-03-22', NULL, '1091', 'Leila, ZN12', '901001000009109', 'Galino, ZN17', '2024-05-13T14:24:28.886000', FALSE),
  (NULL, 'Aila', 'f', 'Farbenzwerg', 'Röhn', NULL, '2022-02-10', NULL, NULL, NULL, NULL, NULL, '2024-02-09T18:59:08.435000', FALSE),
  ('3 631', 'Thea ZN1', 'f', 'Kleinwidder', 'Blauschecke', 'Fruchtbarkeit mangelhaft', '2023-05-11', NULL, '533', 'Sch. Blau 533', '280', 'Voll. Blau 280', '2024-01-21T17:13:17.069000', FALSE),
  ('533', 'Sch. Blau 533', 'f', 'Kleinwidder', 'Blauschecke', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2024-01-21T17:12:06.401000', FALSE),
  ('280', 'Voll. Blau 280', 'm', 'Kleinwidder', 'Blau', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2024-01-21T17:11:10.344000', FALSE),
  ('3 604', 'Ruby ZN2', 'f', 'Kleinwidder', 'Blau', NULL, '2023-03-06', NULL, '432', 'Sch. Blau 432', '422', 'Voll. Blau 422', '2024-01-21T17:10:22.518000', FALSE),
  ('432', 'Sch. Blau 432', 'f', 'Kleinwidder', 'Blauschecke', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2024-01-21T17:06:38.137000', FALSE),
  ('422', 'Voll. Blau 422', 'm', 'Kleinwidder', 'Blau', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2024-01-21T17:05:47.693000', FALSE),
  ('3 612', 'Louis ZN1', 'm', 'Kleinwidder', 'Blau', NULL, '2023-03-06', 3285, '525', 'Voll. Blau 525', '425', 'Sch. Blau 425', '2024-01-21T17:04:44.295000', TRUE),
  ('425', 'Sch. Blau 425', 'm', 'Kleinwidder', 'Blauschecke', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2024-01-21T17:00:54.227000', FALSE),
  ('525', 'Voll. Blau 525', 'f', 'Kleinwidder', 'Blau', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2024-01-21T16:59:34.867000', FALSE),
  (NULL, 'Noelia', 'f', 'Sachsengold', NULL, 'Gekauft bei Grosspapi', '2023-03-15', NULL, NULL, NULL, NULL, 'Fribourg', '2023-12-11T16:12:48.181000', FALSE),
  (NULL, 'Mila, ZN17', 'f', 'Sachsengold', NULL, 'Gekauft von Alexander Graf, Fein,Top Fell', '2023-04-04', NULL, NULL, NULL, NULL, NULL, '2023-11-28T14:21:03.042000', FALSE),
  (NULL, 'Zellia ZN5', 'f', 'Farbenzwerg', 'Rhön', NULL, '2023-06-01', NULL, NULL, 'Zoe', NULL, 'Cäsar', '2023-10-21T07:45:18.910000', TRUE),
  ('901001000009101', 'Garino', 'm', 'Sachsengold', NULL, 'Kopfform nicht gut, Weiches Fell', '2023-04-08', NULL, '1091', 'Leila, ZN12', NULL, 'Gatschet, ZN6', '2023-05-13T15:53:17.439000', FALSE),
  ('901001000009103', 'Gola', 'm', 'Sachsengold', NULL, 'Relativ klein, Leicht, Feines Fell', '2023-04-08', NULL, '1091', 'Leila, ZN12', NULL, 'Gatschet, ZN6', '2023-05-13T15:53:14.040000', FALSE),
  ('901001000009106', 'Ginalano', 'm', 'Sachsengold', NULL, 'Ohrenhaltung, Weiches Fell', '2023-04-08', NULL, '1091', 'Leila, ZN12', NULL, 'Gatschet, ZN6', '2023-05-13T15:53:08.989000', FALSE),
  (NULL, 'Cäsar', 'm', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2023-04-20T07:50:44.038000', FALSE),
  ('901001000009105', 'Hopel', 'm', 'Sachsengold', NULL, 'Brust hell, Fell gut', '2023-03-27', NULL, '8024', 'Lara, ZN6', '9445', 'Hugo, ZN5', '2023-03-28T07:40:58.838000', FALSE),
  ('901001000009119', 'Lina', 'f', 'Sachsengold', NULL, 'Gutes Fell, allgemein schön, Haarung Probleme', '2023-03-25', NULL, '0564', 'Luna, ZN11', NULL, 'Gatschet, ZN6', '2023-03-28T07:00:50.319000', FALSE),
  ('3 614', NULL, 'f', 'Sachsengold', NULL, NULL, '2023-03-25', NULL, '0564', 'Luna, ZN11', NULL, 'Gatschet, ZN6', '2023-03-28T07:00:48.693000', FALSE),
  ('901001000009102', 'Golano', 'm', 'Sachsengold', NULL, 'Höchster Punkt schlecht, Schönes Fell, Guter Bau', '2023-03-25', NULL, '0564', 'Luna, ZN11', NULL, 'Gatschet, ZN6', '2023-03-28T07:00:46.843000', FALSE),
  ('901001000009111', 'Gilo', 'm', 'Sachsengold', NULL, 'Minim Höchster Punkt schlecht, Guter Bau, Relativ weiches Fell', '2023-03-25', NULL, '0564', 'Luna, ZN11', NULL, 'Gatschet, ZN6', '2023-03-28T07:00:44.941000', FALSE),
  ('901001000009110', 'Lenea', 'f', 'Sachsengold', NULL, 'Fell gut, Fein, Hüftknochen schlecht', '2023-03-27', NULL, '8024', 'Lara, ZN6', '9445', 'Hugo, ZN5', '2023-03-28T06:57:49.583000', FALSE),
  (NULL, NULL, 'f', 'Sachsengold', NULL, NULL, '2023-03-27', NULL, '8024', 'Lara, ZN6', '9445', 'Hugo, ZN5', '2023-03-28T06:57:46.880000', FALSE),
  ('901001000009109', 'Galino, ZN17', 'm', 'Sachsengold', NULL, 'Sehr schön', '2023-03-15', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2023-03-15T11:01:07.673000', TRUE),
  ('901001000009116', 'Gilano', 'm', 'Sachsengold', NULL, 'Feiner Bau, Schöne Farbe, Gutes Fell, Haarung Probleme', '2023-03-15', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2023-03-15T11:01:05.603000', FALSE),
  (NULL, NULL, 'f', 'Sachsengold', NULL, NULL, '2023-03-15', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2023-03-15T11:00:59.566000', FALSE),
  ('901001000009115', 'Ginola', 'm', 'Sachsengold', NULL, 'Dreckig, Schönes Fell', '2023-03-15', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2023-03-15T11:00:52.415000', FALSE),
  (NULL, NULL, 'f', 'Sachsengold', NULL, NULL, '2023-03-15', NULL, '900223000188766', 'Emelie, ZN14', NULL, 'GR, ZN0', '2023-03-15T11:00:44.590000', FALSE),
  (NULL, 'Zuranna', 'f', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, 'Zoe', NULL, 'Zumstein 2', '2022-09-10T11:26:33.051000', FALSE),
  ('900223000188778', 'Finn ZN1', 'm', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, 'Zoe', NULL, 'Zumstein 2', '2022-09-10T11:23:56.028000', TRUE),
  (NULL, 'Tierney', 'm', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, 'Switchi', NULL, 'Zumstein', '2022-09-10T11:22:34.892000', FALSE),
  (NULL, 'Zoe', 'f', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, 'Switchi', NULL, 'Zumstein', '2022-09-10T11:21:14.865000', FALSE),
  (NULL, 'Zumstein', 'm', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2022-09-10T11:20:22.299000', FALSE),
  (NULL, 'Switchi', 'f', 'Farbenzwerg', 'Rhön', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2022-09-10T11:19:44.052000', FALSE),
  ('900223000188777', 'Lia', 'f', 'Sachsengold', NULL, NULL, '2022-03-25', NULL, '0564', 'Luna, ZN11', NULL, 'Gatschet, ZN6', '2022-09-10T08:22:07.788000', FALSE),
  ('2092', 'Hopel', 'm', 'Sachsengold', NULL, 'Hell', '2022-03-28', NULL, '9 462', 'Leona, ZN9', NULL, 'GR, ZN0', '2022-09-10T07:33:01.455000', FALSE),
  ('900223000188776', 'Lala', 'f', 'Sachsengold', NULL, NULL, '2022-03-28', NULL, '9 462', 'Leona, ZN9', NULL, 'GR, ZN0', '2022-09-10T07:31:57.459000', FALSE),
  ('900223000188769', 'Lani', 'f', 'Sachsengold', NULL, NULL, '2022-03-25', 2665, '0564', 'Luna, ZN11', NULL, 'Gatschet, ZN6', '2022-09-10T07:29:55.372000', FALSE),
  ('900223000188773', 'Luisa', 'f', 'Sachsengold', NULL, NULL, '2022-03-27', 2700, '8024', 'Lara, ZN6', '9445', 'Hugo, ZN5', '2022-09-10T07:28:20.794000', FALSE),
  ('900223000188771', 'Lena', 'f', 'Sachsengold', NULL, NULL, '2022-04-08', NULL, '1091', 'Leila, ZN12', NULL, 'Gatschet, ZN6', '2022-09-10T07:27:05.502000', FALSE),
  ('900223000188766', 'Emelie, ZN14', 'f', 'Sachsengold', NULL, NULL, '2022-03-23', 2575, NULL, 'Stöckli', '9445', 'Hugo, ZN5', '2022-09-10T07:26:14.406000', TRUE),
  ('900223000188761', 'Lisa', 'f', 'Sachsengold', NULL, NULL, '2022-03-27', 2615, '8024', 'Lara, ZN6', '9445', 'Hugo, ZN5', '2022-09-10T07:24:48.474000', FALSE),
  (NULL, 'Stöckli', 'f', 'Sachsengold', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2022-09-10T07:20:26.019000', FALSE),
  ('2532', 'Hendrick', 'm', 'Sachsengold', NULL, NULL, '2022-03-23', NULL, NULL, 'Stöckli', '9445', 'Hugo, ZN5', '2022-09-10T07:20:02.220000', FALSE),
  ('900223000188774', 'Guido', 'm', 'Sachsengold', NULL, NULL, '2022-03-25', NULL, '0564', 'Luna, ZN11', NULL, 'Gatschet, ZN6', '2022-09-10T07:18:33.437000', FALSE),
  ('900223000188767', 'Henry', 'm', 'Sachsengold', NULL, NULL, '2022-03-27', NULL, '8024', 'Lara, ZN6', '9445', 'Hugo, ZN5', '2022-09-10T07:17:01.749000', FALSE),
  ('900223000188772', 'Gino', 'm', 'Sachsengold', NULL, NULL, '2022-04-08', 3100, '1091', 'Leila, ZN12', NULL, 'Gatschet, ZN6', '2022-09-10T07:10:00.182000', FALSE),
  ('900223000188775', 'Golo', 'm', 'Sachsengold', NULL, NULL, '2022-04-08', NULL, '1091', 'Leila, ZN12', NULL, 'Gatschet, ZN6', '2022-09-10T07:07:38.534000', FALSE),
  (NULL, 'Sarina', 'f', 'Sachsengold', NULL, NULL, NULL, NULL, NULL, 'Seraina', NULL, 'Fribourg', '2022-09-10T06:03:13.131000', FALSE),
  (NULL, 'Fribourg', 'm', 'Sachsengold', NULL, 'Eingestallt bei Grosspapi', NULL, NULL, NULL, NULL, NULL, NULL, '2022-09-10T06:00:26.029000', FALSE),
  (NULL, 'Seraina', 'f', 'Sachsengold', NULL, NULL, NULL, NULL, NULL, 'Chuz 1', NULL, 'Chuz unbekannt', '2022-09-10T05:59:33.043000', FALSE),
  (NULL, 'Chuz unbekannt', 'm', 'Sachsengold', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2022-09-10T05:58:16.241000', FALSE),
  (NULL, 'Chuz 1', 'f', 'Sachsengold', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2022-09-10T05:57:30.769000', FALSE),
  ('7121', 'Sweety', 'm', 'Sachsengold', NULL, NULL, '2017-01-01', NULL, NULL, 'Seraina', NULL, 'Fribourg', '2022-09-09T19:28:54.473000', FALSE),
  ('1091', 'Leila, ZN12', 'f', 'Sachsengold', NULL, NULL, '2021-03-24', NULL, '9 462', 'Leona, ZN9', NULL, 'GR, ZN0', '2022-09-09T19:26:33.168000', TRUE),
  (NULL, 'GR, ZN0', 'm', 'Sachsengold', NULL, 'Eingestallt bei Grosspapi', NULL, NULL, NULL, NULL, NULL, NULL, '2022-09-09T19:25:50.492000', TRUE),
  (NULL, 'Gatschet, ZN6', 'm', 'Sachsengold', NULL, 'Gekauft von Roger Gatschet', '2021-01-01', NULL, NULL, NULL, NULL, NULL, '2022-09-09T19:23:03.226000', FALSE),
  ('0564', 'Luna, ZN11', 'f', 'Sachsengold', NULL, NULL, '2020-03-29', NULL, '8024', 'Lara, ZN6', '9445', 'Hugo, ZN5', '2022-09-09T19:20:09.813000', FALSE),
  ('9 462', 'Leona, ZN9', 'f', 'Sachsengold', NULL, 'Champion 2019 Wikon', '2019-05-01', NULL, '8024', 'Lara, ZN6', '9445', 'Hugo, ZN5', '2022-09-09T19:18:18.649000', FALSE),
  ('8024', 'Lara, ZN6', 'f', 'Sachsengold', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2022-09-09T19:16:45.021000', FALSE),
  ('9445', 'Hugo, ZN5', 'm', 'Sachsengold', NULL, 'Teilweise Stichel an der Brust.', '2019-04-02', NULL, NULL, 'Wuschi', NULL, 'Helli', '2022-09-09T18:49:40.133000', FALSE),
  (NULL, 'Wuschi', 'f', 'Sachsengold', NULL, NULL, NULL, NULL, NULL, 'UR-Hodel', NULL, NULL, '2022-09-09T18:48:00.602000', FALSE),
  (NULL, 'Helli', 'm', 'Sachsengold', NULL, NULL, '2018-04-01', NULL, NULL, NULL, NULL, NULL, '2022-09-09T18:45:59.655000', FALSE)
"""


def parse_values(raw: str) -> list[list]:
    """Kleiner Parser fuer die SQL-VALUES-Tupel: respektiert Anfuehrungszeichen
    (Kommas/Klammern innerhalb von Strings sind kein Trenner)."""
    rows: list[list] = []
    i = 0
    n = len(raw)
    while i < n:
        if raw[i] == "(":
            i += 1
            fields: list = []
            while True:
                while raw[i] in " \t\n\r":
                    i += 1
                if raw[i] == "'":
                    i += 1
                    start = i
                    buf = []
                    while True:
                        if raw[i] == "'" and i + 1 < n and raw[i + 1] == "'":
                            buf.append("'")
                            i += 2
                            continue
                        if raw[i] == "'":
                            break
                        buf.append(raw[i])
                        i += 1
                    fields.append("".join(buf))
                    i += 1
                else:
                    start = i
                    while raw[i] not in ",)":
                        i += 1
                    token = raw[start:i].strip()
                    if token == "NULL":
                        fields.append(None)
                    elif token == "TRUE":
                        fields.append(True)
                    elif token == "FALSE":
                        fields.append(False)
                    else:
                        fields.append(int(token))
                while raw[i] in " \t\n\r":
                    i += 1
                if raw[i] == ",":
                    i += 1
                    continue
                if raw[i] == ")":
                    i += 1
                    break
            rows.append(fields)
        else:
            i += 1
    return rows


def parse_date(v: str | None) -> date | None:
    if not v:
        return None
    return date.fromisoformat(v)


def parse_datetime(v: str | None) -> datetime | None:
    if not v:
        return None
    return datetime.fromisoformat(v)


def main() -> None:
    commit = "--commit" in sys.argv

    env_path = Path(__file__).resolve().parents[1] / ".env.production"
    if not env_path.exists():
        print(f"FEHLER: {env_path} nicht gefunden.")
        sys.exit(1)
    db_url = None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            db_url = line[len("DATABASE_URL=") :].strip()
    if not db_url:
        print("FEHLER: DATABASE_URL nicht in .env.production gefunden.")
        sys.exit(1)
    if db_url.startswith("postgresql://"):
        db_url = "postgresql+psycopg://" + db_url[len("postgresql://") :]

    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    tenant = db.query(Tenant).filter(Tenant.name == TARGET_TENANT_NAME).one_or_none()
    if tenant is None:
        print(f"FEHLER: Kein Zuchtbetrieb mit Namen '{TARGET_TENANT_NAME}' gefunden.")
        sys.exit(1)
    print(f"Ziel-Zuchtbetrieb: {tenant.name} ({tenant.id})")

    breeds_by_name = {b.name: b for b in db.query(Breed).filter(Breed.tenant_id == tenant.id).all()}

    rows_raw = parse_values(RAW_VALUES)
    rows = [dict(zip(COLUMNS, r)) for r in rows_raw]
    print(f"{len(rows)} Zeilen aus den Rohdaten geparst.")

    # --- Erster Durchgang: Tiere anlegen -----------------------------------
    seen_chip_counts: dict[str, int] = {}
    unknown_breed_count = 0
    synthetic_chip_count = 0
    duplicate_chip_count = 0

    # Fuer die Elternzuordnung im zweiten Durchgang:
    by_original_chip: dict[str, list[Animal]] = {}
    by_name: dict[str, list[Animal]] = {}
    animals: list[Animal] = []
    weight_entries: list[WeightEntry] = []

    for row in rows:
        notes_parts = []
        if row["info"]:
            notes_parts.append(row["info"])

        breed = None
        rasse = row["rasse"]
        if rasse:
            breed = breeds_by_name.get(rasse)
            if breed is None:
                unknown_breed_count += 1
                notes_parts.append(f"Rasse im Altbestand: {rasse} (keiner Standardrasse zugeordnet)")

        original_chip = row["chip_nummer"]
        if original_chip:
            count = seen_chip_counts.get(original_chip, 0) + 1
            seen_chip_counts[original_chip] = count
            if count == 1:
                final_chip = original_chip
            else:
                duplicate_chip_count += 1
                final_chip = f"{original_chip}-{count}"
                notes_parts.append("Chip-Nr. im Altbestand mehrfach vergeben, Suffix ergaenzt")
        else:
            synthetic_chip_count += 1
            final_chip = f"LEGACY-{synthetic_chip_count:04d}"
            notes_parts.append("Kein Chip im Altbestand erfasst (nur Name/Herkunft bekannt)")

        sex = {"m": Sex.MALE, "f": Sex.FEMALE}.get(row["geschlecht"], Sex.UNKNOWN)
        status = AnimalStatus.ACTIVE if row["aktiv"] else AnimalStatus.RETIRED

        animal = Animal(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            chip_number=final_chip,
            name=row["name"],
            sex=sex,
            birth_date=parse_date(row["geburtsdatum"]),
            status=status,
            color_variant=row["farbenschlag"],
            category=BreedingCategory.BREEDING,
            breed_id=breed.id if breed else None,
            notes="; ".join(notes_parts) or None,
        )
        animals.append(animal)

        if original_chip:
            by_original_chip.setdefault(original_chip, []).append(animal)
        if row["name"]:
            by_name.setdefault(row["name"], []).append(animal)

        if row["gewicht_gramm"]:
            measured_on = animal.birth_date or parse_datetime(row["eingegeben_am"]).date()
            weight_entries.append(
                WeightEntry(
                    id=uuid.uuid4(),
                    animal_id=animal.id,
                    measured_on=measured_on,
                    weight_grams=int(row["gewicht_gramm"]),
                )
            )

    # --- Zweiter Durchgang: Eltern zuordnen --------------------------------
    def resolve(nr: str | None, name: str | None) -> Animal | None:
        if nr:
            candidates = by_original_chip.get(nr, [])
            if len(candidates) == 1:
                return candidates[0]
            if len(candidates) > 1 and name:
                narrowed = [a for a in candidates if a.name == name]
                if len(narrowed) == 1:
                    return narrowed[0]
        if name:
            candidates = by_name.get(name, [])
            if len(candidates) == 1:
                return candidates[0]
        return None

    unresolved_mothers = 0
    unresolved_fathers = 0
    for row, animal in zip(rows, animals):
        mother = resolve(row["mutter_nr"], row["mutter_name"])
        if mother:
            animal.mother = mother
        elif row["mutter_nr"] or row["mutter_name"]:
            unresolved_mothers += 1
            extra = f"Mutter nicht zuordenbar: {row['mutter_nr'] or ''} {row['mutter_name'] or ''}".strip()
            animal.notes = f"{animal.notes}; {extra}" if animal.notes else extra

        father = resolve(row["vater_nr"], row["vater_name"])
        if father:
            animal.father = father
        elif row["vater_nr"] or row["vater_name"]:
            unresolved_fathers += 1
            extra = f"Vater nicht zuordenbar: {row['vater_nr'] or ''} {row['vater_name'] or ''}".strip()
            animal.notes = f"{animal.notes}; {extra}" if animal.notes else extra

    # --- Zusammenfassung -----------------------------------------------
    active_count = sum(1 for a in animals if a.status == AnimalStatus.ACTIVE)
    retired_count = len(animals) - active_count
    print("\n--- Zusammenfassung ---")
    print(f"Tiere gesamt:              {len(animals)}")
    print(f"  davon aktiv:             {active_count}")
    print(f"  davon ausgeschieden:     {retired_count}")
    print(f"Gewichtseintraege:         {len(weight_entries)}")
    print(f"Unbekannte Rasse (Kreuzung, ohne Zuordnung): {unknown_breed_count}")
    print(f"Synthetische Chip-Nrn. (kein Chip im Altbestand): {synthetic_chip_count}")
    print(f"Duplikat-Chip-Nrn. mit Suffix versehen:    {duplicate_chip_count}")
    print(f"Mutter nicht zuordenbar:   {unresolved_mothers}")
    print(f"Vater nicht zuordenbar:    {unresolved_fathers}")

    if not commit:
        db.rollback()
        print("\nNUR VORSCHAU -- nichts wurde gespeichert. Mit --commit erneut ausfuehren, um wirklich zu importieren.")
        return

    db.add_all(animals)
    db.add_all(weight_entries)
    db.commit()
    print("\nGespeichert.")


if __name__ == "__main__":
    main()
