from enum import Enum


class StateStatusEnum(str, Enum):

    # Pending
    CREATED = 'CREATED'
    QUEUED = 'QUEUED'
    EXECUTED = 'EXECUTED'

    # Errored
    ERRORED = 'ERRORED'
    NEXT_CREATED_ERROR = 'NEXT_CREATED_ERROR'
    TIMEDOUT = 'TIMEDOUT'

    # Success
    SUCCESS = 'SUCCESS'
    PRUNED = 'PRUNED'

    # Retry
    RETRY_CREATED = 'RETRY_CREATED'