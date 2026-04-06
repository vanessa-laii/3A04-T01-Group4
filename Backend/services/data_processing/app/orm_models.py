from typing import Optional
import datetime
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, Double, ForeignKeyConstraint, Index, PrimaryKeyConstraint, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass


class SensorMetadata(Base):
    __tablename__ = 'sensor_metadata'
    __table_args__ = (
        PrimaryKeyConstraint('sensor_id', name='sensor_metadata_pkey'),
    )

    sensor_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    sensor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    geographic_zone: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Double(53), nullable=False)
    longitude: Mapped[float] = mapped_column(Double(53), nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(100), nullable=False)
    location_description: Mapped[Optional[str]] = mapped_column(Text)
    installation_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))
    last_maintenance: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255))
    model: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))

    time_series_sensor_data: Mapped[list['TimeSeriesSensorData']] = relationship('TimeSeriesSensorData', back_populates='sensor')


class TimeSeriesSensorData(Base):
    __tablename__ = 'time_series_sensor_data'
    __table_args__ = (
        CheckConstraint("data_quality_flag::text = ANY (ARRAY['valid'::character varying, 'questionable'::character varying, 'invalid'::character varying]::text[])", name='time_series_sensor_data_data_quality_flag_check'),
        CheckConstraint("metric_type::text = ANY (ARRAY['Air Quality'::character varying, 'Temperature'::character varying, 'Humidity'::character varying, 'Noise Levels'::character varying, 'UV Levels'::character varying]::text[])", name='time_series_sensor_data_metric_type_check'),
        ForeignKeyConstraint(['sensor_id'], ['sensor_metadata.sensor_id'], name='time_series_sensor_data_sensor_id_fkey'),
        PrimaryKeyConstraint('data_id', name='time_series_sensor_data_pkey'),
        Index('idx_sensor_data_metric_zone', 'metric_type', 'geographic_zone', 'recorded_at'),
        Index('idx_sensor_data_sensor_recorded', 'sensor_id', 'recorded_at')
    )

    data_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    sensor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Double(53), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    recorded_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    geographic_zone: Mapped[str] = mapped_column(String(255), nullable=False)
    data_quality_flag: Mapped[Optional[str]] = mapped_column(String(50), server_default=text("'valid'::character varying"))
    additional_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    ingested_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))

    sensor: Mapped['SensorMetadata'] = relationship('SensorMetadata', back_populates='time_series_sensor_data')
