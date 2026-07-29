"""Phase 2 contract — tutor/textnorm.py named policies (PERMANENT).

Differential characterization (docs/reviews-architecture-refactor.md,
"Phase 2 landed"): EXPECTED below was captured 2026-07-28 by running the
PRE-migration implementations — session_memory._deaccent,
teach_assets._norm_key, character_sheet.normalize_error_pattern_id (its
fold step replicated verbatim as the fold_id source) and character_sheet.
fold, observe.word_present, task_runtime.phrase_present,
output_gate._key_match / gloss_after_key — over the probe corpus. The
textnorm named policies must reproduce these outputs byte-for-byte.

These pins are the CONTRACT of the named policies. fold_asset_key keys
the on-disk image cache; fold_id keys error-pattern ids in saved sheets;
fold_lexical keys the asked-topic registry — a semantic change to any of
them is a data migration, not a refactor. Any deliberate change is a
bugfix PR that updates BOTH the pin and the Phase 2 runbook entry.

The word_present vs phrase family divergences (MWU literal-whitespace,
empty-needle degenerate match) are pinned as NAMED-VARIANT behavior —
CHAR_BUG candidates, never silently unified (Phase 0 law: no silent
flips).
"""

from __future__ import annotations

import unittest

from tutor import textnorm
from tutor.textnorm import (
    SPANISH_LETTERS,
    fold_asset_key,
    fold_id,
    fold_lexical,
    fold_prose,
    phrase_match,
    phrase_present,
    word_present,
)


FOLD_CORPUS = ['',
 ' ',
 'café',
 'Café',
 'CAFÉ',
 'mamá',
 'niño',
 'Niño',
 'NIÑO',
 'pingüino',
 'güero',
 'AZÚCAR',
 'él',
 'qué',
 'más o menos',
 'buenos días',
 'el sol',
 'la casa',
 'el gato',
 'la ciudad',
 'el_gato',
 'la_ciudad',
 'el_la_casa',
 'la_única',
 'El Niño',
 'señor',
 'año',
 'leche',
 'café con leche',
 'está-calor',
 'esta calor',
 'weather-hace',
 'ser vs estar',
 'gender-agreement',
 'Está Calor',
 'ME LLAMO-ES',
 '¿Cómo estás?',
 '¡Hola!',
 'Me llamo, Ana.',
 '  spaced   words  ',
 'ü',
 'Ü',
 'ñ',
 '…',
 'papá…',
 'a.b',
 'quote"s',
 "it's",
 "don't",
 'über',
 'vôtre',
 'ça',
 'naïve',
 'coöperate',
 'hola\tmundo',
 'line\nbreak',
 'MAYÚSCULA-Ü',
 'año 2026',
 'sol2',
 'la  doble  espacio',
 'el ',
 'la ',
 'el_',
 'la_']

PATTERN_ID_CORPUS = ['',
 '  ',
 'weather_hace',
 'está_calor',
 'esta calor',
 'Está Calor',
 'weather',
 'Weather',
 'ser vs estar',
 'ser-vs-estar',
 'SER VS ESTAR',
 'gender agreement',
 'gender-agreement',
 'article_agreement',
 'me llama es',
 'me_llamo_es_x',
 'yo esta estar',
 'estar_person_yo_esta',
 'yo_esta',
 'tango',
 'tengo error',
 'soy_nerviosa',
 'soy_nervioso_feeling',
 'unknown_pattern_xyz',
 'años-plural',
 'número_wrong',
 'SOY_BIEN']

