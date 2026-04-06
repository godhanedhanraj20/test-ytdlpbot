# In-memory set of user IDs currently performing a download or extraction
_active_users = set()

def acquire_lock(user_id: int) -> bool:
    if user_id in _active_users:
        return False
    _active_users.add(user_id)
    return True

def release_lock(user_id: int):
    if user_id in _active_users:
        _active_users.remove(user_id)
