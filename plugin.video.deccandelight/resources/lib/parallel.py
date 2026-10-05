"""Bounded workers with a responsive deadline and main-thread UI callbacks."""
import queue
import threading
import time


def collect(jobs, function, workers=4, seconds=20, cancelled=lambda: False, progress=None):
    jobs = list(jobs)
    if cancelled():
        return [], bool(jobs)
    pending = queue.Queue()
    output = queue.Queue()
    stop = threading.Event()
    deadline = time.monotonic() + seconds
    for index, job in enumerate(jobs):
        pending.put((index, job))

    def work():
        while not stop.is_set() and time.monotonic() < deadline:
            try:
                index, job = pending.get_nowait()
            except queue.Empty:
                break
            try:
                value = function(job, deadline, stop)
            except Exception:
                value = None
            output.put((index, value))

    for _ in range(min(max(1, workers), len(jobs))):
        threading.Thread(target=work, daemon=True).start()
    results = {}
    try:
        while len(results) < len(jobs) and time.monotonic() < deadline:
            if cancelled():
                break
            try:
                index, value = output.get(timeout=min(0.1, max(0.001, deadline - time.monotonic())))
            except queue.Empty:
                if progress:
                    progress(len(results), len(jobs))
                continue
            results[index] = value
            if progress:
                progress(len(results), len(jobs))
    finally:
        stop.set()
    return [(jobs[index], results[index]) for index in sorted(results)], len(results) < len(jobs)
