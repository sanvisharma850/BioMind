import time
from functools import wraps


def timed(func):

    @wraps(func)
    def wrapper(state):

        start = time.perf_counter()

        result = func(state)

        elapsed = time.perf_counter() - start

        state.setdefault("timings", {})
        state["timings"][func.__name__] = round(elapsed, 3)

        print(f"{func.__name__}: {elapsed:.3f}s")

        return result

    return wrapper