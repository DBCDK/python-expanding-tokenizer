# Expanding Tokenizer

Helper functions for reading configfiles with environment variable expansion

## Design

* Based around a *Reader* that is line buffered and implements 3 basic functions:
  * get() - next char
  * get_quoted() - reads a basic character as expanded by \\ (newline, carriage-return, tab, \\octal \\uhex ) 
  * unget() which rewinds but is limited to 2 lines
  * at() gives a location (file:line:pos)
* A *Variable* resolving object, that can be user overridden, if something other than environment variables should be
  resolved. It has 2 basic functions:
  * get_name() that takes a *Reader*, and takes a variable name by calling get()/unget()
  * lookup_variable() which takes the name and returns the value (or None is it's unresolvable)
* The *Tokenizer* which is build from a *Reader* and a *Variable* resolver.

  Simple one character tokens are made from a list, and matched against known one character tokens. This allows for
  "`[`" tokens, which disables the **SECTION** token, or "`;`" which disables comments. It's not possible at the moment,
  to disable **#** comments
  
  It also takes a declaration how whitespace should be handled, with 4 options:
  * **NONE** which just skips whitespace in input
  * **NEWLINE** which skips space and tab, but turns newlines into tokens
  * **WHITESPACE** which turns all blocks of whitespace into tokens (including newlines)
  * **BOTH** which turns all whichspace blocks into tokens, but newlines into separate tokens
  The business interface for eht *Tokenizer* is:
    * is_eof() - which tells if there's more tokens to read
    * peek_token() - look at the next token. Usefull for error reporting
    * tokens_are() - which takes a list of token-types or list-of token-type (meaning any any of these), and an optional
      `output=[]`. If the next tokens match the list, output has the matched *Token*s appended, and the same variable is
      returned. Otherwise None is returned
  
  The *Tokenizer* also has a couple of  static helper functions:
   * ini_from_filename() - Which builds a *Tokenizer* meant for parsing ini files
   * full_from_filename() - Which builds a *Tokenizer* which reports all known tokens 
   
  
* The *Token* type has 3 basic conveyors of information.
  * is_a() - Which takes a token-type and returns if it's the same (There's synthetic types, which matches multiple
    token-types or tokens with special properties)
  * content() - which returns the string wrapped by this token
  * at() - which returns an object identical to that of *Reader.at()*
  
* The *Expanding* object is purely designed for internal use, but the interface is simple:
  * expand() - which takes a *Reader*, positiones after a "$" sign. Then resolves the 3 types of expansion, returning it's
    content:
    * `$WORD` - Simple variable expansion
    * `${WORD\[:modifier\[,modifier...\]\]\[|default value\]}` - Which takes the variable, if it is set, and applies the
      modifiers in order. If it doesn't resolve the default value is used, but is processed af if it was a double
      quoted value. ie. \\-escapes (allowing for embedded "}") and variable expansion
      
      Implemented modifiers are:
      * **s**/**ms** - which expands a Amount/Duration (ie 3h) to number of seconds/milliseconds
      * **xml** - for use inside xml tags
      * **attr** - for use inside xml attribute values with double quote
      * **uri** - for use as uri parts
      * **sql** - for use inside single quoted sql strings
    * `$( math-expression )` - calculates a simple (integer) math expression, which allows for variable expansion (all
      variable expansions should resolve to a integer value of the type decimal/octal/hexadecimal).
      
      Supported expressions are:
      * "**(**", "**)**" - simple nested expressions
      * "**-**" - Unary minus
      * "**+**", "**-**", "__*__", "**/**", "**%**" - Basic binary operators (normal precedence rules apply)
      * "**<**", "**>**" -  Binary operators min & max (precedence after "**+**" & "**-**")
      * Literal integer values
      * Variable expansion - the should resolve into a integer value of the format decimal/octal/hexadecimal
* The _Math*_ objects are purely for internal usage

## Example code for parsing a simple `.ini` file

[Example](example/)

## License

License is [GPL-v3](https://www.gnu.org/licenses/gpl-3.0.txt])
