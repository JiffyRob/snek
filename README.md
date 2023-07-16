# SNEK
#### Super NPC/Event Koordinator

SNEK is a very simple scripting language that you can use to control cutscenes or anything that you want really in your games.  The entire language is set up to run as a coroutine, so that one command can take as lont as it wants.

You can use your own single frame frunctions via the @snek_command decorator, which will convert to a coroutine for you.  You can also create your own multiple frame callbacks by sublcassing the SnekCommand class and implementing a `get_value()` method.

## Syntax
The language is centered around being as powerful as possible while still being simple and easy to parse.
Comments are denoted by a `#`, strings by `"` or `'` on each side.  There are no multiline comments.
### basic syntax
`x = 2;` sets x to 2
`y = add(2, 3);` sets y to the sum of 2 and 3
`print("Hello world!");` prints the string "hello world!"
There are many many other functions that you have access to as well:
 - `upper(string)` is the equivalent of `string.upper()` in python
 - `lower(string)` is the equivalent of `string.lower()` in python
 - `title(string)` is the equivalent of `string.title()` in python
 - `print(*stuff)` is like python but gives a little debug info
 - `wait(time)` is the same as `time.sleep(time / 1000)` or `pygame.time.delay(time)`
 - `randint(start, end)` is the same as `random.randint(start, end)`
 - `input(prompt)` is special.  It is the one function that blocks even the async part of the code.  It is used for console demos and for halting things for debugging 
purposes.  It is equivalent to the python `input()` function
 - `not(arg)` is the same as the `not` operator in python `not(True)` = `False`
 - `bool` does the same as in python as well
 - `contains(string, substring)` is the same as `substring in string` in python
 - `lt, le, eq, neq, ge, gt, abs` all are erquivalent to the `<, <=, ==, !=, >=, >, abs` operators in python, respectively
 - `add(*stuff)` takes as many args as you give it and adds them all together
 - `mult(*stuff)` is the same as add, but multiplies
 - `neg(num)` is the same as the unary `-` in python (`neg(3)` = `-3`)
 - `pow(a, b)` is the same as `a**b` in python
 - `sub(a, *b)` subtracts every subsequent number from the first one (`sum(6, 3, 1)` = 6 - 3 - 1 or 2)
 - `div(a, *b) and fdiv(a, *b)` divides every subsequent number from the first one.  `fdiv` rounds to the lowest whole number.
 - `inv(a)` is the bitwise not
 - `lshift(a) and rshift(b)` do bitwise left and right shift
 - `xor` bitwise exclusive or
 - `and` bitwise/logical and
 - `or` bitwise/logical or

### Control flow statments
SNEK has three control flow statements, which would act pretty much how you would expect:
If statement:
```
# if statement runs its code if bool(x) == True
if x {
    print("x evals to true!");
}
# if x is 0, print x is 0.  If it is 1, print it
switch x {
    case 0 {
        print("x is 0");
    }
    case 1 {
        print("x is 1");
    }
}
```

### variable types
SNEK has three variable types as well.  They are all represented the same way python represents them, but you can only call their methods if you wrap them into commands
```
x = 0;  # x is an int
y = -.6  # y is a float
z = "Hello, world!"  # z is a string
```
