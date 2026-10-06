"""
Course: CSE 351 
Lesson: L03 team activity
File:   team.py
Author: <Add name here>

Purpose: Retrieve Star Wars details from a server

Instructions:

- This program requires that the server.py program be started in a terminal window.
- The program will retrieve the names of:
    - characters
    - planets
    - starships
    - vehicles
    - species

- the server will delay the request by 0.5 seconds

TODO
- Create a threaded function to make a call to the server where
  it retrieves data based on a URL.
- The threaded function should only retrieve one URL.
- Create a queue that will be used between the main thread and the threaded functions

- Speed up this program as fast as you can by:
    - creating as many as you can
    - start them all
    - join them all

"""

from datetime import datetime, timedelta
import threading
import queue
from common import *
# Include cse 351 common Python files
from cse351 import *

# global
call_count = 0
url_queue = queue.Queue()

def worker():
    url = url_queue.get()
    item = get_data_from_server(url)
    print(f'  - {item["name"]}')
    url_queue.task_done()


def get_urls(film6, kind):
    global call_count

    threads = []

    urls = film6[kind]
    print(kind)
    for url in urls:
        call_count += 1

        url_queue.put(url)

        thread = threading.Thread(target=worker)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
        

def main():
    global call_count

    log = Log(show_terminal=True)
    log.start_timer('Starting to retrieve data from the server')

    film6 = get_data_from_server(f'{TOP_API_URL}/films/6')
    call_count += 1
    print_dict(film6)

    # Retrieve people
    get_urls(film6, 'characters')
    get_urls(film6, 'planets')
    get_urls(film6, 'starships')
    get_urls(film6, 'vehicles')
    get_urls(film6, 'species')

    log.stop_timer('Total Time To complete')
    log.write(f'There were {call_count} calls to the server')

if __name__ == "__main__":
    main()
