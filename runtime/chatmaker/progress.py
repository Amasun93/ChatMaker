"""Optional progress channel; never writes into the final result on stdout."""
from contextlib import contextmanager
from contextvars import ContextVar
import json
import sys

_listener = ContextVar('chatmaker_progress', default=None)


def emit(event: str, **fields) -> None:
    listener = _listener.get()
    if listener:
        listener({'event': event, **fields})


@contextmanager
def listening(callback):
    token = _listener.set(callback)
    try:
        yield
    finally:
        _listener.reset(token)


@contextmanager
def reporting(mode: str):
    def write(event):
        if mode == 'jsonl':
            print(json.dumps(event, ensure_ascii=True), file=sys.stderr, flush=True)
        elif mode == 'human':
            message = event.get('message') or event['event']
            component = event.get('component', '')
            if event['event'] == 'download_progress':
                size = event.get('total_bytes', 0)
                done = event.get('downloaded', 0)
                message = f"{done / size:.0%}  {done / 1e6:.1f}/{size / 1e6:.1f} MB" if size else str(done)
                speed = event.get('speed_bps', 0)
                if speed:
                    message += f"  {speed / 1e6:.1f} MB/s  ETA {event['eta_seconds']:.0f}s"
            print(f"[ChatMaker] {component} {message}", file=sys.stderr, flush=True)
    with listening(write if mode != 'none' else None):
        yield
