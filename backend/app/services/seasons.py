"""Zuchtsaisons: eine Saison läuft vom 1. September bis 31. August des
Folgejahres (Saison 25/26 = 1.9.2025 bis 31.8.2026)."""

from datetime import date

SEASON_START_MONTH = 9


def season_start_year(d: date) -> int:
    return d.year if d.month >= SEASON_START_MONTH else d.year - 1


def season_label(start_year: int) -> str:
    return f"{start_year % 100:02d}/{(start_year + 1) % 100:02d}"