BOUNDARY_CORPUS = [('sol', 'Hola Marisol'),
 ('sol', 'el sol brilla'),
 ('sol', 'los soles'),
 ('sol', 'yo solo quiero'),
 ('sol', 'sol2'),
 ('sol', 'sol_'),
 ('sol', 'solx'),
 ('sol', 'solñ'),
 ('sol', 'SOL'),
 ('gato', 'gatos'),
 ('gato', 'gatas'),
 ('gato', 'el gatoes raro'),
 ('leche', 'quiero leche'),
 ('leche', 'lechero'),
 ('leche', 'leches'),
 ('bien', 'bienes'),
 ('bien', '¡Muy bien!'),
 ('muy bien', '¡Muy bien!'),
 ('es', 'es'),
 ('es', 'les'),
 ('está', 'estás'),
 ('está', 'está.'),
 ('te', 'té'),
 ('té', 'te'),
 ('café', 'café'),
 ('café', 'un cafe por favor'),
 ('cafe', 'un café por favor'),
 ('año', 'años'),
 ('año', 'añora'),
 ('pingüino', 'los pingüinos'),
 ('guero', 'güero'),
 ('cómo estás', 'Hola, ¿cómo estás hoy?'),
 ('cómo estás', 'cómo  estás'),
 ('cómo estás', 'cómo\nestás'),
 ('cómo estás', 'cómo\testás'),
 ('como estas', '¿cómo estás?'),
 ('buenos día', 'buenos días'),
 ('buenos  días', 'buenos días'),
 (' leche ', 'quiero leche'),
 ('que bebe', 'porque bebemos agua'),
 ('cómo está', 'cómo estás'),
 ('mucho gusto', '¡Mucho gusto, Patrick!'),
 ('mucho gusto', 'muchogusto'),
 ('hola', 'hola,'),
 ('hola', '«hola»'),
 ('hola', 'holas'),
 ('hola', 'holaes'),
 ('', ''),
 ('', 'hola'),
 ('', 'hola !'),
 ('', '!'),
 ('  ', 'a b'),
 ('  ', '!  !'),
 ('el agua', 'El agua está fría'),
 ('de nada', 'denada'),
 ('qué', 'que')]

GLOSS_CORPUS = [('hola', '«hola» (hello) is a greeting'),
 ('hola', 'hola (hello)'),
 ('hola', 'hola(hello)'),
 ('hola', '**hola** (hello)'),
 ('hola', 'hola — (hello)'),
 ('hola', 'hola: (hello)'),
 ('hola', 'holas (hello)'),
 ('hola', 'hola (a very long gloss with more than six words inside)'),
 ('mucho gusto', 'mucho gusto (nice to meet you)'),
 ('mucho gusto', 'mucho  gusto (nice to meet you)'),
 ('café', 'café (coffee)'),
 ('café', 'cafe (coffee)'),
 ('año', 'años (years)'),
 ('hola', 'no gloss here hola')]


def _bkey(n: str, t: str) -> str:
    return f"{n!r}|{t!r}"


