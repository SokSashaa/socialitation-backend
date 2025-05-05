from socialize_main.utils.search_role import search_role


def get_role(user):
   return user.role if hasattr(user, 'role') else search_role(user)[1]