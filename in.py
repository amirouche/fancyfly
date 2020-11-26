def fibo(k):
    if k == 0:
        return 0
    else:
        if k == 1:
            return 1
        else:
            return add(fibo(minus(k, 1)), fibo(minus(k, 2)))

fibo(10000)
