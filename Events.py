# -*- coding: utf-8 -*-
from poller import *
from timer import *
from Queue import Queue

class Events(object):
    def __init__(self):
        self.poller = Poller()
        self.timer = Timer()
        self.file_proc = dict()
        self.file_events = FileEvents()
        self.time_events = TimeEvents()
        self.file_scheduler = FileSchecduler()
        self.time_scheduler = TimeSchecduler()
        self.time_id_generator = IDGenerator()

    def add_file_event(self, fd, mask, file_proc, client_data = None):
        self.poller.register(fd, mask)
        self.file_proc[(fd, mask)] = file_proc
        self.file_events.put(self, fd, mask, file_proc, client_data)

    def remove_file_event(self, fd):
        self.poller.unregister(fd)


    def add_time_event(self, sec, mask, time_proc, client_data = None):
        event_id = self.time_id_generator.get()
        self.time_events.put(self, event_id, mask, sec, time_proc, client_data)
        self.timer.register(event_id, sec, mask)

    def __process_event(self):
        pass

    def run(self):
        # process time event
        while 1:
            time_events = self.timer.poll()
            # print "time events", time_events
            for id in time_events:
                self.time_scheduler.add_event(self.time_events.get(id))
            self.time_scheduler.process_event()
            # print self.timer.latest_timespan_value, self.timer.latest_timespan()
            file_events = self.poller.poll(self.timer.latest_timespan())
            # print "file events", file_events, len(file_events)
            for fd, mask in file_events:
                self.file_scheduler.add_event(self.file_events.get(fd, mask))
            self.file_scheduler.process_event()

# FileEvents独立为一个类，保证可扩展
class FileEvents(object):
    def __init__(self):
        self.events = dict()

    def put(self, events, fd, mask, file_proc, client_data = None):
        self.events[(fd, mask)] = FileEvent(events, fd, mask, file_proc, client_data)   # 必须添加events，否则无法添加fd来监听

    def clear(self):
        pass

    def get(self, fd, mask):
        return self.events[(fd, mask)]

class FileEvent(object):
    def __init__(self, events, fd, mask, proc, client_data):
        self.events = events
        self.fd = fd
        self.mask = mask
        self.proc = proc
        self.client_data = client_data

class TimeEvents(object):
    def __init__(self):
        self.events = dict()

    def put(self, events, event_id, mask, sec, time_proc, client_data):
        self.events[event_id] = TimeEvent(events, event_id, mask, sec, time_proc, client_data)

    def clear(self):
        pass

    def get(self, event_id):
        return self.events[event_id]

class TimeEvent(object):
    def __init__(self, events, event_id, mask, sec, time_proc, client_data):
        self.events = events
        self.event_id = event_id
        self.mask = mask
        self.sec = sec
        self.time_proc = time_proc
        self.client_data = client_data


def process_file_event(event_queue):     # 默认单线程，未考虑并发执行的资源竞争问题
    while not event_queue.empty():
        event = event_queue.get()
        event.proc(event)


class FileSchecduler(object):
    def __init__(self):
        self.event_queue = Queue()
        self.__proc_event = process_file_event

    def add_event(self, file_event):
        self.event_queue.put(file_event)

    def set_process_event(self, process_event):
        self.__proc_event = process_event

    def process_event(self):
        self.__proc_event(self.event_queue)

def process_time_event(event_queue):
    while not event_queue.empty():
        event = event_queue.get()
        event.time_proc(event)

class TimeSchecduler(object):
    def __init__(self):
        self.event_queue = Queue()
        self.__proc_event = process_time_event

    def add_event(self, time_event):
        self.event_queue.put(time_event)

    def set_process_event(self, process_event):
        self.__proc_event = process_event

    def process_event(self):
        self.__proc_event(self.event_queue)

class EventFactory(object):
    pass

class IDGenerator(object):
    def __init__(self, floor = 0, ceiling = 256):
        self.free = list()
        self.used = list()
        self.__generator_id(floor, ceiling)


    def __generator_id(self, floor, ceiling):
        for x in xrange(floor, ceiling + 1):
            self.free.append(x)

    def get(self):
        ID = self.free.pop()
        self.used.append(ID)
        return ID

    def remove(self, ID):
        self.used.remove(ID)
        self.free.append(ID)