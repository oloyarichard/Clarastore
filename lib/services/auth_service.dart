import '../core/api_client.dart';
import '../core/token_storage.dart';
import '../models/user.dart';

class AuthService {
  final _dio = ApiClient.instance.dio;

  Future<AppUser> register({
    required String email,
    required String password,
    required String passwordConfirm,
    required String firstName,
    required String lastName,
    required String phone,
    required int districtId,
  }) async {
    final resp = await _dio.post('/auth/register/', data: {
      'email': email,
      'password': password,
      'password_confirm': passwordConfirm,
      'first_name': firstName,
      'last_name': lastName,
      'phone': phone,
      'district': districtId,
    });
    return AppUser.fromJson(resp.data['user']);
  }

  /// Logs in, stores the JWT pair, and returns the freshly-fetched profile
  /// (login itself only returns tokens, not user details).
  Future<AppUser> login({required String email, required String password}) async {
    final resp = await _dio.post('/auth/login/', data: {
      'email': email,
      'password': password,
    });
    await TokenStorage.saveTokens(access: resp.data['access'], refresh: resp.data['refresh']);
    final profile = await getProfile();
    await TokenStorage.saveRole(profile.role);
    return profile;
  }

  Future<AppUser> getProfile() async {
    final resp = await _dio.get('/auth/profile/');
    return AppUser.fromJson(resp.data);
  }

  Future<AppUser> updateProfile(Map<String, dynamic> fields) async {
    final resp = await _dio.patch('/auth/profile/', data: fields);
    return AppUser.fromJson(resp.data);
  }

  Future<List<District>> getDistricts() async {
    final resp = await _dio.get('/auth/districts/');
    final results = resp.data is Map && resp.data['results'] != null ? resp.data['results'] : resp.data;
    return (results as List).map((e) => District.fromJson(e)).toList();
  }

  Future<void> logout() => TokenStorage.clearAuth();
}
