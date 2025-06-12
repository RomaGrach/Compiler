# Compiler
Custom Language to MASM Compiler


/*
EBNF Grammar for RomasCompiler Language
Defines syntax for variables, functions, control flow, I/O, and expressions.
*/

program         ::= { declaration }

declaration     ::= function_decl
| statement

function_decl   ::= "func" identifier "(" [ param_list ] ")" ":" "{" statement_list "}"
param_list      ::= identifier { "," identifier }

statement_list  ::= { statement }

statement       ::= var_decl
| assignment
| print_stmt
| input_stmt
| if_stmt
| while_stmt
| return_stmt
| expr_stmt

var_decl        ::= "var" identifier [ "=" expression ] ";"
assignment      ::= identifier "=" expression ";"
print_stmt      ::= "print" ( string_literal | identifier | expression ) ";"
input_stmt      ::= "input" identifier [ "," integer_literal ] ";"
if_stmt         ::= "if" expression ":" "{" statement_list "}" [ "else" ":" "{" statement_list "}" ]
while_stmt      ::= "while" expression ":" "{" statement_list "}"
return_stmt     ::= "return" expression ";"
expr_stmt       ::= expression ";"

expression      ::= logical_or_expr
logical_or_expr ::= logical_and_expr { "||" logical_and_expr }
logical_and_expr::= equality_expr { "&&" equality_expr }
equality_expr  ::= relational_expr { ("==" | "!=") relational_expr }
relational_expr ::= additive_expr { ("<" | "<=" | ">" | ">=") additive_expr }
additive_expr   ::= multiplicative_expr { ("+" | "-") multiplicative_expr }
multiplicative_expr ::= unary_expr { ("*" | "/" | "%") unary_expr }
unary_expr      ::= [ ("+" | "-" | "!") ] primary_expr
primary_expr    ::= integer_literal
| identifier
| string_literal
| "(" expression ")"

identifier      ::= letter { letter | digit | "_" }
integer_literal ::= digit { digit }
string_literal  ::= '"' { any_character_except_quote | '\"' } '"'

// Comments
comment         ::= "//" { any } NEWLINE
| "/" { any } "/"

// Tokens to ignore
WHITESPACE      ::= ( " " | "\t" | NEWLINE )+

