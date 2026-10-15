"""
Course    : CSE 351
Assignment: 04
Student   : Sam Bradshaw

Assignment 04: Retrieving Weather Data from a Server
"""

import time
import threading
from common import *
from cse351 import *

THREADS = 20
WORKERS = 10
RECORDS_TO_RETRIEVE = 5000


# ---------------------------------------------------------------------------
# A bounded wrapper around the required Queue351 class.
# Limits each queue to 10 items and safely coordinates concurrent access.
class BoundedQueue:
    def __init__(self):
        self.queue = Queue351()
        self.lock = threading.Lock()
        self.slots = threading.Semaphore(10)
        self.items = threading.Semaphore(0)

    def put(self, item):
        self.slots.acquire()

        with self.lock:
            self.queue.put(item)

        self.items.release()

    def get(self):
        self.items.acquire()

        with self.lock:
            item = self.queue.get()

        self.slots.release()
        return item


# ---------------------------------------------------------------------------
# Thread function that retrieves weather records from the server.
def retrieve_weather_data(command_queue, result_queue):
    while True:
        command = command_queue.get()

        if command is None:
            break

        city, recno = command

        data = get_data_from_server(
            f'{TOP_API_URL}/record/{city}/{recno}'
        )

        if data is not None:
            result_queue.put(
                (data['city'], data['date'], data['temp'])
            )


# ---------------------------------------------------------------------------
# Worker thread that processes weather records.
class Worker(threading.Thread):
    def __init__(self, result_queue, noaa):
        super().__init__()
        self.result_queue = result_queue
        self.noaa = noaa

    def run(self):
        while True:
            record = self.result_queue.get()

            if record is None:
                break

            city, date, temp = record
            self.noaa.add_record(city, date, temp)


# ---------------------------------------------------------------------------
# Stores weather records and calculates average temperatures.
class NOAA:
    def __init__(self):
        self.data = {city: [] for city in CITIES}
        self.lock = threading.Lock()

    def add_record(self, city, date, temp):
        with self.lock:
            self.data[city].append((date, temp))

    def get_temp_details(self, city):
        with self.lock:
            records = self.data[city]

            if not records:
                return 0.0

            total = sum(temp for date, temp in records)
            return total / len(records)


# ---------------------------------------------------------------------------
class Queue351:
    """ This is the queue object to use for this class. Do not modify!! """

    def __init__(self):
        self.__items = []

    def put(self, item):
        assert len(self.__items) <= 10
        self.__items.append(item)

    def get(self):
        return self.__items.pop(0)

    def get_size(self):
        """ Return the size of the queue like queue.Queue does -> Approx size """
        extra = 1 if random.randint(1, 50) == 1 else 0
        if extra > 0:
            extra *= -1 if random.randint(1, 2) == 1 else 1
        return len(self.__items) + extra


# ---------------------------------------------------------------------------
def verify_noaa_results(noaa):

    answers = {
        'sandiego': 14.5004,
        'philadelphia': 14.865,
        'san_antonio': 14.638,
        'san_jose': 14.5756,
        'new_york': 14.6472,
        'houston': 14.591,
        'dallas': 14.835,
        'chicago': 14.6584,
        'los_angeles': 15.2346,
        'phoenix': 12.4404,
    }

    print()
    print('NOAA Results: Verifying Results')
    print('===================================')

    for name in CITIES:
        answer = answers[name]
        avg = noaa.get_temp_details(name)

        if abs(avg - answer) > 0.00001:
            msg = f'FAILED  Expected {answer}'
        else:
            msg = 'PASSED'

        print(f'{name:>15}: {avg:<10} {msg}')

    print('===================================')


# ---------------------------------------------------------------------------
def main():

    log = Log(show_terminal=True, filename_log='assignment.log')
    log.start_timer()

    noaa = NOAA()

    # Start server data loading.
    data = get_data_from_server(f'{TOP_API_URL}/start')

    if data is None:
        print('Could not connect to the server. Start server.py first.')
        return

    # Get the number of records for each city.
    print('Retrieving city details')
    city_details = {}

    print(f'{"City":>15}: Records')
    print('===================================')

    for name in CITIES:
        city_details[name] = get_data_from_server(
            f'{TOP_API_URL}/city/{name}'
        )

        if city_details[name] is None:
            print(f'Could not retrieve details for {name}')
            return

        print(
            f'{name:>15}: Records = '
            f'{city_details[name]["records"]:,}'
        )

    print('===================================')

    # Create the two required bounded queues.
    command_queue = BoundedQueue()
    result_queue = BoundedQueue()

    # Start worker threads first so they can process records immediately.
    workers = []

    for _ in range(WORKERS):
        worker = Worker(result_queue, noaa)
        worker.start()
        workers.append(worker)

    # Start the retrieval threads.
    retrieval_threads = []

    for _ in range(THREADS):
        thread = threading.Thread(
            target=retrieve_weather_data,
            args=(command_queue, result_queue)
        )
        thread.start()
        retrieval_threads.append(thread)

    # Queue all weather-record retrieval commands.
    # The bounded queue ensures no more than 10 commands are waiting.
    for city in CITIES:
        for recno in range(RECORDS_TO_RETRIEVE):
            command_queue.put((city, recno))

    # Tell each retrieval thread to stop after finishing its commands.
    for _ in range(THREADS):
        command_queue.put(None)

    # Wait until all retrieval threads have finished.
    for thread in retrieval_threads:
        thread.join()

    # Tell each worker to stop after processing its queued records.
    for _ in range(WORKERS):
        result_queue.put(None)

    # Wait until all workers have finished processing.
    for worker in workers:
        worker.join()

    # End server - keep this request after all processing is complete.
    data = get_data_from_server(f'{TOP_API_URL}/end')
    print(data)

    # Verify average temperatures.
    verify_noaa_results(noaa)

    log.stop_timer('Run time: ')


if __name__ == '__main__':
    main()