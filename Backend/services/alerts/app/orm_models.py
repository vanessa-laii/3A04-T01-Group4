from typing import Optional
import datetime
import uuid

from sqlalchemy import Boolean, CheckConstraint, Computed, DateTime, Double, ForeignKeyConstraint, Index, Integer, PrimaryKeyConstraint, SmallInteger, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        CheckConstraint('email_change_confirm_status >= 0 AND email_change_confirm_status <= 2', name='users_email_change_confirm_status_check'),
        PrimaryKeyConstraint('id', name='users_pkey'),
        UniqueConstraint('phone', name='users_phone_key'),
        Index('confirmation_token_idx', 'confirmation_token', postgresql_where="((confirmation_token)::text !~ '^[0-9 ]*$'::text)", unique=True),
        Index('email_change_token_current_idx', 'email_change_token_current', postgresql_where="((email_change_token_current)::text !~ '^[0-9 ]*$'::text)", unique=True),
        Index('email_change_token_new_idx', 'email_change_token_new', postgresql_where="((email_change_token_new)::text !~ '^[0-9 ]*$'::text)", unique=True),
        Index('reauthentication_token_idx', 'reauthentication_token', postgresql_where="((reauthentication_token)::text !~ '^[0-9 ]*$'::text)", unique=True),
        Index('recovery_token_idx', 'recovery_token', postgresql_where="((recovery_token)::text !~ '^[0-9 ]*$'::text)", unique=True),
        Index('users_email_partial_key', 'email', postgresql_where='(is_sso_user = false)', unique=True),
        Index('users_instance_id_email_idx', 'instance_id'),
        Index('users_instance_id_idx', 'instance_id'),
        Index('users_is_anonymous_idx', 'is_anonymous'),
        {'comment': 'Auth: Stores user login data within a secure schema.',
     'schema': 'auth'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    is_sso_user: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'), comment='Auth: Set this column to true when the account comes from SSO. These accounts can have duplicate emails.')
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    instance_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    aud: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    encrypted_password: Mapped[Optional[str]] = mapped_column(String(255))
    email_confirmed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    invited_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    confirmation_token: Mapped[Optional[str]] = mapped_column(String(255))
    confirmation_sent_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    recovery_token: Mapped[Optional[str]] = mapped_column(String(255))
    recovery_sent_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    email_change_token_new: Mapped[Optional[str]] = mapped_column(String(255))
    email_change: Mapped[Optional[str]] = mapped_column(String(255))
    email_change_sent_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_sign_in_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    raw_app_meta_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw_user_meta_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_super_admin: Mapped[Optional[bool]] = mapped_column(Boolean)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    phone: Mapped[Optional[str]] = mapped_column(Text, server_default=text('NULL::character varying'))
    phone_confirmed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    phone_change: Mapped[Optional[str]] = mapped_column(Text, server_default=text("''::character varying"))
    phone_change_token: Mapped[Optional[str]] = mapped_column(String(255), server_default=text("''::character varying"))
    phone_change_sent_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    confirmed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), Computed('LEAST(email_confirmed_at, phone_confirmed_at)', persisted=True))
    email_change_token_current: Mapped[Optional[str]] = mapped_column(String(255), server_default=text("''::character varying"))
    email_change_confirm_status: Mapped[Optional[int]] = mapped_column(SmallInteger, server_default=text('0'))
    banned_until: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    reauthentication_token: Mapped[Optional[str]] = mapped_column(String(255), server_default=text("''::character varying"))
    reauthentication_sent_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    account_information: Mapped[list['AccountInformation']] = relationship('AccountInformation', back_populates='user')


class AccountInformation(Base):
    __tablename__ = 'account_information'
    __table_args__ = (
        CheckConstraint("role::text = ANY (ARRAY['City Operator'::character varying, 'System Administrator'::character varying, 'Public User'::character varying]::text[])", name='role_check'),
        CheckConstraint("role::text = ANY (ARRAY['City Operator'::character varying, 'System Administrator'::character varying, 'Public User'::character varying]::text[])", name='account_information_role_check'),
        ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='CASCADE', name='account_information_user_id_fkey'),
        PrimaryKeyConstraint('accountinfo_id', name='account_information_pkey'),
        UniqueConstraint('email', name='account_information_email_key'),
        UniqueConstraint('username', name='account_information_username_key')
    )

    accountinfo_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))
    last_login: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)

    user: Mapped[Optional['Users']] = relationship('Users', back_populates='account_information')
    configured_alerts_approved_by: Mapped[list['ConfiguredAlerts']] = relationship('ConfiguredAlerts', foreign_keys='[ConfiguredAlerts.approved_by]', back_populates='account_information')
    configured_alerts_operator: Mapped[list['ConfiguredAlerts']] = relationship('ConfiguredAlerts', foreign_keys='[ConfiguredAlerts.operator_id]', back_populates='operator')
    triggered_alerts: Mapped[list['TriggeredAlerts']] = relationship('TriggeredAlerts', back_populates='account_information')


