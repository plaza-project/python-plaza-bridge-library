class ExtraData:
    def __init__(self, user_id, extra_data_dict=None):
        self.user_id = user_id
        if extra_data_dict is None:
            self.extra_data_dict = {}
        else:
            self.extra_data_dict = extra_data_dict

        self._last_monitor_value = self.extra_data_dict.get("last_monitor_value", None)
        if self._last_monitor_value is None:
            self.last_monitor_value = None
        else:
            self.last_monitor_value = self._last_monitor_value.get("value", None)
