from locust import HttpLocust, TaskSet, task


class MyTaskSet(TaskSet):
    @task
    def my_task(self):
        self.client.get("/")


class MyLocust(HttpLocust):
    host = "http://example.org"
    min_wait = 1000
    max_wait = 1000
    task_set = MyTaskSet