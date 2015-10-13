from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import tornado.ioloop
import tornado.web
from tornado import gen

import datetime
import pymongo.errors
import motor

import ujson
import jsonschema


from metadataservice.server import utils


""".. note
    ultra-json is 3-5 orders of magnitude faster since it runs outside GIL.
    bson.json_util does encode/decode neatly but painfully slow normalize object fields manually.
    Early alpha. Might go under some changes. Handlers and dataapi are unlikely to change.
"""

CACHE_SIZE = 10000


def db_connect(database ,host, port, replicaset=None, write_concern="majority",
               write_timeout=1000):
    """Helper function to deal with stateful connections to motor.
    Connection established lazily. Asycnc so do not treat like mongonengine connection pool.

    Parameters
    ----------
    server: str
        The name of the server that data is stored
    host: str
        Name/address of the server that mongo daemon lives
    port: int
        Port num of the server
    replicaset: str
        Name of the replica set. Configured within mongo deployment.
    write_concern: int
        Traditional mongo write concern. Int denotes number of replica set writes
        to be verified

    write_timeout: int
        Time tolerance before write fails. Affects the package size in bulk insert so use wisely

    Returns motor.MotorDatabase
    -------
        Async server object which comes in handy as server has to juggle multiple clients
        and makes no difference for a single client compared to pymongo
    """
    client = motor.MotorClient(host, port, replicaset=replicaset)
    client.write_concern = {'w': write_concern, 'wtimeout': write_timeout}
    database = client[database]
    return database


class RunStartHandler(tornado.web.RequestHandler):
    """Handler for run_start insert and query operations.
    Uses traditional RESTful lingo. get for querying and post for inserts
    
   Methods
    -------
    get()
        Query run_start documents.Very thin as we do not want to create a
        bottleneck dealing with multiple clients. self.write() dumps the json to
        socket. Client keeps connection open until server kills the socket with
        self.finish(), otherwise keeps hanging wasting resources
    post()
        Insert a run_start document.Same validation method as bluesky, secondary
        safety net. Any changes done here or BlueSky must be implemented here and
        BlueSky.Any data acquisition script can utilize metadataservice as long as 
        it follows this format. 
    """
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        database = self.settings['db']
        query = utils._unpack_params(self)
        start = query.pop('range_floor')
        stop = query.pop('range_ceil')
        docs = yield database.run_start.find(query).sort(
            'time', pymongo.ASCENDING)[start:stop].to_list(None)
        if not docs and start == 0:
            raise tornado.web.HTTPError(404)
        else:
            utils._return2client(self, utils._stringify_data(docs))
            self.finish()

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        database = self.settings['db']
        data = ujson.loads(self.request.body.decode("utf-8"))
        jsonschema.validate(data, utils.schemas['run_start'])
        result = yield database.run_start.insert(data)
        db.run_start.ensure_index()
        if not result:
            raise tornado.web.HTTPError(500)
        else:
            utils._return2client(self, data)
   
    @tornado.web.asynchronous
    @gen.coroutine
    def put(self):
        raise tornado.web.HTTPError(404)


class EventDescriptorHandler(tornado.web.RequestHandler):
    """Handler for event_descriptor insert and query operations.
    Uses traditional RESTful lingo. get for querying and post for inserts
    
    Methods
    -------
    get()
        Query event_descriptor documents.Very thin as we do not want to create a
        bottleneck dealing with multiple clients. self.write() dumps the json to
        socket. Client keeps connection open until server kills the socket with
        self.finish(), otherwise keeps hanging wasting resources
    post()
        Insert a event_descriptor document.Same validation method as bluesky, secondary
        safety net. Any changes done here or BlueSky must be implemented here and
        BlueSky.Any data acquisition script can utilize metadataservice as long as 
        it follows this format. 
    """
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        database = self.settings['db']
        docs = yield database.event_descriptor.find({},
                                                    await_data=True,
                                                    tailable=True).to_list(None)
        if not docs:
            raise tornado.web.HTTPError(404)
        else:
            for d in docs:
                run_start_id = d.pop('run_start_id')
                rstart = yield database.run_start.find_one({'run_start_id': run_start_id})
                d['run_start'] = rstart
            utils._return2client(self, utils._stringify_data(docs))
            self.finish()

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        database = self.settings['db']
        data = ujson.loads(self.request.body.decode("utf-8"))
        jsonschema.validate(data, utils.schemas['descriptor'])
        result = yield database.event_descriptor.insert(data)#async insert
        if not result:
            raise tornado.web.HTTPError(500)
        else:
            utils._return2client(self, data)
            
    @tornado.web.asynchronous
    @gen.coroutine
    def put(self):
        raise tornado.web.HTTPError(404)

            