EXPECTED = {'fold_lexical': {'': '',
                  ' ': ' ',
                  'café': 'cafe',
                  'Café': 'cafe',
                  'CAFÉ': 'cafe',
                  'mamá': 'mama',
                  'niño': 'niño',
                  'Niño': 'niño',
                  'NIÑO': 'niño',
                  'pingüino': 'pinguino',
                  'güero': 'guero',
                  'AZÚCAR': 'azucar',
                  'él': 'el',
                  'qué': 'que',
                  'más o menos': 'mas o menos',
                  'buenos días': 'buenos dias',
                  'el sol': 'el sol',
                  'la casa': 'la casa',
                  'el gato': 'el gato',
                  'la ciudad': 'la ciudad',
                  'el_gato': 'el_gato',
                  'la_ciudad': 'la_ciudad',
                  'el_la_casa': 'el_la_casa',
                  'la_única': 'la_unica',
                  'El Niño': 'el niño',
                  'señor': 'señor',
                  'año': 'año',
                  'leche': 'leche',
                  'café con leche': 'cafe con leche',
                  'está-calor': 'esta-calor',
                  'esta calor': 'esta calor',
                  'weather-hace': 'weather-hace',
                  'ser vs estar': 'ser vs estar',
                  'gender-agreement': 'gender-agreement',
                  'Está Calor': 'esta calor',
                  'ME LLAMO-ES': 'me llamo-es',
                  '¿Cómo estás?': '¿como estas?',
                  '¡Hola!': '¡hola!',
                  'Me llamo, Ana.': 'me llamo, ana.',
                  '  spaced   words  ': '  spaced   words  ',
                  'ü': 'u',
                  'Ü': 'u',
                  'ñ': 'ñ',
                  '…': '…',
                  'papá…': 'papa…',
                  'a.b': 'a.b',
                  'quote"s': 'quote"s',
                  "it's": "it's",
                  "don't": "don't",
                  'über': 'uber',
                  'vôtre': 'vôtre',
                  'ça': 'ça',
                  'naïve': 'naïve',
                  'coöperate': 'coöperate',
                  'hola\tmundo': 'hola\tmundo',
                  'line\nbreak': 'line\nbreak',
                  'MAYÚSCULA-Ü': 'mayuscula-u',
                  'año 2026': 'año 2026',
                  'sol2': 'sol2',
                  'la  doble  espacio': 'la  doble  espacio',
                  'el ': 'el ',
                  'la ': 'la ',
                  'el_': 'el_',
                  'la_': 'la_'},
 'fold_asset_key': {'': '',
                    ' ': '',
                    'café': 'cafe',
                    'Café': 'cafe',
                    'CAFÉ': 'cafe',
                    'mamá': 'mama',
                    'niño': 'nino',
                    'Niño': 'nino',
                    'NIÑO': 'nino',
                    'pingüino': 'pingüino',
                    'güero': 'güero',
                    'AZÚCAR': 'azucar',
                    'él': 'el',
                    'qué': 'que',
                    'más o menos': 'mas_o_menos',
                    'buenos días': 'buenos_dias',
                    'el sol': 'sol',
                    'la casa': 'casa',
                    'el gato': 'gato',
                    'la ciudad': 'ciudad',
                    'el_gato': 'gato',
                    'la_ciudad': 'ciudad',
                    'el_la_casa': 'casa',
                    'la_única': 'unica',
                    'El Niño': 'nino',
                    'señor': 'senor',
                    'año': 'ano',
                    'leche': 'leche',
                    'café con leche': 'cafe_con_leche',
                    'está-calor': 'esta-calor',
                    'esta calor': 'esta_calor',
                    'weather-hace': 'weather-hace',
                    'ser vs estar': 'ser_vs_estar',
                    'gender-agreement': 'gender-agreement',
                    'Está Calor': 'esta_calor',
                    'ME LLAMO-ES': 'me_llamo-es',
                    '¿Cómo estás?': '¿como_estas?',
                    '¡Hola!': '¡hola!',
                    'Me llamo, Ana.': 'me_llamo,_ana',
                    '  spaced   words  ': 'spaced___words',
                    'ü': 'ü',
                    'Ü': 'ü',
                    'ñ': 'n',
                    '…': '',
                    'papá…': 'papa',
                    'a.b': 'ab',
                    'quote"s': 'quote"s',
                    "it's": "it's",
                    "don't": "don't",
                    'über': 'über',
                    'vôtre': 'vôtre',
                    'ça': 'ça',
                    'naïve': 'naïve',
                    'coöperate': 'coöperate',
                    'hola\tmundo': 'hola\tmundo',
                    'line\nbreak': 'line\nbreak',
                    'MAYÚSCULA-Ü': 'mayuscula-ü',
                    'año 2026': 'ano_2026',
                    'sol2': 'sol2',
                    'la  doble  espacio': '_doble__espacio',
                    'el ': 'el',
                    'la ': 'la',
                    'el_': '',
                    'la_': ''},
 'fold_prose': {'': '',
                ' ': '',
                'café': 'cafe',
                'Café': 'cafe',
                'CAFÉ': 'cafe',
                'mamá': 'mama',
                'niño': 'nino',
                'Niño': 'nino',
                'NIÑO': 'nino',
                'pingüino': 'pinguino',
                'güero': 'guero',
                'AZÚCAR': 'azucar',
                'él': 'el',
                'qué': 'que',
                'más o menos': 'mas o menos',
                'buenos días': 'buenos dias',
                'el sol': 'el sol',
                'la casa': 'la casa',
                'el gato': 'el gato',
                'la ciudad': 'la ciudad',
                'el_gato': 'el_gato',
                'la_ciudad': 'la_ciudad',
                'el_la_casa': 'el_la_casa',
                'la_única': 'la_unica',
                'El Niño': 'el nino',
                'señor': 'senor',
                'año': 'ano',
                'leche': 'leche',
                'café con leche': 'cafe con leche',
                'está-calor': 'esta-calor',
                'esta calor': 'esta calor',
                'weather-hace': 'weather-hace',
                'ser vs estar': 'ser vs estar',
                'gender-agreement': 'gender-agreement',
                'Está Calor': 'esta calor',
                'ME LLAMO-ES': 'me llamo-es',
                '¿Cómo estás?': 'como estas',
                '¡Hola!': 'hola',
                'Me llamo, Ana.': 'me llamo ana',
                '  spaced   words  ': 'spaced words',
                'ü': 'u',
                'Ü': 'u',
                'ñ': 'n',
                '…': '…',
                'papá…': 'papa…',
                'a.b': 'ab',
                'quote"s': 'quotes',
                "it's": 'its',
                "don't": 'dont',
                'über': 'uber',
                'vôtre': 'votre',
                'ça': 'ca',
                'naïve': 'naive',
                'coöperate': 'cooperate',
                'hola\tmundo': 'hola mundo',
                'line\nbreak': 'line break',
                'MAYÚSCULA-Ü': 'mayuscula-u',
                'año 2026': 'ano 2026',
                'sol2': 'sol2',
                'la  doble  espacio': 'la doble espacio',
                'el ': 'el',
                'la ': 'la',
                'el_': 'el_',
                'la_': 'la_'},
 'normalize_pattern_id': {'': '',
                          '  ': '',
                          'weather_hace': 'weather_hace',
                          'está_calor': 'weather_hace',
                          'esta calor': 'weather_hace',
                          'Está Calor': 'weather_hace',
                          'weather': 'weather_hace',
                          'Weather': 'weather_hace',
                          'ser vs estar': 'ser_estar_confuse',
                          'ser-vs-estar': 'ser_estar_confuse',
                          'SER VS ESTAR': 'ser_estar_confuse',
                          'gender agreement': 'gender_number_article',
                          'gender-agreement': 'gender_number_article',
                          'article_agreement': 'gender_number_article',
                          'me llama es': 'me_llamo_es',
                          'me_llamo_es_x': 'me_llamo_es',
                          'yo esta estar': 'estar_yo_estoy_vs_esta',
                          'estar_person_yo_esta': 'estar_yo_estoy_vs_esta',
                          'yo_esta': 'estar_yo_estoy_vs_esta',
                          'tango': 'tengo_not_tango',
                          'tengo error': 'tengo_not_tango',
                          'soy_nerviosa': 'ser_estar_confuse',
                          'soy_nervioso_feeling': 'ser_estar_confuse',
                          'unknown_pattern_xyz': 'unknown_pattern_xyz',
                          'años-plural': 'años-plural',
                          'número_wrong': 'número_wrong',
                          'SOY_BIEN': 'ser_estar_confuse'},
 'word_present': {"'sol'|'Hola Marisol'": False,
                  "'sol'|'el sol brilla'": True,
                  "'sol'|'los soles'": True,
                  "'sol'|'yo solo quiero'": False,
                  "'sol'|'sol2'": True,
                  "'sol'|'sol_'": True,
                  "'sol'|'solx'": False,
                  "'sol'|'solñ'": False,
                  "'sol'|'SOL'": True,
                  "'gato'|'gatos'": True,
                  "'gato'|'gatas'": False,
                  "'gato'|'el gatoes raro'": True,
                  "'leche'|'quiero leche'": True,
                  "'leche'|'lechero'": False,
                  "'leche'|'leches'": True,
                  "'bien'|'bienes'": True,
                  "'bien'|'¡Muy bien!'": True,
                  "'muy bien'|'¡Muy bien!'": True,
                  "'es'|'es'": True,
                  "'es'|'les'": False,
                  "'está'|'estás'": True,
                  "'está'|'está.'": True,
                  "'te'|'té'": False,
                  "'té'|'te'": False,
                  "'café'|'café'": True,
                  "'café'|'un cafe por favor'": False,
                  "'cafe'|'un café por favor'": False,
                  "'año'|'años'": True,
                  "'año'|'añora'": False,
                  "'pingüino'|'los pingüinos'": True,
                  "'guero'|'güero'": False,
                  "'cómo estás'|'Hola, ¿cómo estás hoy?'": True,
                  "'cómo estás'|'cómo  estás'": False,
                  "'cómo estás'|'cómo\\nestás'": False,
                  "'cómo estás'|'cómo\\testás'": False,
                  "'como estas'|'¿cómo estás?'": False,
                  "'buenos día'|'buenos días'": True,
                  "'buenos  días'|'buenos días'": False,
                  "' leche '|'quiero leche'": False,
                  "'que bebe'|'porque bebemos agua'": False,
                  "'cómo está'|'cómo estás'": True,
                  "'mucho gusto'|'¡Mucho gusto, Patrick!'": True,
                  "'mucho gusto'|'muchogusto'": False,
                  "'hola'|'hola,'": True,
                  "'hola'|'«hola»'": True,
                  "'hola'|'holas'": True,
                  "'hola'|'holaes'": True,
                  "''|''": True,
                  "''|'hola'": False,
                  "''|'hola !'": True,
                  "''|'!'": True,
                  "'  '|'a b'": False,
                  "'  '|'!  !'": True,
                  "'el agua'|'El agua está fría'": True,
                  "'de nada'|'denada'": False,
                  "'qué'|'que'": False},
 'phrase_present': {"'sol'|'Hola Marisol'": False,
                    "'sol'|'el sol brilla'": True,
                    "'sol'|'los soles'": True,
                    "'sol'|'yo solo quiero'": False,
                    "'sol'|'sol2'": True,
                    "'sol'|'sol_'": True,
                    "'sol'|'solx'": False,
                    "'sol'|'solñ'": False,
                    "'sol'|'SOL'": True,
                    "'gato'|'gatos'": True,
                    "'gato'|'gatas'": False,
                    "'gato'|'el gatoes raro'": True,
                    "'leche'|'quiero leche'": True,
                    "'leche'|'lechero'": False,
                    "'leche'|'leches'": True,
                    "'bien'|'bienes'": True,
                    "'bien'|'¡Muy bien!'": True,
                    "'muy bien'|'¡Muy bien!'": True,
                    "'es'|'es'": True,
                    "'es'|'les'": False,
                    "'está'|'estás'": True,
                    "'está'|'está.'": True,
                    "'te'|'té'": False,
                    "'té'|'te'": False,
                    "'café'|'café'": True,
                    "'café'|'un cafe por favor'": False,
                    "'cafe'|'un café por favor'": False,
                    "'año'|'años'": True,
                    "'año'|'añora'": False,
                    "'pingüino'|'los pingüinos'": True,
                    "'guero'|'güero'": False,
                    "'cómo estás'|'Hola, ¿cómo estás hoy?'": True,
                    "'cómo estás'|'cómo  estás'": True,
                    "'cómo estás'|'cómo\\nestás'": True,
                    "'cómo estás'|'cómo\\testás'": True,
                    "'como estas'|'¿cómo estás?'": False,
                    "'buenos día'|'buenos días'": True,
                    "'buenos  días'|'buenos días'": True,
                    "' leche '|'quiero leche'": True,
                    "'que bebe'|'porque bebemos agua'": False,
                    "'cómo está'|'cómo estás'": True,
                    "'mucho gusto'|'¡Mucho gusto, Patrick!'": True,
                    "'mucho gusto'|'muchogusto'": False,
                    "'hola'|'hola,'": True,
                    "'hola'|'«hola»'": True,
                    "'hola'|'holas'": True,
                    "'hola'|'holaes'": True,
                    "''|''": False,
                    "''|'hola'": False,
                    "''|'hola !'": False,
                    "''|'!'": False,
                    "'  '|'a b'": False,
                    "'  '|'!  !'": False,
                    "'el agua'|'El agua está fría'": True,
                    "'de nada'|'denada'": False,
                    "'qué'|'que'": False},
 'phrase_match_spans': {"'sol'|'Hola Marisol'": None,
                        "'sol'|'el sol brilla'": [3, 6],
                        "'sol'|'los soles'": [4, 9],
                        "'sol'|'yo solo quiero'": None,
                        "'sol'|'sol2'": [0, 3],
                        "'sol'|'sol_'": [0, 3],
                        "'sol'|'solx'": None,
                        "'sol'|'solñ'": None,
                        "'sol'|'SOL'": [0, 3],
                        "'gato'|'gatos'": [0, 5],
                        "'gato'|'gatas'": None,
                        "'gato'|'el gatoes raro'": [3, 9],
                        "'leche'|'quiero leche'": [7, 12],
                        "'leche'|'lechero'": None,
                        "'leche'|'leches'": [0, 6],
                        "'bien'|'bienes'": [0, 6],
                        "'bien'|'¡Muy bien!'": [5, 9],
                        "'muy bien'|'¡Muy bien!'": [1, 9],
                        "'es'|'es'": [0, 2],
                        "'es'|'les'": None,
                        "'está'|'estás'": [0, 5],
                        "'está'|'está.'": [0, 4],
                        "'te'|'té'": None,
                        "'té'|'te'": None,
                        "'café'|'café'": [0, 4],
                        "'café'|'un cafe por favor'": None,
                        "'cafe'|'un café por favor'": None,
                        "'año'|'años'": [0, 4],
                        "'año'|'añora'": None,
                        "'pingüino'|'los pingüinos'": [4, 13],
                        "'guero'|'güero'": None,
                        "'cómo estás'|'Hola, ¿cómo estás hoy?'": [7, 17],
                        "'cómo estás'|'cómo  estás'": [0, 11],
                        "'cómo estás'|'cómo\\nestás'": [0, 10],
                        "'cómo estás'|'cómo\\testás'": [0, 10],
                        "'como estas'|'¿cómo estás?'": None,
                        "'buenos día'|'buenos días'": [0, 11],
                        "'buenos  días'|'buenos días'": [0, 11],
                        "' leche '|'quiero leche'": [7, 12],
                        "'que bebe'|'porque bebemos agua'": None,
                        "'cómo está'|'cómo estás'": [0, 10],
                        "'mucho gusto'|'¡Mucho gusto, Patrick!'": [1, 12],
                        "'mucho gusto'|'muchogusto'": None,
                        "'hola'|'hola,'": [0, 4],
                        "'hola'|'«hola»'": [1, 5],
                        "'hola'|'holas'": [0, 5],
                        "'hola'|'holaes'": [0, 6],
                        "''|''": None,
                        "''|'hola'": None,
                        "''|'hola !'": None,
                        "''|'!'": None,
                        "'  '|'a b'": None,
                        "'  '|'!  !'": None,
                        "'el agua'|'El agua está fría'": [0, 7],
                        "'de nada'|'denada'": None,
                        "'qué'|'que'": None},
 'gloss_after_key': {"'hola'|'«hola» (hello) is a greeting'": False,
                     "'hola'|'hola (hello)'": True,
                     "'hola'|'hola(hello)'": True,
                     "'hola'|'**hola** (hello)'": True,
                     "'hola'|'hola — (hello)'": True,
                     "'hola'|'hola: (hello)'": True,
                     "'hola'|'holas (hello)'": True,
                     "'hola'|'hola (a very long gloss with more than six words inside)'": False,
                     "'mucho gusto'|'mucho gusto (nice to meet you)'": True,
                     "'mucho gusto'|'mucho  gusto (nice to meet you)'": True,
                     "'café'|'café (coffee)'": True,
                     "'café'|'cafe (coffee)'": False,
                     "'año'|'años (years)'": True,
                     "'hola'|'no gloss here hola'": False},
 'fold_id': {'': '',
             '  ': '__',
             'weather_hace': 'weather_hace',
             'está_calor': 'esta_calor',
             'esta calor': 'esta_calor',
             'Está Calor': 'esta_calor',
             'weather': 'weather',
             'Weather': 'weather',
             'ser vs estar': 'ser_vs_estar',
             'ser-vs-estar': 'ser_vs_estar',
             'SER VS ESTAR': 'ser_vs_estar',
             'gender agreement': 'gender_agreement',
             'gender-agreement': 'gender_agreement',
             'article_agreement': 'article_agreement',
             'me llama es': 'me_llama_es',
             'me_llamo_es_x': 'me_llamo_es_x',
             'yo esta estar': 'yo_esta_estar',
             'estar_person_yo_esta': 'estar_person_yo_esta',
             'yo_esta': 'yo_esta',
             'tango': 'tango',
             'tengo error': 'tengo_error',
             'soy_nerviosa': 'soy_nerviosa',
             'soy_nervioso_feeling': 'soy_nervioso_feeling',
             'unknown_pattern_xyz': 'unknown_pattern_xyz',
             'años-plural': 'anos_plural',
             'número_wrong': 'numero_wrong',
             'SOY_BIEN': 'soy_bien',
             ' ': '_',
             'café': 'cafe',
             'Café': 'cafe',
             'CAFÉ': 'cafe',
             'mamá': 'mama',
             'niño': 'nino',
             'Niño': 'nino',
             'NIÑO': 'nino',
             'pingüino': 'pingüino',
             'güero': 'güero',
             'AZÚCAR': 'azucar',
             'él': 'el',
             'qué': 'que',
             'más o menos': 'mas_o_menos',
             'buenos días': 'buenos_dias',
             'el sol': 'el_sol',
             'la casa': 'la_casa',
             'el gato': 'el_gato',
             'la ciudad': 'la_ciudad',
             'el_gato': 'el_gato',
             'la_ciudad': 'la_ciudad',
             'el_la_casa': 'el_la_casa',
             'la_única': 'la_unica',
             'El Niño': 'el_nino',
             'señor': 'senor',
             'año': 'ano',
             'leche': 'leche',
             'café con leche': 'cafe_con_leche',
             'está-calor': 'esta_calor',
             'weather-hace': 'weather_hace',
             'ME LLAMO-ES': 'me_llamo_es',
             '¿Cómo estás?': '¿como_estas?',
             '¡Hola!': '¡hola!',
             'Me llamo, Ana.': 'me_llamo,_ana.',
             '  spaced   words  ': '__spaced___words__',
             'ü': 'ü',
             'Ü': 'ü',
             'ñ': 'n',
             '…': '…',
             'papá…': 'papa…',
             'a.b': 'a.b',
             'quote"s': 'quote"s',
             "it's": "it's",
             "don't": "don't",
             'über': 'über',
             'vôtre': 'vôtre',
             'ça': 'ça',
             'naïve': 'naïve',
             'coöperate': 'coöperate',
             'hola\tmundo': 'hola\tmundo',
             'line\nbreak': 'line\nbreak',
             'MAYÚSCULA-Ü': 'mayuscula_ü',
             'año 2026': 'ano_2026',
             'sol2': 'sol2',
             'la  doble  espacio': 'la__doble__espacio',
             'el ': 'el_',
             'la ': 'la_',
             'el_': 'el_',
             'la_': 'la_'}}


