"""Launch the thin installed shared-project browser interface."""

import signal

from ._gui_http import Server
from ._gui_state import Controller


def serve(workspace, *, port=0, runtime_attachment=None):
    controller = Controller(workspace, runtime_attachment=runtime_attachment)
    server = None
    previous = {}
    try:
        server = Server(controller, port)

        def stop(_number, _frame):
            server.request_stop()

        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[number] = signal.signal(number, stop)
        print("OpenT1D project GUI: " + server.origin, flush=True)
        print(
            "Closing a browser tab keeps work running. Use Stop server or Ctrl+C "
            "to stop runs and finish project actions.",
            flush=True,
        )
        server.serve_forever(poll_interval=0.2)
    finally:
        if server is not None:
            server.server_close()
        controller.close()
        for number, handler in previous.items():
            signal.signal(number, handler)
