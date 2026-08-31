from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin_role


class IsAgent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_agent


class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_customer


class IsOrderOwnerOrAgent(permissions.BasePermission):
    """
    Custom permission to only allow owners of an order or assigned agents to view it.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin_role:
            return True
        if user.is_agent and obj.assigned_agent == user:
            return True
        # Deliberately role-agnostic — being the actual recipient of
        # this specific order is what grants access, not whether the
        # account's overall role happens to be labeled 'customer'. An
        # agent buying something for themselves is still obj.customer
        # on that order and needs the same access a customer account
        # would get.
        if obj.customer == user:
            return True
        return False
