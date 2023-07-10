import functools
import operator
import random
import shlex
import time

UNFINISHED = "const unfinished"
NEXT = "const next"


class SnekError(SyntaxError):
    pass


class SnekCommand:
    def __next__(self):
        return self.get_value()

    def get_value(self):
        return None


class Wait(SnekCommand):
    def __init__(self, amount=1000):
        self.time = amount
        self.start = time.time() * 1000

    def get_value(self):
        now = time.time() * 1000
        if now - self.start >= self.time:
            return 1
        return UNFINISHED


def snek_command(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        yield func(*args, **kwargs)

    return wrapper


def unfinished_run():
    yield UNFINISHED
    yield 1


def neq(*args):
    last_arg = args[0]
    for arg in args:
        if arg != last_arg:
            return True
    return False


class SNEKProgram:
    def __init__(self, script, start_variables=None, api=None):
        self.api = {
            "upper": snek_command(lambda arg: arg.upper()),
            "lower": snek_command(lambda arg: arg.lower()),
            "title": snek_command(lambda arg: arg.title()),
            "print": self.print,
            "wait": Wait,
            "randint": random.randint,
            "input": snek_command(input),
            "not": snek_command(lambda arg: operator.not_(arg)),
            "bool": snek_command(lambda arg: bool(arg)),
            "contains": snek_command(lambda seq, sub: operator.contains(seq, sub)),
            "lt": snek_command(lambda a, b: a < b),
            "le": snek_command(lambda a, b: a <= b),
            "eq": snek_command(lambda *args: functools.reduce(operator.ne, args)),
            "neq": snek_command(neq),
            "ge": snek_command(lambda a, b: a >= b),
            "gt": snek_command(lambda a, b: a > b),
            "abs": snek_command(abs),
            "add": snek_command(lambda *args: sum(args)),
            "mult": snek_command(lambda *args: functools.reduce(operator.mul, args)),
            "neg": snek_command(lambda a: -a),
            "pow": snek_command(lambda a, b: a**b),
            "sub": snek_command(lambda a, *args: a - sum(args)),
            "div": snek_command(lambda *args: functools.reduce(operator.truediv, args)),
            "fdiv": snek_command(
                lambda *args: functools.reduce(operator.floordiv, args)
            ),
            "inv": snek_command(operator.inv),
            "lshift": snek_command(operator.lshift),
            "rshift": snek_command(operator.rshift),
            "xor": snek_command(operator.xor),
            "and": snek_command(operator.and_),
            "or": snek_command(operator.or_),
        }
        if api is not None:
            self.api.update(api)
        self.kwd = {
            "if": self._if,
            "switch": self._switch,
            "case": self._case,
            "}": self._end,
        }
        # variables go here
        self.namespace = {}
        if start_variables is not None:
            self.namespace.update(start_variables)
        # actual lexing
        self.lexer = shlex.shlex(script, punctuation_chars="()+-*/=")
        # interpreter state and control flow
        self.running = True
        self.current_command = None
        self.control_statements = []
        self.set_name = None

    def error(self, prompt):
        raise SnekError(
            f"{self.lexer.error_leader('main')}{prompt}",
        )

    def _if(self, arg):
        self.control_statements.append(bool(arg))

    def _switch(self, arg):
        self.control_statements.append(arg)

    def _case(self, arg):
        self.control_statements.append(
            arg == self.eval_arg(self.control_statements[-1])
        )

    def _end(self):
        self.control_statements.pop()

    def _set(self, name, value):
        if value == NEXT:
            self.set_name = name
        else:
            self.namespace[name] = value

    @snek_command
    def print(self, *args):
        print(self.lexer.error_leader("main"), *args)

    def run(self):
        while self.running:
            self.cycle()

    def control_running(self):
        if not self.control_statements:
            return True
        for statement in self.control_statements:
            if not statement:
                return False
        return True

    def get_statement(self):
        token_list = []
        current_token = None
        while current_token not in {";", "{", "}"}:
            current_token = self.lexer.get_token()
            if current_token is self.lexer.eof:
                if token_list:
                    self.error("Unexpected eof while parsing" + repr(token_list))
                self.running = False
                return []
            if current_token == "}" and token_list:
                self.error("Unexpected closing bracket while parsing")
            token_list.append(current_token)

        return token_list

    def is_arg(self, value):
        if value.isidentifier():
            return True
        if value.isdigit():
            return True
        if value[0] == value[-1] and value[0] in self.lexer.quotes:
            return True
        if value in self.namespace:
            return True
        return False

    def eval_arg(self, value):
        if value == "NEXT":
            return NEXT
        if value in self.namespace:
            return self.namespace[value]
        if value.isdigit():
            return int(value)
        if value[0] == value[-1] and value[0] in self.lexer.quotes:
            return value[1:-1].format(**self.namespace)
        self.error(f"Unable to parse argument '{value}'")

    def cycle(self):
        # parsed on the fly
        # a statement ends with a ;
        if self.current_command is not None:
            value = next(self.current_command)
            if value != UNFINISHED:
                self.current_command = None
            if self.set_name is not None:
                self._set(self.set_name, value)
                self._set(self.set_name, value)
                self.set_name = None
        while self.current_command is None and self.running:
            statement = self.get_statement()
            match statement:
                # empty line, probably eof
                case []:
                    pass
                # execute a command
                case [command, "(", *args, ")", ";"] if command in self.api:
                    if self.control_running():
                        args = [self.eval_arg(arg) for arg in args if arg != ","]
                        command = self.api[command](*args)
                        value = next(command)
                        if value == UNFINISHED:
                            self.current_command = command
                            continue
                        if self.set_name is not None:
                            self._set(self.set_name, value)
                            self.set_name = None
                # command with variable assignment
                # WHYYY does black do this
                case [
                    name,
                    "=",
                    command,
                    "(",
                    *args,
                    ")",
                    ";",
                ] if command in self.api and name.isidentifier():
                    if self.control_running():
                        self.set_name = name
                        args = [self.eval_arg(arg) for arg in args if arg != ","]
                        command = self.api[command](*args)
                        value = next(command)
                        if value == UNFINISHED:
                            self.current_command = command
                            continue
                        self._set(self.set_name, value)
                        self.set_name = None
                # control flow
                case ["if", arg, "{"]:
                    self._if(self.eval_arg(arg))
                case ["switch", arg, "{"]:
                    self._switch(arg)
                case ["case", arg, "{"]:
                    self._case(self.eval_arg(arg))
                case ["}"]:
                    self._end()
                # variable assignment
                case [name, "=", value, ";"] if name.isidentifier() and self.is_arg(
                    value
                ):
                    self._set(name, self.eval_arg(value))
                # errors
                case _:
                    self.error(f"Unable to parse line {statement}")
