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


def can_be_float(string):
    try:
        float(string)
        return True
    except ValueError:
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
        # variables go here
        self.namespace = {}
        if start_variables is not None:
            self.namespace.update(start_variables)
        # actual lexing
        self.lexer = shlex.shlex(script, punctuation_chars="()+-*/=")
        # interpreter state and control flow
        self.running = True
        self.current_command = None
        # list of tuples containing control state (eg, [('switch', 'b')]
        self.control_statements = []
        # list of lists of tokens in while loops.
        # shlex doesn't support jumping lines, so we cache and push the whole loop in manually
        self.loop_cache = []
        # when repeating a loop the lexer doesn't parse the newlines twice
        # increment line number manually when this is set to True
        self.running_stack = False
        self.set_name = None

    def error(self, prompt):
        raise SnekError(
            f"{self.lexer.error_leader('main')}{prompt}",
        )

    def _skip(self):
        brace_count = 1
        while brace_count:
            token = self.lexer.get_token()
            if token == "{":
                brace_count += 1
            if token == "}":
                brace_count -= 1

    def _if(self, arg):
        if arg:
            self.control_statements.append(("if", True, self.lexer.lineno))
        else:
            self._skip()

    def _switch(self, arg):
        self.control_statements.append(("switch", arg, self.lexer.lineno))

    def _case(self, arg):
        if arg == self.eval_arg(self.control_statements[-1][1]):
            self.control_statements.append(
                (
                    "case",
                    True,
                    self.lexer.lineno,
                )
            )
        else:
            self._skip()

    def _while(self, arg):
        self.control_statements.append(("while", arg, self.lexer.lineno))
        self.loop_cache.append([])

    def _end(self):
        kwd, expr, line = self.control_statements.pop()
        if kwd == "while":
            loop_tokens = self.loop_cache.pop()
            if self.eval_arg(expr):
                self.control_statements.append((kwd, expr, line))
                self.loop_cache.append([])
                self.running_stack = True
                for loop_token in reversed(loop_tokens):
                    self.lexer.push_token(loop_token)
                self.lexer.lineno = line
            elif self.loop_cache:
                self.loop_cache[-1].extend(loop_tokens)
            else:
                self.running_stack = False

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
            if statement[0] in {"if", "case"} and not statement[1]:
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
        if self.loop_cache:
            self.loop_cache[-1].extend(token_list)
        return token_list

    def is_arg(self, value):
        if value.isidentifier():
            return True
        if value.isdigit():
            return True
        if can_be_float(value):
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
        if can_be_float(value):
            return float(value)
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
                case ["while", arg, "{"]:
                    self._while(arg)
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
            if self.running_stack:
                self.lexer.lineno += 1


if __name__ == "__main__":
    with open("test.snk") as file:
        script = file.read()
    SNEKProgram(script).run()
