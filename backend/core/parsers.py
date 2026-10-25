"""BB-11 JSON parser: reject ambiguous duplicate keys and redact parse errors.

Opt-in per endpoint after owner review. Does NOT change global parser settings.
"""
import codecs
from django.conf import settings
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.utils import json


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Repeated object key.')
        result[key] = value
    return result


class StrictJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        encoding = (parser_context or {}).get('encoding', settings.DEFAULT_CHARSET)
        try:
            decoded = codecs.getreader(encoding)(stream)
            return json.load(decoded, object_pairs_hook=_unique_object,
                             parse_constant=json.strict_constant)
        except (ValueError, UnicodeError, LookupError, RecursionError):
            raise ParseError('The JSON request could not be parsed.') from None
