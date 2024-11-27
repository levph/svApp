def exception_handler_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # raise the error with the string we printed (with the same error type)
            raise type(e)(f"Error in {func.__name__}: {e}")

    return wrapper


class Example:
    @exception_handler_decorator
    def test(self):
        return 1 / 0


example = Example()
result = example.test()
