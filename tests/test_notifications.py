"""Tests for notification scheduling logic."""
from __future__ import annotations
import uuid, sys, types
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest

# Stub out external deps
for mod_name in ['firebase_admin', 'firebase_admin.auth', 'google', 'google.cloud', 'google.cloud.firestore']:
    if mod_name not in sys.modules:
        m = types.ModuleType(mod_name)
        if mod_name == 'firebase_admin':
            m._apps = {}
            m.initialize_app = lambda: None
        sys.modules[mod_name] = m

db_stub = types.ModuleType('db')
db_stub.get_client = MagicMock()
sys.modules.setdefault('db', db_stub)

from models import NotificationRule, Occurrence, OccurrenceOverrides, Series, ScheduleRule, Room, DeliveryLog


def _rm(room_id='ws1', members=None):
    members = members or {'uid-a': 'organizer', 'uid-b': 'participant'}
    return Room(room_id=room_id, title='Test WS', type='shared', timezone='UTC', owner_uids=['uid-a'], member_roles=members)


def _series(room_id='ws1'):
    return Series(series_id='series-1', room_id=room_id, kind='meeting', title='Weekly Standup', schedule_rule=ScheduleRule(frequency='weekly', weekdays=[1]), default_time='10:00', default_duration_minutes=30)


def _occ(minutes_from_now=30, room_id='ws1'):
    dt = datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)
    return Occurrence(occurrence_id=str(uuid.uuid4()), series_id='series-1', room_id=room_id, scheduled_for=dt.isoformat(), status='scheduled')


def _rule(room_id='ws1', remind_before_minutes=60, target_roles=None, channel='in_app'):
    return NotificationRule(rule_id=str(uuid.uuid4()), room_id=room_id, series_id=None, channel=channel, remind_before_minutes=remind_before_minutes, enabled=True, target_roles=target_roles or [])


class TestOccurrencesInWindow:
    def test_occurrence_in_window(self):
        from jobs.send_notifications import _occurrences_in_window
        occ = _occ(minutes_from_now=30)
        rule = _rule(remind_before_minutes=60)
        now = datetime.now(timezone.utc)
        with patch('series_storage.list_occurrences_for_room', return_value=[occ]):
            result = _occurrences_in_window('ws1', rule, now)
        assert len(result) == 1
        assert result[0].occurrence_id == occ.occurrence_id

    def test_occurrence_outside_window(self):
        from jobs.send_notifications import _occurrences_in_window
        occ = _occ(minutes_from_now=120)
        rule = _rule(remind_before_minutes=30)
        now = datetime.now(timezone.utc)
        with patch('series_storage.list_occurrences_for_room', return_value=[occ]):
            result = _occurrences_in_window('ws1', rule, now)
        assert result == []

    def test_occurrence_in_past_excluded(self):
        from jobs.send_notifications import _occurrences_in_window
        occ = _occ(minutes_from_now=-10)
        rule = _rule(remind_before_minutes=60)
        now = datetime.now(timezone.utc)
        with patch('series_storage.list_occurrences_for_room', return_value=[occ]):
            result = _occurrences_in_window('ws1', rule, now)
        assert result == []

    def test_series_filter(self):
        from jobs.send_notifications import _occurrences_in_window
        occ = _occ(minutes_from_now=30)
        occ.series_id = 'other-series'
        rule = _rule(remind_before_minutes=60)
        rule.series_id = 'series-1'
        now = datetime.now(timezone.utc)
        with patch('series_storage.list_occurrences_for_room', return_value=[occ]):
            result = _occurrences_in_window('ws1', rule, now)
        assert result == []


class TestMembersForRule:
    def test_all_members_when_no_target_roles(self):
        from jobs.send_notifications import _members_for_rule
        rm = _rm(members={'uid-a': 'organizer', 'uid-b': 'participant'})
        rule = _rule(target_roles=[])
        result = _members_for_rule(rm, rule)
        assert set(result) == {'uid-a', 'uid-b'}

    def test_filtered_by_role(self):
        from jobs.send_notifications import _members_for_rule
        rm = _rm(members={'uid-a': 'organizer', 'uid-b': 'participant', 'uid-c': 'organizer'})
        rule = _rule(target_roles=['organizer'])
        result = _members_for_rule(rm, rule)
        assert set(result) == {'uid-a', 'uid-c'}

    def test_no_matching_role(self):
        from jobs.send_notifications import _members_for_rule
        rm = _rm(members={'uid-a': 'participant'})
        rule = _rule(target_roles=['teacher'])
        result = _members_for_rule(rm, rule)
        assert result == []


class TestRunScheduler:
    def _db_mock(self, room_id):
        doc_mock = MagicMock()
        doc_mock.to_dict.return_value = {'workspace_id': room_id}
        doc_mock.id = room_id
        coll_mock = MagicMock()
        coll_mock.stream.return_value = [doc_mock]
        db = MagicMock()
        db.collection.return_value = coll_mock
        return db

    def test_dispatches_in_app_notification(self):
        from jobs.send_notifications import run_scheduler
        occ = _occ(minutes_from_now=30)
        rule = _rule(remind_before_minutes=60, channel='in_app')
        rm = _rm()
        s = _series()
        with (
            patch('db.get_client', return_value=self._db_mock('ws1')),
            patch('series_storage.list_notification_rules_for_room', return_value=[rule]),
            patch('room_storage.get_room', return_value=rm),
            patch('series_storage.list_occurrences_for_room', return_value=[occ]),
            patch('series_storage.get_series', return_value=s),
            patch('delivery_storage.has_been_delivered', return_value=False),
            patch('delivery_storage.append_delivery_log'),
        ):
            result = run_scheduler(lookahead_minutes=60)
        assert result['dispatched'] == 2  # 2 members
        assert result['skipped'] == 0

    def test_skips_already_delivered(self):
        from jobs.send_notifications import run_scheduler
        occ = _occ(minutes_from_now=30)
        rule = _rule(remind_before_minutes=60, channel='in_app')
        rm = _rm()
        s = _series()
        with (
            patch('db.get_client', return_value=self._db_mock('ws1')),
            patch('series_storage.list_notification_rules_for_room', return_value=[rule]),
            patch('room_storage.get_room', return_value=rm),
            patch('series_storage.list_occurrences_for_room', return_value=[occ]),
            patch('series_storage.get_series', return_value=s),
            patch('delivery_storage.has_been_delivered', return_value=True),
            patch('delivery_storage.append_delivery_log'),
        ):
            result = run_scheduler(lookahead_minutes=60)
        assert result['dispatched'] == 0
        assert result['skipped'] == 2

    def test_disabled_rule_skipped(self):
        from jobs.send_notifications import run_scheduler
        occ = _occ(minutes_from_now=30)
        rule = _rule(remind_before_minutes=60, channel='in_app')
        rule.enabled = False
        rm = _rm()
        s = _series()
        with (
            patch('db.get_client', return_value=self._db_mock('ws1')),
            patch('series_storage.list_notification_rules_for_room', return_value=[rule]),
            patch('room_storage.get_room', return_value=rm),
            patch('series_storage.list_occurrences_for_room', return_value=[occ]),
            patch('series_storage.get_series', return_value=s),
            patch('delivery_storage.has_been_delivered', return_value=False),
            patch('delivery_storage.append_delivery_log'),
        ):
            result = run_scheduler(lookahead_minutes=60)
        assert result['dispatched'] == 0
