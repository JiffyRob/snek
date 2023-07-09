# SNEK
#### Super NPC/Event Koordinator

SNEK is a very simple scripting language that you can use to control cutscenes or anything that you want really in your games.  It implements all functions  as coroutines and can use this to execute functions over multiple frames.  

You can use your own single frame frunctions via the @snek_command decorator, which will convert to a coroutine for you.  You can also create your own multiple frame callbacks by sublcassing the SnekCommand class and implementing a `get_value()` method.

## Syntax
The language is centered around being as powerful as possible while still being simple and easy to parse.
Every program is divided into lines, which in turn are divided into tokens.  Tokens are seperated by two spaces `"  "` or a parenthesis `'(' or ')'`
Comments are denoted by a `#`, strings by `*` on each side.  There are no multiline comments.

Every line is either:
 - A comment or blank line (Comment tokens or no tokens)
 - A command (eg `print(x)`) (Command token followed any amount of arg tokens)
 - A control flow statement (eg `IF y`)  (Keyword token optionally followed by an arg token)
 - A variable setting `SET  x  0` or `x  =  0`  (SET token, var_name token, optional value token ,or SET token, var_name token)

Every token is either:
 - A comment token (#......)
 - A command token (eg `print`)
 - An arg token (eg `4` or `*mystring*`)
 - A keyword token (eg `SWITCH`)
 - A var name token (eg `My_var3`)

Sytax errors try to be good but there are always token patterns that the interpreter will not understand, in which case they are given to you.
There are currently only two types: ints and strings.  We may need arrays later or floats.

To set a variable to the result of a command you do like this:
```
SET  x
add(2  3)
print(x)  # will print 5
```
If statements are constructed like this:
```
IF x
print *X is true*  # you can indent this
ENDIF
```
Switch case are a little more complex:
```
SWITCH x
  # indentation is optional here, but can improve readability
  CASE 0
    print *x is 0*
  ENDCASE
  CASE 1
    print *x is 1*
  ENDCASE
ENDSWITCH
```
As of yet there is no default case but you can always set a variable to work around it if you have to.

Commands:
```
eq *args returns if all args are equal to e/0
neq *args is the inverse of eq
add *args gets the sum of all args
sub *args subtracts all subsequent args from the first one
mult *args gets the produt of all args
div *args is equivalent to args[0] / (product(args[1:])
print *args prints all args given
wait millis waits by a given amount of milliseconds.
```

There will be more commands later.  You can always add your own if the set is too small.
To run a script in async mode you call `SnekProgram.cycle()` every execution frame.  `run()` does this in one go and can eat serious resources.  