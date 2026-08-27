import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Wraps flutter_secure_storage for the handful of values we need to
/// persist across app restarts: the JWT pair, and a guest cart session key
/// (used before a customer signs up, per the guest-browsing decision).
class TokenStorage {
  static const _storage = FlutterSecureStorage();

  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';
  static const _roleKey = 'user_role';
  static const _sessionKeyKey = 'guest_session_key';

  static Future<void> saveTokens({required String access, required String refresh}) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
  }

  static Future<String?> getAccessToken() => _storage.read(key: _accessKey);
  static Future<String?> getRefreshToken() => _storage.read(key: _refreshKey);

  static Future<void> saveRole(String role) => _storage.write(key: _roleKey, value: role);
  static Future<String?> getRole() => _storage.read(key: _roleKey);

  static Future<void> saveGuestSessionKey(String key) =>
      _storage.write(key: _sessionKeyKey, value: key);
  static Future<String?> getGuestSessionKey() => _storage.read(key: _sessionKeyKey);
  static Future<void> clearGuestSessionKey() => _storage.delete(key: _sessionKeyKey);

  static Future<void> clearAuth() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    await _storage.delete(key: _roleKey);
  }

  static Future<bool> hasValidSession() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }
}
