from datetime import datetime, timedelta

class FeedHelper():
    def __init__(self, start_date_str, minutes_to_advance):
        self.minutes_to_advance = minutes_to_advance
        self.start_date = datetime.strptime(
             start_date_str,"%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ_UTC)
        self.end_date = self.start_date + timedelta(minutes=self.minutes_to_advance)
        self.now = datetime.utcnow().replace(tzinfo=TZ_UTC)
        if self.end_date > self.now:
            self.end_date = self.now
        self.start = False
        self.done = False


    def advance(self):
        """
        Returns True if keep going, False if we already hit the end time and cannot advance
        :return: True or False
        """
        if not self.start:
            self.start = True
            return True

        if self.done:
            return False

        self.start_date = self.end_date
        self.end_date += timedelta(minutes=self.minutes_to_advance)
        if self.end_date > self.now:
            self.end_date = self.now
            self.done = True

        return True