class TestFoldPolicies(unittest.TestCase):
    """The three (plus one) named fold policies, byte-exact."""

    def test_fold_lexical(self):
        for s in FOLD_CORPUS:
            self.assertEqual(
                fold_lexical(s), EXPECTED["fold_lexical"][s], repr(s))

    def test_fold_asset_key(self):
        for s in FOLD_CORPUS:
            self.assertEqual(
                fold_asset_key(s), EXPECTED["fold_asset_key"][s], repr(s))

    def test_fold_prose(self):
        for s in FOLD_CORPUS:
            self.assertEqual(
                fold_prose(s), EXPECTED["fold_prose"][s], repr(s))

    def test_fold_id(self):
        for s in PATTERN_ID_CORPUS + FOLD_CORPUS:
            self.assertEqual(fold_id(s), EXPECTED["fold_id"][s], repr(s))

    def test_policies_are_deliberately_incompatible(self):
        # The merge-refusal law in one assertion each: ü (lexical folds it,
        # asset key keeps it), ñ (lexical keeps it, asset/id/prose fold it),
        # article strip (asset only), hyphen (id only), punctuation+NFD
        # (prose only).
        self.assertEqual(fold_lexical("pingüino"), "pinguino")
        self.assertEqual(fold_asset_key("pingüino"), "pingüino")
        self.assertEqual(fold_lexical("año"), "año")
        self.assertEqual(fold_asset_key("año"), "ano")
        self.assertEqual(fold_id("año"), "ano")
        self.assertEqual(fold_prose("año"), "ano")
        self.assertEqual(fold_asset_key("el sol"), "sol")
        self.assertEqual(fold_id("el sol"), "el_sol")
        self.assertEqual(fold_id("ser-vs-estar"), "ser_vs_estar")
        self.assertEqual(fold_asset_key("ser-vs-estar"), "ser-vs-estar")
        self.assertEqual(fold_prose("¡Hola!"), "hola")
        self.assertEqual(fold_lexical("¡Hola!"), "¡hola!")

    def test_normalize_error_pattern_id_end_to_end(self):
        # The caller around fold_id: catalog/alias/fuzzy resolution intact.
        from tutor.character_sheet import normalize_error_pattern_id
        for s in PATTERN_ID_CORPUS:
            self.assertEqual(
                normalize_error_pattern_id(s),
                EXPECTED["normalize_pattern_id"][s], repr(s))


