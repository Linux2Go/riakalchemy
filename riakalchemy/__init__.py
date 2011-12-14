"""
    RiakAlchemy - Object Mapper for Riak

    Copyright (C) 2011  Linux2Go

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 3 as
    published by the Free Software Foundation.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Pull relevant stuff into the riakalchemy.* namespace
"""
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
