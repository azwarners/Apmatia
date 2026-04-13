class YsparrError(Exception):
    pass

class ExecutionError(YsparrError):
    pass

class StorageError(YsparrError):
    pass

class BackendError(YsparrError):
    pass