class TestBoundaryMatchers(unittest.TestCase):
    """word_present + the phrase family, byte-exact per caller."""

    def test_word_present(self):
        for n, t in BOUNDARY_CORPUS:
            self.assertEqual(
                word_present(n, t),
                EXPECTED["word_present"][_bkey(n, t)], _bkey(n, t))

    def test_phrase_present(self):
        for n, t in BOUNDARY_CORPUS:
            self.assertEqual(
                phrase_present(n, t),
                EXPECTED["phrase_present"][_bkey(n, t)], _bkey(n, t))

    def test_phrase_match_spans(self):
        # output_gate's overlap filter consumes .start()/.end() — the spans
        # are contract, not just truthiness.
        for n, t in BOUNDARY_CORPUS:
            m = phrase_match(n, t)
            got = [m.start(), m.end()] if m else None
            self.assertEqual(
                got, EXPECTED["phrase_match_spans"][_bkey(n, t)],
                _bkey(n, t))

    def test_phrase_present_is_bool_of_phrase_match(self):
        for n, t in BOUNDARY_CORPUS:
            self.assertEqual(
                phrase_present(n, t), phrase_match(n, t) is not None,
                _bkey(n, t))

    def test_named_variant_divergences(self):
        r"""The characterized word_present ≠ phrase family probes.

        CHAR_BUG candidates (Phase 2 runbook): (1) MWU whitespace —
        word_present needs the needle's literal spacing, phrase family
        matches \s+, yet BOTH scan the same table keys (conv_session
        mark_introduced_if_visible vs output_gate's new-item scan);
        (2) empty-needle — word_present degenerates to a boundary-only
        pattern that can match. Deliberately NOT unified here; a fix is
        a bugfix PR that updates these pins.
        """
        divergent = [       "'  '|'!  !'",
        "' leche '|'quiero leche'",
        "''|'!'",
        "''|''",
        "''|'hola !'",
        "'buenos  días'|'buenos días'",
        "'cómo estás'|'cómo  estás'",
        "'cómo estás'|'cómo\\nestás'",
        "'cómo estás'|'cómo\\testás'"]
        for key in divergent:
            self.assertNotEqual(
                EXPECTED["word_present"][key],
                EXPECTED["phrase_present"][key], key)
        for n, t in BOUNDARY_CORPUS:
            key = _bkey(n, t)
            if key not in divergent:
                self.assertEqual(
                    EXPECTED["word_present"][key],
                    EXPECTED["phrase_present"][key], key)

    def test_gloss_after_key(self):
        # gloss_after_key recomposed over textnorm.phrase_body — regex
        # byte-identity insurance.
        from tutor.output_gate import gloss_after_key
        for n, t in GLOSS_CORPUS:
            self.assertEqual(
                gloss_after_key(n, t),
                EXPECTED["gloss_after_key"][_bkey(n, t)], _bkey(n, t))


