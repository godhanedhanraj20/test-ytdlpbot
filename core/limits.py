# In-memory set of user IDs currently performing a download or extraction
_active_users = set()

# In-memory set of user IDs who have requested cancellation of their current task
_cancel_requests = set()

def acquire_lock(user_id: int) -> bool:
    if user_id in _active_users:
        return False
    _active_users.add(user_id)
    return True

def release_lock(user_id: int):
    if user_id in _active_users:
        _active_users.remove(user_id)
    # Also clear any pending cancel requests when releasing lock
    if user_id in _cancel_requests:
        _cancel_requests.remove(user_id)

def request_cancel(user_id: int) -> bool:
    if user_id in _active_users:
        _cancel_requests.add(user_id)
        return True
    return False

def is_cancel_requested(user_id: int) -> bool:
    return user_id in _cancel_requests
