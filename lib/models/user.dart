class District {
  final int id;
  final String name;
  final String type; // 'hub' or 'sub'
  final int? forwardingHub;

  District({required this.id, required this.name, required this.type, this.forwardingHub});

  bool get isHub => type == 'hub';

  factory District.fromJson(Map<String, dynamic> json) => District(
        id: json['id'],
        name: json['name'],
        type: json['type'],
        forwardingHub: json['forwarding_hub'],
      );
}

class AppUser {
  final int id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;
  final String phone;
  final String role; // customer / agent / admin
  final int? district;
  final String? districtName;

  AppUser({
    required this.id,
    required this.username,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.phone,
    required this.role,
    this.district,
    this.districtName,
  });

  bool get isAgent => role == 'agent';
  bool get isAdmin => role == 'admin';
  bool get isCustomer => role == 'customer';

  String get fullName => [firstName, lastName].where((s) => s.isNotEmpty).join(' ');

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'],
        username: json['username'] ?? '',
        email: json['email'] ?? '',
        firstName: json['first_name'] ?? '',
        lastName: json['last_name'] ?? '',
        phone: json['phone'] ?? '',
        role: json['role'] ?? 'customer',
        district: json['district'],
        districtName: json['district_name'],
      );
}
