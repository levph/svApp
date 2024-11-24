def cat(hey, **kwargs):
    print(hey)
    print(kwargs)
    for key, value in kwargs.items():
        print(key, value)

def cat_middleware(**kwargs):
    print("middleware")
    cat(**kwargs)


if __name__ == "__main__":
    cat_middleware(name="joe", age=20)