# -*- coding: utf-8 -*-
import time
import select

try:
    from enum import Enum       # 默认使用Python带有的枚举，更加安全，在2.7下，需要pip install enum34，3.4之上默认带有enum
    class PollerMask(Enum):
        POLLERREAD = 0
        POLLERWRITE = 1
        POLLERERROR = 2
except ImportError as e:
    class PollerMask():         # 如果当前环境缺少enum，则使用class简单模拟枚举，也可以达到目的，但不够安全
        POLLERREAD = 0
        POLLERWRITE = 1
        POLLERERROR = 2


class Poller(object):       # factory
    def __init__(self):
        try:
            # raise ImportError     # 测试select时使用
            from select import epoll    # 默认使用Epoll，因为Epoll比select有更好的性能表现
            self.poller = EpollPoller()
        except ImportError as e:
            self.poller = SelectPoller()

    def register(self, fd, mask):
        self.poller.register(fd, mask)

    def modify(self, fd, mask):
        self.poller.modify(fd, mask)

    def unregister(self, fd):
        self.poller.unregister(fd)

    def poll(self, timeout):
        return self.poller.poll(timeout)

class SelectPoller(object):
    def __init__(self):
        self.fds = set()        # 保存信息，（fd,mask）

    def register(self, fd, mask):
        self.fds.add((fd, mask))

    def modify(self, fd, mask):
        self.fds.add((fd, mask))

    def unregister(self, fd):
        if (fd, PollerMask.POLLERREAD) in self.fds:
            self.fds.remove((fd, PollerMask.POLLERREAD))
        if (fd, PollerMask.POLLERWRITE) in self.fds:
            self.fds.remove((fd, PollerMask.POLLERWRITE))
        if (fd, PollerMask.POLLERERROR) in self.fds:
            self.fds.remove((fd, PollerMask.POLLERERROR))


    def poll(self, timeout):
        inputs = []
        outputs = []
        for elem in self.fds:
            if elem[1] is PollerMask.POLLERREAD:
                inputs.append(elem[0])
            elif elem[1] is PollerMask.POLLERWRITE:
                outputs.append(elem[0])
            elif elem[1] is PollerMask.POLLERERROR:
                pass
        reads, writes, errors = select.select(inputs, outputs, inputs, timeout)
        results = set()
        # 错误使用，在这里不能这样使用生成器来添加元素
        # results.add(((read, PollerMask.POLLERREAD) for read in reads))
        # results.add(((write, PollerMask.POLLERWRITE) for write in writes))
        # results.add(((error, PollerMask.POLLERERROR) for error in errors))
        for read in reads:
            results.add((read, PollerMask.POLLERREAD))
        for write in writes:
            results.add((write, PollerMask.POLLERWRITE))
        for error in errors:
            results.add((error, PollerMask.POLLERERROR))
        return results


class EpollPoller(object):
    def __init__(self):
        self.poller = select.epoll()
        self.fileno_sock = dict()
        self.sock_fileno = dict()

    # @profile
    def __map_mask(self, mask):
        if mask is PollerMask.POLLERREAD:
            return select.EPOLLIN
        elif mask is PollerMask.POLLERWRITE:
            return select.EPOLLOUT
        elif mask is PollerMask.POLLERERROR:
            return select.EPOLLERR

    # @profile
    def __reverse_map_mask(self, mask):
        if mask is select.EPOLLIN:
            return PollerMask.POLLERREAD
        elif mask is select.EPOLLOUT:
            return PollerMask.POLLERWRITE
        elif mask is select.EPOLLERR:
            return PollerMask.POLLERERROR

    # @profile
    def register(self, fd, mask):
        if self.sock_fileno.has_key(fd):
            self.poller.modify(self.sock_fileno[fd], self.__map_mask(mask))       # 传递fileno而不是fd,可以减少fileno（）操作的时间，fileno（）是一个耗时操作
        else:
            fileno = fd.fileno()
            self.fileno_sock[fileno] = fd
            self.sock_fileno[fd] = fileno
            self.poller.register(fileno, self.__map_mask(mask))

    # @profile
    def modify(self, fd, mask):
        self.poller.modify(self.sock_fileno[fd], self.__map_mask(mask))

    # @profile
    def unregister(self, fd):
        del self.fileno_sock[self.sock_fileno[fd]]          # 必须删除记录，否则会出现socket未注册却被检测为已经注册的状况
        self.poller.unregister(self.sock_fileno[fd])
        del self.sock_fileno[fd]                            # 必须删除记录，否则会出现socket未注册却被检测为已经注册的状况

    # @profile
    def poll(self, timeout):
        events = self.poller.poll(timeout)
        results = set()
        for fd, mask in events:
            if mask & select.EPOLLIN:
                results.add((self.fileno_sock[fd], PollerMask.POLLERREAD))
            elif mask & select.EPOLLOUT:
                results.add((self.fileno_sock[fd], PollerMask.POLLERWRITE))
            elif mask & select.EPOLLHUP:
                results.add((self.fileno_sock[fd], PollerMask.POLLERERROR))
        return results








