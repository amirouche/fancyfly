import ast
from pprint import pprint


IT = 0


def makevar(name="t"):
    global IT
    IT += 1
    return name + str(IT)


def python(node):
    if node is None:
        return None
    elif isinstance(node, (str, int)):
        return node
    elif isinstance(node, list):
        return [python(item) for item in node]
    elif isinstance(node._fields, tuple):
        return [type(node).__name__, *(python(getattr(node, name)) for name in node._fields)]
    elif node._fields is None:
        return [type(node).__name__]
    else:
        raise NotImplementedError(node)


def lispy(node):
    # This will simplify ACCORDING TO ME the ast into a prefix-based
    # calling convention like found in LISP languages with the
    # addition of the `Return`, original ast nodes that contains
    # lists, like `FunctionDef`, `Module`, `If` bodies are are wrapped
    # with `Begin` to keep the "prefix" notation and avoid lists that
    # are not tagged except Function arguments that is the definition
    # of function have an untagged list at position one.  The goal is
    # make it more readable.
    match node:
        case ["Module", program, _]:
             return ["Begin", *(lispy(node) for node in program)]
        case ["FunctionDef", name, arguments, body, _, _, _]:
            return [
                 "FunctionDef",
                 name,
                 lispy(arguments),
                 ["Begin", *(lispy(node) for node in body)]
            ]
        case ["Assign", target, value, _]:
            return ["Assign", target[0][1], lispy(value)]
        case ["arguments", _, args, *_]:
             return [arg[1] for arg in args]
        case ["Compare", left, ops, comparators]:
             assert len(ops) == 1
             assert len(comparators) == 1
             return ["Call", ops[0][0], lispy(left), lispy(comparators[0])]
        case ["Name", variable, [op]]:
             return variable
        case ["Constant", c, None]:
             return ["Constant", c]
        case ["BinOp", left, op, right]:
             assert len(op) == 1
             return ["Call", op[0], lispy(left), lispy(right)]
        case ["Call", name, args, _]:
             return ["Call", lispy(name), *(lispy(arg) for arg in args)]
        case ["Expr", expr]:
             return lispy(expr)
        case ["If", predicate, then, elsex]:
             return [
                 "If",
                 ["Begin", lispy(predicate)],
                 ["Begin", *(lispy(x) for x in then)],
                 ["Begin", *(lispy(x) for x in elsex)]
             ]
        case _:
             if isinstance(node, (str, int)):
                 return node
             else:
                 return [lispy(item) for item in node]


def drop_return(node):
    match node:
        case ["Return", expr]:
             # We can only drop return on the example fibonnaci
             # program because return is always at the end of a
             # statement like in lisp.
             return expr
        case _:
            if isinstance(node, (str, int)):
                return node
            else:
                return [drop_return(item) for item in node]


def if_predicate(node):
    match node:
        case ["If", predicate, then, elsex]:
            t = makevar()
            return [
                 "Begin",
                 ["Assign", t, predicate],
                 ["If", t, if_predicate(then), if_predicate(elsex)]
            ]
        case _:
             if isinstance(node, (str, int)):
                 return node
             else:
                 return [if_predicate(item) for item in node]


def terminal_arguments(node):
    # mighty Continuation Passing Style transformation
    match node:
        case ["Call", name, *args]:
             ts = [makevar() for arg in args]
             return [
                 "Begin",
                 *[["Assign", v[0], terminal_arguments(v[1])] for v in zip(ts, args)]
            ] + [["Call", name, *ts]]
        case _:
            if isinstance(node, (str, int)):
                return node
            else:
                return [terminal_arguments(item) for item in node]


def flatten_begin(node):
    match node:
        case ["Begin", *exprs]:
            out = ["Begin"]
            for expr in exprs:
                expr = flatten_begin(expr)
                if expr[0] == 'Begin':
                    out += expr[1:]
                else:
                    out.append(expr)
            return out
        case _:
            if isinstance(node, (str, int)):
                return node
            else:
                return [flatten_begin(item) for item in node]


def cps_begin(exprs):
    out = []
    for expr in exprs[:-1]:
        out.append(["Call", cps(expr), ["Function", ["v"], "v"]])
    out.append(["Call", cps(exprs[-1]), "k"])
    return out


NONE = ["Call", "k", None]


def cps(node):
    # Mighty Continuation Passing Style transformation
    match node:
        case ["Constant", x]:
            return ["Function", ["k"], ["Call", "k", x]]
        case ["Assign", target, value] as assign:
            return ["Function", ["k"],
                    ["Call", cps(value),
                     ["Function", ["v"],
                      ["Assign", target,
                       ["Function", ["k"],
                        ["Call", "k", "v"]]],
                      NONE]]]
        case ["Begin", *args]:
            return ["Function", ["k"], *cps_begin(args)]
        # case ["FunctionDef", name, args, body]:
        #      args.insert(0, "k")
        #      return ["FunctionDef", name, args, cps(body)]
        case ["Call", name, *args]:
            return ["Function", ["k"], ["Call", name, "k", *(cps(arg) for arg in args)]]
        case _:
            if isinstance(node, (str, int)):
                return node
            else:
                return [cps(item) for item in node]


def wrap(node):
    return ["Call", node, "print"]


def schemize(node):
    match node:
        case ["Function", args, *exprs]:
            return "(lambda ({}) {})".format(
                " ".join(schemize(arg) for arg in args),
                " ".join(schemize(expr) for expr in exprs)
            )
        case ["Assign", t, v]:
            return "(set! {} {})".format(t, schemize(v))
        case ["Call", *args]:
            return "({})".format(" ".join(schemize(arg) for arg in args))
        case _:
            return str(node)


def ppk(*x):
    pprint(x)
    return x[-1]


pipeline = [
    ast.parse,
    python,
    lispy,
    drop_return,
    if_predicate,
    terminal_arguments,
    flatten_begin,
    cps,
    ppk,
    wrap,
    schemize,
    print,
]


program = open(sys.argv[1]).read()


for callable in pipeline:
    program = callable(program)