class TestCallerBindings(unittest.TestCase):
    """Every migrated module binds THE shared object — a re-added local
    copy (drift vector) breaks identity, not just equality."""

    def test_facade_reexports_are_the_shared_functions(self):
        from tutor import observe, task_runtime
        self.assertIs(observe.word_present, textnorm.word_present)
        self.assertIs(task_runtime.phrase_present, textnorm.phrase_present)

    def test_fold_aliases_are_the_named_policies(self):
        from tutor import character_sheet, teach_assets
        self.assertIs(teach_assets._norm_key, textnorm.fold_asset_key)
        self.assertIs(character_sheet.fold, textnorm.fold_prose)
        self.assertIs(character_sheet.fold_id, textnorm.fold_id)

    def test_gate_and_memory_share_fold_lexical(self):
        # The dead private crossing (output_gate → session_memory._deaccent)
        # stays dead: both sides now hold the PUBLIC policy.
        from tutor import output_gate, session_memory
        self.assertIs(output_gate.fold_lexical, textnorm.fold_lexical)
        self.assertIs(session_memory.fold_lexical, textnorm.fold_lexical)
        self.assertFalse(hasattr(session_memory, "_deaccent"))
        self.assertFalse(hasattr(output_gate, "_key_match"))
        self.assertFalse(hasattr(output_gate, "_ES_BOUND"))

    def test_letter_class_single_source(self):
        from tutor import observe, output_gate, turn_morph, tutor_response
        self.assertEqual(SPANISH_LETTERS, "a-záéíóúüñ")
        self.assertIs(observe._ES_LETTERS, SPANISH_LETTERS)
        self.assertIs(turn_morph._ES, SPANISH_LETTERS)
        self.assertIs(output_gate.SPANISH_LETTERS, SPANISH_LETTERS)
        self.assertEqual(
            tutor_response._CONCEPT_TOKEN,
            rf"[{SPANISH_LETTERS}_]{{1,24}}")


if __name__ == "__main__":
    unittest.main()
