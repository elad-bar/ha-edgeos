import logging

_LOGGER = logging.getLogger(__name__)

MAX_PARTS = 3
MINIMUM_EDGEOS_VERSION = "1.10"


class VersionCheck:
    def __init__(self):
        self._minimum_version_score = self._get_score(MINIMUM_EDGEOS_VERSION)

    @staticmethod
    def _get_score(version):
        ver_number_arr = version.split(".")

        multiplier = 100000000
        total_version = 0

        max_numbers_to_check = len(ver_number_arr)
        if max_numbers_to_check > MAX_PARTS:
            max_numbers_to_check = MAX_PARTS

        for i in range(0, max_numbers_to_check):
            ver_id = int(ver_number_arr[i]) * multiplier
            total_version = total_version + ver_id

            multiplier = multiplier / 10000

        return total_version

    def is_compatible(self, fw_version):
        version_parts = fw_version.split("v")
        version = version_parts[len(version_parts) - 1]

        version_score = self._get_score(version)

        is_compatible = version_score >= self._minimum_version_score

        return is_compatible
