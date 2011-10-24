class RiakAlchemyError(Exception):
    pass

class ValidationError(RiakAlchemyError):
    pass

class NoSuchObjectError(RiakAlchemyError):
    pass

