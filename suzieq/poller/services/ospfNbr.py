from datetime import datetime, timedelta
from suzieq.poller.services.service import Service


class OspfNbrService(Service):
    """OSPF Neighbor service. Output needs to be munged"""

    def frr_convert_reltime_to_epoch(self, reltime):
        """Convert string of type 1d12h3m23s into absolute epoch"""
        secs = 0
        s = reltime
        if not reltime:
            return 0

        for t, mul in {
            "w": 3600 * 24 * 7,
            "d": 3600 * 24,
            "h": 3600,
            "m": 60,
            "s": 1,
        }.items():
            v = s.split(t)
            if len(v) == 2:
                secs += int(v[0]) * mul
            s = v[-1]

        return int((datetime.utcnow().timestamp() - secs) * 1000)

    def clean_data(self, processed_data, raw_data):

        dev_type = raw_data.get("devtype", None)
        if dev_type == "cumulus" or dev_type == "linux":
            processed_data = self._clean_linux_data(processed_data, raw_data)
        elif dev_type == "eos":
            processed_data = self._clean_eos_data(processed_data, raw_data)
        elif dev_type == "junos":
            processed_data = self._clean_junos_data(processed_data, raw_data)

        return super().clean_data(processed_data, raw_data)

    def _clean_linux_data(self, processed_data, raw_data):
        for entry in processed_data:
            entry["vrf"] = "default"
            entry["state"] = entry["state"].lower()
            entry["lastUpTime"] = self.frr_convert_reltime_to_epoch(
                entry["lastUpTime"]
            )
            entry["lastDownTime"] = self.frr_convert_reltime_to_epoch(
                entry["lastDownTime"]
            )
            if entry["lastUpTime"] > entry["lastDownTime"]:
                entry["lastChangeTime"] = entry["lastUpTime"]
            else:
                entry["lastChangeTime"] = entry["lastDownTime"]
            entry["areaStub"] = entry["areaStub"] == "[Stub]"
            if not entry["bfdStatus"]:
                entry["bfdStatus"] = "disabled"

        return processed_data

    def _clean_eos_data(self, processed_data, raw_data):
        for entry in processed_data:
            entry["state"] = entry["state"].lower()
            entry["lastChangeTime"] = int(entry["lastChangeTime"] * 1000)
            # What is provided is the opposite of stub and so we not it
            entry["areaStub"] = not entry["areaStub"]

        return processed_data

    def _clean_junos_data(self, processed_data, raw_data):
        for entry in processed_data:
            vrf = entry['vrf'][0]['data']
            if vrf == "master":
                entry['vrf'] = "default"
            else:
                entry['vrf'] = vrf

            entry['ifname'] = entry['ifname'].replace('/', '-')
            hours, minutes, seconds = entry['lastChangeTime'].split(':')
            entry['lastChangeTime'] = int(
                (datetime.utcnow().timestamp() -
                 timedelta(hours=int(hours), minutes=int(minutes),
                           seconds=int(seconds)).seconds))*1000

        return processed_data
