"""Launch the thin installed shared-project browser interface."""

import signal
import threading

from ._gui_http import Server
from ._gui_state import Controller


def serve(workspace, *, port=0, runtime_attachment=None, ready=None):
    controller = Controller(workspace, runtime_attachment=runtime_attachment)
    server = None
    serving = None
    previous = {}
    try:
        server = Server(controller, port)

        def stop(_number, _frame):
            server.request_stop()

        for number in (
            signal.SIGINT,
            signal.SIGTERM,
            *([signal.SIGHUP] if hasattr(signal, "SIGHUP") else []),
        ):
            previous[number] = signal.signal(number, stop)
        if ready is not None:
            # The private owner can disappear during its readiness handshake.
            # Start the loop first, so shutdown never waits on an unstarted loop.
            serving = threading.Thread(
                target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=False
            )
            serving.start()
            ready(server)
            serving.join()
        else:
            print("OpenT1D project GUI: " + server.origin, flush=True)
            print("OpenT1D Study workbench: " + server.origin + "/workbench", flush=True)
            print(
                "Closing a browser tab keeps work running. Use Stop server or Ctrl+C "
                "to stop runs and finish project actions.",
                flush=True,
            )
            server.serve_forever(poll_interval=0.2)
    finally:
        if server is not None:
            if serving is not None:
                server.request_stop()
                serving.join()
            server.server_close()
        controller.close()
        for number, handler in previous.items():
            signal.signal(number, handler)
