"""
Database router for sync_manager.
sqlite_cache is managed manually — Django won't auto-migrate it.
"""


class SyncRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Only allow automatic migrations on 'default'
        # sqlite_cache migrations are run explicitly in run_server.py
        if db == 'sqlite_cache':
            return False
        return None

    def db_for_read(self, model, **hints):
        return None  # use default routing

    def db_for_write(self, model, **hints):
        return None  # use default routing

    def allow_relation(self, obj1, obj2, **hints):
        return None
