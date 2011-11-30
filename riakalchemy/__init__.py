import model
from model import NoSuchObjectError

global RiakObject
global connect


def use_real_backend():
    global RiakObject
    global connect
    RiakObject = model.RiakObject
    connect = model.connect

reset_registry = model.reset_registry
use_real_backend()
