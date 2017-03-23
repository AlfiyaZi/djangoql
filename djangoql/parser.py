import sys

import ply.yacc as yacc

from .ast import *  # noqa
from .exceptions import DjangoQLParserError
from .lexer import DjangoQLLexer


PY2 = sys.version_info.major == 2


class DjangoQLParser(object):
    def __init__(self, debug=False, **kwargs):
        self.default_lexer = DjangoQLLexer()
        self.tokens = self.default_lexer.tokens
        kwargs['debug'] = debug
        self.yacc = yacc.yacc(module=self, **kwargs)

    def parse(self, input=None, lexer=None, **kwargs):
        lexer = lexer or self.default_lexer
        return self.yacc.parse(input=input, lexer=lexer, **kwargs)

    start = 'expression'

    def p_expression_parens(self, p):
        """
        expression : PAREN_L expression PAREN_R
        """
        p[0] = p[2]

    def p_expression_logical(self, p):
        """
        expression : expression logical expression
        """
        p[0] = Expression(left=p[1], operator=p[2], right=p[3])

    def p_expression_comparison(self, p):
        """
        expression : name comparison_number number
                   | name comparison_string string
                   | name comparison_equality boolean_value
                   | name comparison_equality none
                   | name comparison_in_list const_list_value
        """
        p[0] = Expression(left=p[1], operator=p[2], right=p[3])

    def p_name(self, p):
        """
        name : name_parts
        """
        p[0] = Name(parts=p[1])

    def p_name_parts(self, p):
        """
        name_parts : name_parts DOT NAME
                   | NAME
        """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = p[1] + [p[3]]

    def p_logical(self, p):
        """
        logical : AND
                | OR
        """
        p[0] = Logical(operator=p[1])

    def p_comparison_number(self, p):
        """
        comparison_number : comparison_equality
                          | comparison_greater_less
        """
        p[0] = p[1]

    def p_comparison_string(self, p):
        """
        comparison_string : comparison_equality
                          | comparison_greater_less
                          | comparison_contains
        """
        p[0] = p[1]

    def p_comparison_equality(self, p):
        """
        comparison_equality : EQUALS
                            | NOT_EQUALS
        """
        p[0] = Comparison(operator=p[1])

    def p_comparison_greater_less(self, p):
        """
        comparison_greater_less : GREATER
                                | GREATER_EQUAL
                                | LESS
                                | LESS_EQUAL
        """
        p[0] = Comparison(operator=p[1])

    def p_comparison_contains(self, p):
        """
        comparison_contains : CONTAINS
                            | NOT_CONTAINS
        """
        p[0] = Comparison(operator=p[1])

    def p_comparison_in_list(self, p):
        """
        comparison_in_list : IN
                           | NOT IN
        """
        if len(p) == 2:
            p[0] = Comparison(operator=p[1])
        else:
            p[0] = Comparison(operator='%s %s' % (p[1], p[2]))

    def p_const_value(self, p):
        """
        const_value : number
                    | string
                    | none
                    | boolean_value
        """
        p[0] = p[1]

    def p_number(self, p):
        """
        number : INT_VALUE
               | FLOAT_VALUE
        """
        p[0] = Const(value=p[1])

    def p_string(self, p):
        """
        string : STRING_VALUE
        """
        if PY2:
            value = p[1].decode('string_escape')
        else:
            value = bytes(p[1], 'utf8').decode('unicode_escape')
        p[0] = Const(value=value)

    def p_none(self, p):
        """
        none : NONE
        """
        p[0] = Const(value=None)

    def p_boolean_value(self, p):
        """
        boolean_value : true
                      | false
        """
        p[0] = p[1]

    def p_true(self, p):
        """
        true : TRUE
        """
        p[0] = Const(value=True)

    def p_false(self, p):
        """
        false : FALSE
        """
        p[0] = Const(value=False)

    def p_const_list_value(self, p):
        """
        const_list_value : PAREN_L const_value_list PAREN_R
        """
        p[0] = List(items=p[2])

    def p_const_value_list(self, p):
        """
        const_value_list : const_value_list const_value
        """
        p[0] = p[1] + [p[2]]

    def p_const_value_list_single(self, p):
        """
        const_value_list : const_value
        """
        p[0] = [p[1]]

    def p_error(self, token):
        if token is None:
            self.raise_syntax_error('Unexpected end of input')
        else:
            fragment = str(token.value)
            if len(fragment) > 20:
                fragment = fragment[:17] + '...'
            self.raise_syntax_error(
                'Syntax error at %s' % repr(fragment),
                token=token,
            )

    def raise_syntax_error(self, message, token=None):
        if token is None:
            raise DjangoQLParserError(message)
        lexer = token.lexer
        if callable(getattr(lexer, 'find_column', None)):
            column = lexer.find_column(token)
        else:
            column = None
        raise DjangoQLParserError(
            message=message,
            value=token.value,
            line=token.lineno,
            column=column,
        )