class ConfiguredAlerts(Base):
    __tablename__ = 'configured_alerts'
    __table_args__ = (
        CheckConstraint("alert_visibility::text = ANY (ARRAY['Internal'::character varying, 'Public Facing'::character varying]::text[])", name='configured_alerts_alert_visibility_check'),
        CheckConstraint("environmental_metric::text = ANY (ARRAY['Air Quality'::character varying, 'Temperature'::character varying, 'Humidity'::character varying, 'Noise Levels'::character varying, 'UV Levels'::character varying]::text[])", name='configured_alerts_environmental_metric_check'),
        CheckConstraint("status::text = ANY (ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying]::text[])", name='configured_alerts_status_check'),
        ForeignKeyConstraint(['approved_by'], ['account_information.accountinfo_id'], name='configured_alerts_approved_by_fkey'),
        ForeignKeyConstraint(['operator_id'], ['account_information.accountinfo_id'], name='configured_alerts_operator_id_fkey'),
        PrimaryKeyConstraint('alert_id', name='configured_alerts_pkey')
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    operator_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    environmental_metric: Mapped[str] = mapped_column(String(100), nullable=False)
    geographic_area: Mapped[str] = mapped_column(String(255), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Double(53), nullable=False)
    timeframe_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    alert_visibility: Mapped[str] = mapped_column(String(50), nullable=False)
    alert_name: Mapped[str] = mapped_column(String(255), nullable=False)
    threshold_value_max: Mapped[Optional[float]] = mapped_column(Double(53))
    condition: Mapped[Optional[str]] = mapped_column(String(10), server_default=text("'ABOVE'::character varying"))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('true'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    approval_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    status: Mapped[Optional[str]] = mapped_column(String(50), server_default=text("'pending'::character varying"))

    account_information: Mapped[Optional['AccountInformation']] = relationship('AccountInformation', foreign_keys=[approved_by], back_populates='configured_alerts_approved_by')
    operator: Mapped['AccountInformation'] = relationship('AccountInformation', foreign_keys=[operator_id], back_populates='configured_alerts_operator')
    triggered_alerts: Mapped[list['TriggeredAlerts']] = relationship('TriggeredAlerts', back_populates='alert')


class TriggeredAlerts(Base):
    __tablename__ = 'triggered_alerts'
    __table_args__ = (
        CheckConstraint("alert_severity::text = ANY (ARRAY['Low'::character varying, 'Medium'::character varying, 'High'::character varying, 'Critical'::character varying]::text[])", name='triggered_alerts_alert_severity_check'),
        CheckConstraint("status::text = ANY (ARRAY['active'::character varying, 'acknowledged'::character varying, 'resolved'::character varying, 'dismissed'::character varying]::text[])", name='triggered_alerts_status_check'),
        ForeignKeyConstraint(['acknowledged_by'], ['account_information.accountinfo_id'], name='triggered_alerts_acknowledged_by_fkey'),
        ForeignKeyConstraint(['alert_id'], ['configured_alerts.alert_id'], name='triggered_alerts_alert_id_fkey'),
        PrimaryKeyConstraint('triggered_alert_id', name='triggered_alerts_pkey')
    )

    triggered_alert_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    alert_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    triggered_value: Mapped[float] = mapped_column(Double(53), nullable=False)
    sensor_id: Mapped[Optional[str]] = mapped_column(String(255))
    region: Mapped[Optional[str]] = mapped_column(String(255))
    triggered_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))
    acknowledged_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    is_false_alarm: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    alert_severity: Mapped[Optional[str]] = mapped_column(String(50))
    is_public: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))
    status: Mapped[Optional[str]] = mapped_column(String(50), server_default=text("'active'::character varying"))

    account_information: Mapped[Optional['AccountInformation']] = relationship('AccountInformation', back_populates='triggered_alerts')
    alert: Mapped['ConfiguredAlerts'] = relationship('ConfiguredAlerts', back_populates='triggered_alerts')


class TimeSeriesSensorData(Base):
    """Read-only mirror used by the alerts service for immediate rule evaluation on approval."""
    __tablename__ = 'time_series_sensor_data'

    data_id:          Mapped[uuid.UUID]             = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    sensor_id:        Mapped[str]                   = mapped_column(String(255), nullable=False)
    metric_type:      Mapped[str]                   = mapped_column(String(100), nullable=False)
    metric_value:     Mapped[float]                 = mapped_column(Double(53), nullable=False)
    unit:             Mapped[str]                   = mapped_column(String(50), nullable=False)
    recorded_at:      Mapped[datetime.datetime]     = mapped_column(DateTime(True), nullable=False)
    geographic_zone:  Mapped[str]                   = mapped_column(String(255), nullable=False)
