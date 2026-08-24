import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _enum(enum_cls, name: str, length: int = 20):
    """Stored as VARCHAR + CHECK constraint (native_enum=False) rather than a
    native Postgres ENUM type, to avoid driver-specific enum (de)serialization
    quirks (psycopg3 maps Python Enums by name, not by value, for native types)."""
    return Enum(enum_cls, name=name, native_enum=False, length=length, values_callable=lambda e: [m.value for m in e])


class Sex(str, enum.Enum):
    MALE = "male"  # Rammler
    FEMALE = "female"  # Häsin
    UNKNOWN = "unknown"


class AnimalStatus(str, enum.Enum):
    ACTIVE = "active"
    SOLD = "sold"
    DECEASED = "deceased"
    RETIRED = "retired"  # aus der Zucht genommen
    SLAUGHTERED = "slaughtered"  # geschlachtet


class BreedingCategory(str, enum.Enum):
    YOUNG = "young"  # Jungtier
    BREEDING = "breeding"  # Zuchttier
    EXTERNAL = "external"  # externes Zuchttier


class BreedGroup(str, enum.Enum):
    DWARF = "dwarf"  # Zwergrassen
    SMALL = "small"  # Kleine Rassen
    MEDIUM = "medium"  # Mittlere Rassen
    LARGE = "large"  # Grosse Rassen


class FeedingStage(str, enum.Enum):
    MAINTENANCE = "maintenance"  # Erhaltung
    GROWTH = "growth"  # Wachstum
    GESTATION = "gestation"  # Trächtigkeit
    LACTATION = "lactation"  # Säugezeit


