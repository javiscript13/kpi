# coding: utf-8
import operator
from collections import defaultdict
from distutils import util
from functools import reduce

from django.conf import settings
from django.db.models import Q
from django_request_cache import cache_for_request

from kpi.exceptions import SearchQueryTooShortException
from .canopy_autogenerated_parser import parse as grammar_parse


"""
This is a utility for parsing a Boolean, Whoosh-like query string and
translating it into a Django Q object, which can then be used to filter a
queryset in the ORM.

Syntax examples:
    * `name:term` returns any object whose `name` field exactly matches
        `term` (case sensitive)
    * `owner__username=meg` traverses the `owner` relationship, returning
        any object whose `owner` field matches an object whose `username` field
        exactly matches `meg` (case sensitive)
    * `color:orange NOT (type:fruit OR type:chair)` returns anything
        whose color is orange so long as it is not a fruit or a chair. AND, OR,
        and NOT operators are supported. They must be in ALL CAPS.

Special notes:
    * The value `null` in a query is translated to `None`, e.g. `parent:null`
        effectively becomes the ORM `filter(parent=None)`
"""


class QueryParseActions:
    """
    Actions for the parser to take when it encounters certain identifiers
    (see the file grammar.peg)
    """

    def __init__(self, default_field_lookups: list, min_search_characters: int):
        self.default_field_lookups = default_field_lookups
        self.min_search_characters = min_search_characters

    @staticmethod
    def process_value(field, value):
        # If all we're doing when we have a type mismatch with a field
        # is returning an empty set, then we don't need to do type validation.
        # Django compares between field values and string versions just fine.
        # But there's no magic string for null, so we're adding one.

        # TODO: Use Django or DRF machinery (or JSON parsing?) to handle types
        # that need special treatment, like dates

        # Handle None value
        if value == 'null':
            return None

        # Handle booleans - necessary when querying inside JSONBFields, and
        # also some other contexts: see `get_parsed_parameters()`
        try:
            lower_value = value.lower()
        except AttributeError:
            pass
        else:
            if lower_value in ['true', 'false']:
                return bool(util.strtobool(lower_value))

        return value

    @staticmethod
    def query(text, a, b, elements):
        exp = elements[1]
        if hasattr(exp, 'text') and exp.text == '':
            # Handle the empty query case with an empty Q object, returning all
            return Q()
        else:
            # fallthrough
            return exp

    @staticmethod
    def orexp(text, a, b, elements):
        # fallthrough if singular
        if elements[1].text == '':
            return elements[0]
        # else, combine full sequence of ORs into flattened expression
        else:
            # Start with the first Q object
            orgroup = elements[0]
            # Loop through the repeated clauses and OR the subexpressions.
            for clause in elements[1].elements:
                orgroup |= clause.expr
            return orgroup

    @staticmethod
    def andexp(text, a, b, elements):
        # fallthrough if singular
        if elements[1].text == '':
            return elements[0]
        # else, combine full sequence of ANDs into flattened expression
        else:
            # Start with the first Q object
            andgroup = elements[0]
            # Loop through the repeated clauses and AND the subexpressions.
            for clause in elements[1].elements:
                andgroup &= clause.expr
            return andgroup

    @staticmethod
    def parenexp(text, a, b, elements):
        # fallthrough to subexpression
        exp = elements[2]
        return exp

    @staticmethod
    def notexp(text, a, b, elements):
        # negate subexpression (Q object)
        exp = elements[2]
        return ~exp

    def term(self, text, a, b, elements):

        def _get_value(_field, _elements):
            # A search term by itself without a specified field
            _value = _elements[1]
            # the `field` value is not used in `process_value()`
            return self.process_value(_field, _value)

        if elements[0].text == '':
            value = _get_value('', elements)

            # As discussed here: https://github.com/kobotoolbox/kpi/pull/2830
            # there strain on the server for small search queries without a
            # specified field. The user will receive an empty list in response
            # until using `self.min_search_characters` or more characters
            if len(value) < self.min_search_characters:
                raise SearchQueryTooShortException()

            # A list of `Q` objects where every value is the same
            # searched value
            q_list = [
                Q(**{field: value}) for field in self.default_field_lookups
            ]
            # combining all the `Q` objects with an `or` operator and
            # returning the result
            return reduce(operator.or_, q_list)
        else:
            # A field+colon, and a value [[field,':'],value]
            field = elements[0].elements[0]
            # ByPass `status` field because it does not really exist.
            # It's only a property of Asset model.
            if field == 'status':
                return Q()

        value = _get_value(field, elements)
        return Q(**{field: value})

    @staticmethod
    def word(text, a, b, elements):
        return text[a:b]

    @staticmethod
    def string(text, a, b, elements):
        return text[a+1:b-1]

    @staticmethod
    def name(text, a, b, elements):
        return text[a:b]


def get_parsed_parameters(parsed_query: Q) -> dict:
    """
    NOTE: this is a hack that does not respect boolean logic.
    Returns a dictionary of all parameters detected in the query and their
    values. Values are always returned as list even if there is only one value
    found.
    For example:
    `q=parent_uid:foo AND asset_type:survey OR asset_type:block` returns
    {'parent_uid':['foo'], 'asset_type': ['survey', 'block']}

    """

    parameters = defaultdict(list)
    for child in parsed_query.__dict__['children']:
        if isinstance(child, Q):
            parameters.update(get_parsed_parameters(child))
            continue

        parameters[child[0]].append(child[1])

    # Cast to `dict` to be able raise KeyError when accessing a non-existing
    # member of returned value
    return dict(parameters)


@cache_for_request
def parse(
    query: str, default_field_lookups: list, min_search_characters: int = None
) -> Q:
    """
    Parse a Boolean query string into a Django Q object.
    If no field is specified in the query, `default_field_lookups` is assumed.
    For example, if `default_field_lookups` is a list containing
    `summary__icontains` and `name__icontains`, then the query `term` returns
    any object whose `summary` or `name` field contains `term` (case
    insensitive)
    """
    if not min_search_characters:
        min_search_characters = settings.MINIMUM_DEFAULT_SEARCH_CHARACTERS

    return grammar_parse(
        query, QueryParseActions(default_field_lookups, min_search_characters)
    )
