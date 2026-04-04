from typing import Optional
import datetime
import uuid

from sqlalchemy import Boolean, CheckConstraint, Computed, DateTime, ForeignKeyConstraint, Index, PrimaryKeyConstraint, SmallInteger, String, Text, UniqueConstraint, Uuid, text
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
        CheckConstraint("role::text = ANY (ARRAY['City Operator'::character varying, 'System Administrator'::character varying, 'Public User'::character varying]::text[])", name='account_information_role_check'),
        CheckConstraint("role::text = ANY (ARRAY['City Operator'::character varying, 'System Administrator'::character varying, 'Public User'::character varying]::text[])", name='role_check'),
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
    audit_log_data: Mapped[list['AuditLogData']] = relationship('AuditLogData', back_populates='user')


class AuditLogData(Base):
    __tablename__ = 'audit_log_data'
    __table_args__ = (
        CheckConstraint("event_type::text = ANY (ARRAY['user_login'::character varying, 'user_logout'::character varying, 'user_created'::character varying, 'user_modified'::character varying, 'user_deleted'::character varying, 'alert_created'::character varying, 'alert_modified'::character varying, 'alert_deleted'::character varying, 'alert_triggered'::character varying, 'alert_acknowledged'::character varying, 'alert_verified'::character varying, 'alert_rejected'::character varying, 'data_access'::character varying, 'api_request'::character varying, 'permission_change'::character varying, 'system_event'::character varying, 'error_event'::character varying]::text[])", name='audit_log_data_event_type_check'),
        CheckConstraint("status::text = ANY (ARRAY['success'::character varying, 'failure'::character varying, 'partial'::character varying]::text[])", name='audit_log_data_status_check'),
        ForeignKeyConstraint(['user_id'], ['account_information.accountinfo_id'], name='audit_log_data_user_id_fkey'),
        PrimaryKeyConstraint('log_id', name='audit_log_data_pkey'),
        Index('idx_audit_log_entity', 'entity_type', 'entity_id', 'timestamp'),
        Index('idx_audit_log_event_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_audit_log_timestamp', 'timestamp'),
        Index('idx_audit_log_user_timestamp', 'user_id', 'timestamp')
    )

    log_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100))
    entity_id: Mapped[Optional[str]] = mapped_column(String(255))
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    status: Mapped[Optional[str]] = mapped_column(String(50), server_default=text("'success'::character varying"))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))
    retention_until: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text("(CURRENT_TIMESTAMP + '1 year'::interval)"))

    user: Mapped[Optional['AccountInformation']] = relationship('AccountInformation', back_populates='audit_log_data')
