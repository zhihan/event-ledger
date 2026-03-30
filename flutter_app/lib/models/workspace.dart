class Workspace {
  final String workspaceId;
  final String title;
  final String type;
  final String timezone;
  final List<String> ownerUids;
  final Map<String, String> memberRoles;
  final Map<String, Map<String, String?>> memberProfiles;
  final String? description;

  const Workspace({
    required this.workspaceId,
    required this.title,
    required this.type,
    required this.timezone,
    required this.ownerUids,
    required this.memberRoles,
    required this.memberProfiles,
    this.description,
  });

  factory Workspace.fromJson(Map<String, dynamic> json) {
    final roles = <String, String>{};
    (json['member_roles'] as Map<String, dynamic>? ?? {}).forEach((k, v) {
      roles[k] = v as String;
    });
    final profiles = <String, Map<String, String?>>{};
    (json['member_profiles'] as Map<String, dynamic>? ?? {}).forEach((k, v) {
      final m = <String, String?>{};
      (v as Map<String, dynamic>).forEach((pk, pv) {
        m[pk] = pv as String?;
      });
      profiles[k] = m;
    });
    return Workspace(
      workspaceId: json['workspace_id'] as String,
      title: json['title'] as String,
      type: json['type'] as String? ?? 'shared',
      timezone: json['timezone'] as String? ?? 'UTC',
      ownerUids: List<String>.from(json['owner_uids'] ?? []),
      memberRoles: roles,
      memberProfiles: profiles,
      description: json['description'] as String?,
    );
  }
}

class MemberDetail {
  final String uid;
  final String role;
  final String? displayName;
  final String? email;

  const MemberDetail({
    required this.uid,
    required this.role,
    this.displayName,
    this.email,
  });

  factory MemberDetail.fromJson(Map<String, dynamic> json) {
    return MemberDetail(
      uid: json['uid'] as String,
      role: json['role'] as String,
      displayName: json['display_name'] as String?,
      email: json['email'] as String?,
    );
  }
}
