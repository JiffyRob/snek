import functools
import operator
import time
from dataclasses import dataclass
from typing import Any


class Argtype:
    INT = 0
    STR = 1
    DATA = 2


class SNEKConst:
    UNFINISHED = "const UNFINISHED"
    NULL = "const NULL"
    END = "const END"
    SET_COMMAND = "SET"
    EQ_OPERATOR = "="


@dataclass
class Token:
    data: Any

    def convert(self):
        return self.data

    def __str__(self):
        return str(self.data)


@dataclass
class CommandToken(Token):
    pass


@dataclass
class NoneToken(Token):
    pass


@dataclass
class ArgToken(Token):
    pass


@dataclass
class KwdToken(Token):
    pass


@dataclass
class VarnameToken(Token):
    pass


@dataclass
class SetToken(Token):
    pass


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
        return SNEKConst.UNFINISHED


def snek_command(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        yield func(*args, **kwargs)

    return wrapper


def unfinished_run():
    yield SNEKConst.UNFINISHED
    yield 1


class SnekProgram:
    def __init__(self, script, start_variables=None, api=None):
        self.api = {
            "eq": snek_command(lambda *args: functools.reduce(operator.eq, args)),
            "neq": snek_command(lambda *args: not functools.reduce(operator.eq, args)),
            "add": snek_command(lambda *args: functools.reduce(operator.add, args)),
            "sub": snek_command(lambda *args: functools.reduce(operator.sub, args)),
            "mult": snek_command(lambda *args: functools.reduce(operator.mul, args)),
            "div": snek_command(
                lambda *args: functools.reduce(operator.floordiv, args)
            ),
            "print": self.print,
            "wait": Wait,
        }
        if api is not None:
            self.api.update(api)
        self.kwd = {
            "IF": self._if,
            "ENDIF": self._endif,
            "SWITCH": self._switch,
            "ENDSWITCH": self._endswitch,
            "CASE": self._case,
            "ENDCASE": self._endcase,
            "BREAK": unfinished_run,
        }
        # dict of variables
        self.namespace = {}
        if start_variables is not None:
            self.namespace.update(start_variables)
        # list of bools from evaluated if statements
        self.conditions = [True]
        # list of switch var names
        self.switches = []
        # list of cases in switch statements
        self.cases = [True]
        # name to set next command to
        self.set_name = None
        # set the script
        self.script = []
        script = script.replace("(", "  ")
        script = script.replace(")", "  ")
        for line in script.split("\n"):
            line = line.strip()
            line = line.split("#")[0]
            self.script.append(line)
        # coroutine setup
        self.line_number = 0
        self.command_running = None

    def error(self, prompt):
        raise SnekError(
            f"Line {self.line_number + 1} ({self.script[self.line_number]}): " + prompt
        )

    def run(self):
        while self.line_number < len(self.script):
            self.cycle()

    def cycle(self):
        def make_token(token):
            if not token or token[0] == "#":
                return NoneToken(token)
            if token in self.api:
                return CommandToken(token)
            if token.isdigit():
                token = ArgToken(int(token))
                return token
            if token[0] == token[-1] == "*":
                return ArgToken(token[1:-1])
            if token in self.namespace:
                return ArgToken(self.namespace[token])
            if token in self.kwd:
                return KwdToken(token)
            if token == SNEKConst.SET_COMMAND:
                return SetToken(token)
            if token.isidentifier():
                return VarnameToken(token)
            self.error(f"Unable to parse token '{token}'")

        if self.command_running is not None:
            value = next(self.command_running)
            if value != SNEKConst.UNFINISHED:
                if self.set_name:
                    self.namespace[self.set_name] = value
                self.command_running = None
                self.line_number += 1
        while self.command_running is None and self.line_number < len(self.script):
            line = self.script[self.line_number]
            tokens = [
                make_token(token) for token in self.script[self.line_number].split("  ")
            ]
            tokens = [i for i in tokens if not isinstance(i, NoneToken)]
            commands_running = min(self.conditions) and min(self.cases)
            match tokens:
                # empty
                case []:
                    pass
                # command
                case [CommandToken() as com, *args]:
                    if commands_running:
                        func = self.api[str(com)](*[arg.convert() for arg in args])
                        value = next(func)
                        if value == SNEKConst.UNFINISHED:
                            self.command_running = func
                            continue
                        if self.set_name is not SNEKConst.NULL:
                            self.namespace[self.set_name] = value
                # variable setting
                case [SetToken(), VarnameToken() as var_name]:
                    if max(self.conditions):
                        self._set(str(var_name))
                case [SetToken(), VarnameToken() as var_name, ArgToken() as value]:
                    if commands_running:
                        self._set(str(var_name), value.convert())
                # if endif, switch, while, etc
                case [KwdToken() as kwd, ArgToken() as arg]:
                    if kwd == "ENDIF" or commands_running:
                        self.kwd[str(kwd)](arg.convert())
                case [KwdToken() as kwd]:
                    if kwd == "ENDIF" or commands_running:
                        self.kwd[str(kwd)]()
                # emtpy line
                case []:
                    pass
                # here on are common errors
                case [CommandToken(), *_]:
                    self.error("Unexpected newline.  Perhaps you forgot 'END'?")
                case [KwdToken(), VarnameToken() as var_name] | [
                    CommandToken(),
                    VarnameToken() as var_name,
                ]:
                    self.error(
                        f"Unrecognized token '{var_name}'.  Perhaps you forgot to mark it as a string?"
                    )
                case [VarnameToken() as var_name, *_] | [ArgToken() as var_name]:
                    self.error(f"Unrecognized command '{var_name}'.")
                # wow you really messed up
                case _:
                    self.error(
                        f"This line is so bad I can't even advise you what it is! ({tokens})"
                    )
            self.line_number += 1

    def _if(self, *args):
        if len(args) != 1:
            self.error(f"If statement only takes one argument.  Got {args}")
        self.conditions.append(bool(args[0]))

    def _endif(self, *args):
        if args:
            self.error("ENDIF takes no arguments")
        if len(self.conditions) <= 1:
            self.error("If statement never closed")
        self.conditions.pop(-1)

    def _switch(self, *args):
        if len(args) != 1:
            self.error(f"Switch statement only takes one argument.  Got {args}")
        self.switches.append(args[0])

    def _endswitch(self):
        if not self.switches:
            self.error(f"Unexpected ENDSWITCH statement.")
        self.switches.pop()

    def _case(self, *args):
        if len(args) != 1:
            self.error(f"Case statement only takes one argument.  Got {args}")
        if len(self.cases) - len(self.switches) > 1:
            self.error(
                f"Unexpected case statement.  Did you forget to close the first one?"
            )
        self.cases.append(self.switches[-1] == args[0])

    def _endcase(self, *args):
        if args:
            self.error(f"ENDCASE takes no arguments")
        self.cases.pop()

    def _set(self, name, value=SNEKConst.NULL):
        if value == SNEKConst.NULL:
            self.set_name = name
        else:
            self.namespace[name] = value

    @staticmethod
    @snek_command
    def print(*args):
        print("SNEK Script:", *args)
