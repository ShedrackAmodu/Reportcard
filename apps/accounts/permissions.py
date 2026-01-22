from rest_framework import permissions

class IsSchoolMember(permissions.BasePermission):
	"""
	Allow access only when request.school is set and matches object's school FK.
	"""
	def has_permission(self, request, view):
		return bool(getattr(request, "school", None) or (request.user and request.user.is_authenticated))

	def has_object_permission(self, request, view, obj):
		obj_school = getattr(obj, "school", None)
		return obj_school is None or obj_school == getattr(request, "school", None)