class RunStopHandler(tornado.web.RequestHandler):
    """Handler for run_stop insert and query operations.
    Uses traditional RESTful lingo. get for querying and post for inserts
    
    Methods
    -------
    get()
        Query run_stop documents.Very thin as we do not want to create a
        bottleneck dealing with multiple clients. self.write() dumps the json to
        socket. Client keeps connection open until server kills the socket with
        self.finish(), otherwise keeps hanging wasting resources
    post()
        Insert a run_stop document.Same validation method as bluesky, secondary
        safety net. Any changes done here or BlueSky must be implemented here and
        BlueSky.Any data acquisition script can utilize metadataservice as long as 
        it follows this format. 
    """
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        database = self.settings['db']
        query = utils._unpack_params(self)
        start = query.pop('range_floor')
        stop = query.pop('range_ceil')    
        docs = yield database.run_stop.find(query).sort(
            'time', pymongo.ASCENDING)[start:stop].to_list(None)
        if not docs and start == 0:
            raise tornado.web.HTTPError(404)
        else:
            utils._return2client(self, utils._stringify_data(docs))
            self.finish()

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        database = self.settings['db']
        data = ujson.loads(self.request.body.decode("utf-8"))
        jsonschema.validate(data, utils.schemas['run_stop'])
        result = yield database.run_stop.insert(data)
        if not result:
            raise tornado.web.HTTPError(500)
        else:
            utils._return2client(self, data)

    @tornado.web.asynchronous
    @gen.coroutine
    def put(self):
        raise tornado.web.HTTPError(404)


class EventHandler(tornado.web.RequestHandler):
    """Handler for event insert and query operations.
    Uses traditional RESTful lingo. get for querying and post for inserts
    
    Methods
    -------
    get()
        Query event documents.Very thin as we do not want to create a
        bottleneck dealing with multiple clients. self.write() dumps the json to
        socket. Client keeps connection open until server kills the socket with
        self.finish(), otherwise keeps hanging wasting resources
    post()
        Insert a event document.Same validation method as bluesky, secondary
        safety net. Any changes done here or BlueSky must be implemented here and
        BlueSky.Any data acquisition script can utilize metadataservice as long as 
        it follows this format.
    """
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        database = self.settings['db']
        query = utils._unpack_params(self)
        start = query.pop('range_floor')
        stop = query.pop('range_ceil')
        docs = yield database.event_descriptor.find(query).sort(
            'time', pymongo.ASCENDING)[start:stop].to_list(None)
        if not docs and start == 0:
            raise tornado.web.HTTPError(404)
        else:
            utils._return2client(self, utils._stringify_data(docs))
            self.finish()

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        database = self.settings['db']
        data = ujson.loads(self.request.body.decode("utf-8"))
        if isinstance(data, list):
            # unordered insert. in seq_num I trust
            jsonschema.validate(data, utils.schemas['bulk_events'])
            bulk = yield database.event.initialize_unordered_bulk_op()
            for _ in data:
                bulk.insert(_)
            try:
                yield bulk.execute() #TODO: Add appropriate timeout
            except pymongo.errors.BulkWriteError as err:
                print(err) #TODO: Log this instead of print
                raise tornado.web.HTTPError(500)
        else:
            jsonschema.validate(data, utils.schemas['event'])
            result = yield database.event.insert(data)
            if not result:
                raise tornado.web.HTTPError(500)
    
    @tornado.web.asynchronous
    @gen.coroutine
    def put(self):
        raise tornado.web.HTTPError(404)


class CappedRunStartHandler(tornado.web.RequestHandler):
    """Handler for capped run_start collection that is used for caching 
    and monitoring.
    """
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        database = self.settings['db']
        cursor = database.run_start_capped.find({},
                                                await_data=True,
                                                tailable=True)
        while True:
            if (yield cursor.fetch_next):
                tmp = cursor.next_object() #pop from cursor all old entries
            else:
                break 
        while cursor.alive:
            if (yield cursor.fetch_next):
                result = cursor.next_object()
                utils._return2client(self, result)
                break
            else:
                yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=1))
            
    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        database = self.settings['db']
        data = ujson.loads(self.request.body.decode("utf-8"))
        jsonschema.validate(data, utils.schemas['run_start'])
        try:
            result = yield database.run_start_capped.insert(data)
        except pymongo.errors.CollectionInvalid:
            #try to create the collection if it doesn't exist
            db.create_collection('run_start_capped', size=CACHE_SIZE)
        if not result:
            raise tornado.web.HTTPError(500)
        else:
            utils._return2client(self, data)

    @tornado.web.asynchronous
    @gen.coroutine
    def put(self):
        raise tornado.web.HTTPError(404)


class CappedRunStopHandler(tornado.web.RequestHandler):
    """Handler for capped run_stop collection that is used for caching 
    and monitoring.
    """
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        database = self.settings['db']
        cursor = database.run_stop_capped.find({},
                                               await_data=True,
                                               tailable=True)
        while True:
            if (yield cursor.fetch_next):
                tmp = cursor.next_object() #pop from cursor all old entries
            else:
                break
        while cursor.alive:
            if (yield cursor.fetch_next):
                result = cursor.next_object()
                utils._return2client(self, result)
                break
            else:
                yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=1))
        
            
    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        database = self.settings['db']
        data = ujson.loads(self.request.body.decode("utf-8"))
        jsonschema.validate(data, utils.schemas['run_start'])
        try:
            result = yield database.run_stop_capped.insert(data)
        except pymongo.errors.CollectionInvalid:
            #try to create the collection if it doesn't exist
            db.create_collection('run_start_capped', size=CACHE_SIZE)
        if not result:
            raise tornado.web.HTTPError(500)
        else:
            utils._return2client(self, data)

    @tornado.web.asynchronous
    @gen.coroutine
    def put(self):
        raise tornado.web.HTTPError(404)


