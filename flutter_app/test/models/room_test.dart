import 'package:test/test.dart';
import 'package:event_ledger/models/room.dart';

void main() {
  group('Room.fromJson', () {
    test('parses minimal room', () {
      final json = {
        'room_id': 'rm-1',
        'title': 'Test Room',
        'type': 'shared',
        'timezone': 'Asia/Taipei',
        'owner_uids': ['uid-1'],
        'member_roles': {'uid-1': 'organizer'},
        'member_profiles': {},
      };
      final room = Room.fromJson(json);
      expect(room.roomId, 'rm-1');
      expect(room.title, 'Test Room');
      expect(room.type, 'shared');
      expect(room.timezone, 'Asia/Taipei');
      expect(room.ownerUids, ['uid-1']);
      expect(room.memberRoles, {'uid-1': 'organizer'});
      expect(room.description, isNull);
    });

    test('parses room with member profiles', () {
      final json = {
        'room_id': 'rm-2',
        'title': 'Study Group',
        'type': 'study',
        'timezone': 'UTC',
        'owner_uids': ['uid-1'],
        'member_roles': {'uid-1': 'organizer', 'uid-2': 'participant'},
        'member_profiles': {
          'uid-1': {'display_name': 'Alice', 'email': 'alice@test.com'},
          'uid-2': {'display_name': 'Bob', 'email': null},
        },
        'description': 'A study group',
      };
      final room = Room.fromJson(json);
      expect(room.memberProfiles['uid-1']!['display_name'], 'Alice');
      expect(room.memberProfiles['uid-2']!['email'], isNull);
      expect(room.description, 'A study group');
    });

    test('handles missing optional fields', () {
      final json = {
        'room_id': 'rm-3',
        'title': 'Minimal',
      };
      final room = Room.fromJson(json);
      expect(room.type, 'shared');
      expect(room.timezone, 'UTC');
      expect(room.ownerUids, isEmpty);
      expect(room.memberRoles, isEmpty);
      expect(room.memberProfiles, isEmpty);
    });
  });

  group('MemberDetail.fromJson', () {
    test('parses member detail', () {
      final json = {
        'uid': 'uid-1',
        'role': 'organizer',
        'display_name': 'Alice',
        'email': 'alice@test.com',
      };
      final detail = MemberDetail.fromJson(json);
      expect(detail.uid, 'uid-1');
      expect(detail.role, 'organizer');
      expect(detail.displayName, 'Alice');
      expect(detail.email, 'alice@test.com');
    });

    test('handles null display name and email', () {
      final json = {
        'uid': 'uid-2',
        'role': 'participant',
        'display_name': null,
        'email': null,
      };
      final detail = MemberDetail.fromJson(json);
      expect(detail.displayName, isNull);
      expect(detail.email, isNull);
    });
  });
}