class Tenant(Base):
    """Ein Zuchtbetrieb — der geteilte Datenbestand, den ein oder mehrere
    Logins gemeinsam sehen und bearbeiten (verbunden über den Einlade-Code)."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    invite_code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped["Tenant"] = relationship(back_populates="users")


class UserSession(Base):
    """Angemeldete Sitzung — der Cookie im Browser enthält nur den (zufälligen,
    nicht erratbaren) Token; serverseitig jederzeit widerrufbar."""

    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship()


class Breed(Base):
    __tablename__ = "breeds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    abbreviation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    group: Mapped[BreedGroup | None] = mapped_column(_enum(BreedGroup, "breed_group"), nullable=True)
    min_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    ideal_weight_min_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    ideal_weight_max_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    gestation_days: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Rasse-Tragzeit
    lactation_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Säugezeit-Dauer
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    animals: Mapped[list["Animal"]] = relationship(back_populates="breed")
    scoring_positions: Mapped[list["BreedScoringPosition"]] = relationship(
        back_populates="breed", cascade="all, delete-orphan", order_by="BreedScoringPosition.position_number"
    )
    growth_points: Mapped[list["BreedGrowthPoint"]] = relationship(
        back_populates="breed", cascade="all, delete-orphan", order_by="BreedGrowthPoint.age_weeks"
    )

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_breed_tenant_name"),)


class BreedScoringPosition(Base):
    """Eine Position der Bewertungsskala einer Rasse (Standard CH: 8 Positionen, 100 Punkte)."""

    __tablename__ = "breed_scoring_positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    breed_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("breeds.id"), nullable=False)
    position_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    max_points: Mapped[int] = mapped_column(Integer, nullable=False)

    breed: Mapped["Breed"] = relationship(back_populates="scoring_positions")

    __table_args__ = (UniqueConstraint("breed_id", "position_number", name="uq_breed_position"),)


class BreedGrowthPoint(Base):
    """Stützpunkt einer rassespezifischen Idealgewichtskurve (Alter in Wochen -> Gewicht)."""

    __tablename__ = "breed_growth_points"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    breed_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("breeds.id"), nullable=False)
    age_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_grams: Mapped[int] = mapped_column(Integer, nullable=False)

    breed: Mapped["Breed"] = relationship(back_populates="growth_points")

    __table_args__ = (UniqueConstraint("breed_id", "age_weeks", name="uq_breed_growth_age"),)


class StallPage(Base):
    """Eine Seite/ein Bereich des Stallplans (z.B. 'Scheune', 'Aussenstall'), die
    mehrere Ställe nebeneinander gruppiert."""

    __tablename__ = "stall_pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    stalls: Mapped[list["Stall"]] = relationship(back_populates="page", order_by="Stall.position")


class Stall(Base):
    """Ein Stall als Raster aus Boxen (z.B. 3 Kästen hoch, 2 breit)."""

    __tablename__ = "stalls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    page_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stall_pages.id"), nullable=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    rows: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    columns: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    page: Mapped["StallPage | None"] = relationship(back_populates="stalls")
    boxes: Mapped[list["CageBox"]] = relationship(
        back_populates="stall", cascade="all, delete-orphan", order_by="CageBox.row_index, CageBox.col_index"
    )


class CageBox(Base):
    """Eine einzelne Box/ein einzelner Käfig an einer Rasterposition im Stall."""

    __tablename__ = "cage_boxes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    stall_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stalls.id"), nullable=False)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    col_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    stall: Mapped["Stall"] = relationship(back_populates="boxes")
    animals: Mapped[list["Animal"]] = relationship(back_populates="cage_box")

    __table_args__ = (UniqueConstraint("stall_id", "row_index", "col_index", name="uq_stall_grid_position"),)


class Feed(Base):
    """Ein Futterprodukt mit Nährwertangaben."""

    __tablename__ = "feeds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    energy_mj_per_kg: Mapped[float] = mapped_column(Float, nullable=False)
    crude_protein_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    crude_fiber_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    crude_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    container_capacity_grams: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    animals: Mapped[list["Animal"]] = relationship(back_populates="feed")


class Animal(Base):
    __tablename__ = "animals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    chip_number: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    tattoo_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sex: Mapped[Sex] = mapped_column(_enum(Sex, "sex"), nullable=False, default=Sex.UNKNOWN)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[AnimalStatus] = mapped_column(
        _enum(AnimalStatus, "animal_status"), nullable=False, default=AnimalStatus.ACTIVE
    )
    color_variant: Mapped[str | None] = mapped_column(String(120), nullable=True)  # Farbenschlag
    litter_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[BreedingCategory] = mapped_column(
        _enum(BreedingCategory, "breeding_category"), nullable=False, default=BreedingCategory.YOUNG
    )
    feeding_stage: Mapped[FeedingStage] = mapped_column(
        _enum(FeedingStage, "feeding_stage"), nullable=False, default=FeedingStage.MAINTENANCE
    )
    mating_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Deckdatum
    target_weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_date_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    breed_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("breeds.id"), nullable=True)
    cage_box_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cage_boxes.id", ondelete="SET NULL"), nullable=True
    )
    feed_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("feeds.id"), nullable=True)
    mother_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("animals.id", ondelete="SET NULL"), nullable=True)
    father_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("animals.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    breed: Mapped["Breed | None"] = relationship(back_populates="animals")
    cage_box: Mapped["CageBox | None"] = relationship(back_populates="animals")
    feed: Mapped["Feed | None"] = relationship(back_populates="animals")
    mother: Mapped["Animal | None"] = relationship(remote_side=[id], foreign_keys=[mother_id])
    father: Mapped["Animal | None"] = relationship(remote_side=[id], foreign_keys=[father_id])

    weight_entries: Mapped[list["WeightEntry"]] = relationship(
        back_populates="animal", cascade="all, delete-orphan", order_by="WeightEntry.measured_on"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="animal", cascade="all, delete-orphan", order_by="Evaluation.evaluated_on"
    )

    __table_args__ = (UniqueConstraint("tenant_id", "chip_number", name="uq_animal_tenant_chip"),)


class WeightEntry(Base):
    __tablename__ = "weight_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    animal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("animals.id"), nullable=False)
    measured_on: Mapped[date] = mapped_column(Date, nullable=False)
    weight_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    animal: Mapped["Animal"] = relationship(back_populates="weight_entries")

    __table_args__ = (UniqueConstraint("animal_id", "measured_on", name="uq_weight_animal_date"),)


class Evaluation(Base):
    """Bewertungskarte einer Ausstellung (Standard CH: 8 Positionen, 100 Punkte)."""

    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    animal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("animals.id"), nullable=False)
    evaluated_on: Mapped[date] = mapped_column(Date, nullable=False)
    show_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    exhibitor_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    exhibitor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    exhibitor_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    total_score: Mapped[float | None] = mapped_column(nullable=True)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual | scan
    confirmed: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    animal: Mapped["Animal"] = relationship(back_populates="evaluations")
    scores: Mapped[list["EvaluationScore"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan", order_by="EvaluationScore.position_number"
    )


class EvaluationScore(Base):
    """Einzelne Bewertungsposition einer Bewertungskarte (z.B. Fell: 18.5)."""

    __tablename__ = "evaluation_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluations.id"), nullable=False)
    position_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category_label: Mapped[str] = mapped_column(String(120), nullable=False)
    max_points: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    points: Mapped[float] = mapped_column(nullable=False)

    evaluation: Mapped["Evaluation"] = relationship(back_populates="scores")
