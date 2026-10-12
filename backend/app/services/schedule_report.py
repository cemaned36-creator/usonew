class ScheduleReport:

    def __init__(self):

        self.total = 0

        self.created = 0

        self.failed = 0

        self.reasons = []


    def add_success(self):

        self.created += 1


    def add_failure(
        self,
        lesson_id,
        reason
    ):

        self.failed += 1

        self.reasons.append(
            {
                "lesson_id": lesson_id,
                "reason": reason
            }
        )


    def print(self):

        print("\n====== ОТЧЁТ ======")

        print(
            f"Всего занятий: {self.total}"
        )

        print(
            f"Назначено: {self.created}"
        )

        print(
            f"Не назначено: {self.failed}"
        )


        if self.reasons:

            print("\nПричины:")

            for item in self.reasons:

                print(
                    f"Занятие {item['lesson_id']}: "
                    f"{item['reason']}"
                )