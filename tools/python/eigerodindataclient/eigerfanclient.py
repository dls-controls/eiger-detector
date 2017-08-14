import sys

sys.path.insert(
    0, "/dls_sw/work/tools/RHEL6-x86_64/odin/odin-data/tools/python")
from common import ZMQClient


class EigerFanClient(ZMQClient):

    CTRL_PORT = 5559

    STATE = "state"
    CONSUMERS = "num_connected"
    SERIES = "series"
    FRAME = "frame"

    def __init__(self, ip_address, lock):
        super(EigerFanClient, self).__init__(ip_address, lock, 0)

    def request_status(self):
        return self.send_request("status")["params"]

    def request_latest_frame(self):
        status = self.request_status()
        return status["frame"]

    def current_consumers(self):
        status = self.request_status()
        return status[self.CONSUMERS]

    def rewind(self, frames, active_frame):
        config = {
            "frames": int(frames),
            "active_frame": int(active_frame)
        }
        self.send_configuration("rewind", config)

    def stop(self):
        config = {
            "close": True
        }
        self.send_configuration_dict(**config)

    def kill(self):
        config = {
            "kill": True,
        }
        self.send_configuration_dict(**config)
