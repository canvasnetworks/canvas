from canvas import util, stickers
from canvas.tests.tests_helpers import CanvasTestCase
from canvas.util import ArgSpec, make_absolute_url
from django.conf import settings


class QuerySetMock(list):
    pass


class TestJsonEnconding(CanvasTestCase):
    def _assertJSON(self, value):
        self.assertEqual(value, util.loads(util.dumps(value)))

    def test_simplest_strings(self):
        self.assertEqual("{}", util.dumps({}))
        self.assertEqual("[]", util.dumps([]))

    def test_simple_data(self):
        self._assertJSON({"foo": "bar"})

    def test_client_dumps(self):
        self.assertEqual('{}', util.client_dumps({}))

    def test_sticker_details(self):
        util.client_dumps(stickers.all_details())


class TestAbsoluteUrls(CanvasTestCase):
    def setUp(self):
        super(TestAbsoluteUrls, self).setUp()
        self._domain, settings.DOMAIN = settings.DOMAIN, 'foo.com'

    def tearDown(self):
        settings.DOMAIN = self._domain
        super(TestAbsoluteUrls, self).tearDown()

    def test_without_prepended_slash(self):
        self.assertEqual('//foo.com/foo', make_absolute_url('foo'))

    def test_without_protocol(self):
        self.assertEqual('//foo.com/foo', make_absolute_url('/foo'))

    def test_with_protocol(self):
        self.assertEqual('https://foo.com/foo', make_absolute_url('/foo', protocol='https'))

    def test_already_absolute(self):
        self.assertEqual('https://foo.com/foo', make_absolute_url('https://foo.com/foo'))

    def test_already_absolute_without_protocol(self):
        self.assertEqual('//foo.com/foo', make_absolute_url('//foo.com/foo'))

    def test_already_absolute_without_protocol_with_kwarg(self):
        self.assertEqual('https://foo.com/foo', make_absolute_url('//foo.com/foo', protocol='https'))

    def test_base_path_with_protocol(self):
        self.assertEqual('https://foo.com/', make_absolute_url('/', protocol='https'))


class TestArgSpec(CanvasTestCase):
    def setUp(self):
        super(TestArgSpec, self).setUp()

        def foo(a, b, c=2, d=1, e=0): pass

        self.spec = ArgSpec(foo)

    def test_args_exclude_kwargs(self):
        self.assertEqual(self.spec.args, ['a', 'b'])

    def test_kwargs_exclude_args_and_have_defaults(self):
        self.assertEqual(self.spec.kwargs, {'c': 2, 'd': 1, 'e': 0})

    def test_empty_kwargs(self):
        def empty_kwargs(a, b, c): pass
        empty_kwargs_spec = ArgSpec(empty_kwargs)
        self.assertEqual(empty_kwargs_spec.args, ['a', 'b', 'c'])
        self.assertEqual(empty_kwargs_spec.kwargs, {})

    def test_empty_args(self):
        def empty_args(a=1, b=2): pass
        empty_args_spec = ArgSpec(empty_args)
        self.assertEqual(empty_args_spec.args, [])
        self.assertEqual(empty_args_spec.kwargs, {'a': 1, 'b': 2})

        
class TestIpIntConversion(CanvasTestCase):
    ip_int_pairs = [
        ('127.0.0.1', 16777343),
        ('0.0.0.0', 0),
        ('255.255.255.255', 256**4 - 1),
        ('12.34.56.78', 1312301580),
        ('87.65.43.21', 355156311),
    ]
    
    def test_known_ip_to_int(self):
        for (ip, integer) in self.ip_int_pairs:
            self.assertEqual(util.ip_to_int(ip), integer, "util.ip_to_int(%r) != %r" % (ip, integer))

    def test_known_int_to_ip(self):
        for (ip, integer) in self.ip_int_pairs:
            self.assertEqual(util.int_to_ip(integer), ip, "util.int_to_ip(%r) != %r" % (integer, ip))
            
    def test_malformed_input_ip_to_int(self):
        self.assertEqual(util.ip_to_int("2001:0db8:85a3:0000:0000:8a2e:0370:7334"), 0)
        self.assertEqual(util.ip_to_int("unknown"), 0)
        self.assertEqual(util.ip_to_int(None), 0)

class TestBase36(CanvasTestCase):
    happy_paths = [(1, '1j'), (100, '2su'), (101, '2td'), (999, 'rri'), (2**64, '3w5e11264sgsgc')]

    def test_encode_happy_paths(self):
        for happy_int, happy_b36 in self.happy_paths:
            self.assertEqual(util.base36encode(happy_int), happy_b36)

    def test_encode_negative_number_raises_ValueError(self):
        with self.assertRaises(ValueError):
            util.base36encode(-1)

    def test_decode_happy_paths(self):
        for happy_int, happy_b36 in self.happy_paths:
            self.assertEqual(util.base36decode(happy_b36), happy_int)
            
    def test_decode_bad_check_digit_raises_Base36DecodeException(self):
        with self.assertRaises(util.Base36DecodeException):
            util.base36decode('1x') # 1j is correct

    def test_decode_invalid_characters_raises_Base36DecodeException(self):
        with self.assertRaises(util.Base36DecodeException):
            util.base36decode('1!')
            
    def test_decode_negative_number_raises_Base36DecodeException(self):
        with self.assertRaises(util.Base36DecodeException):
            util.base36decode('-1j')

class TestPaginate(CanvasTestCase):
    def test_empty_iterable(self):
        segment, current, next, last = util.paginate(QuerySetMock([]), page=1, per_page=10)
        self.assertEqual(segment, [])
        self.assertEqual(current, 1)
        self.assertEqual(next, None)
        self.assertEqual(last, 1)
        
    def test_handles_string_page(self):
        segment, current, next, last = util.paginate(QuerySetMock(range(30)), page='2', per_page=10)
        self.assertEqual(segment, range(10, 20))
        self.assertEqual(current, 2)
        self.assertEqual(next, 3)
        self.assertEqual(last, 3)

    def test_onepage_iterable(self):
        segment, current, next, last = util.paginate(QuerySetMock(['a', 'b', 'c']), page=1, per_page=10)
        self.assertEqual(segment, ['a', 'b', 'c'])
        self.assertEqual(current, 1)
        self.assertEqual(next, None)
        self.assertEqual(last, 1)
        
    def test_multipage_firstpage(self):
        segment, current, next, last = util.paginate(QuerySetMock(range(25)), page=1, per_page=10)
        self.assertEqual(segment, range(10))
        self.assertEqual(current, 1)
        self.assertEqual(next, 2)
        self.assertEqual(last, 3)
        
    def test_multipage_middlepage(self):
        segment, current, next, last = util.paginate(QuerySetMock(range(25)), page=2, per_page=10)
        self.assertEqual(segment, range(10, 20))
        self.assertEqual(current, 2)
        self.assertEqual(next, 3)
        self.assertEqual(last, 3)
        
    def test_multipage_lastpage(self):
        segment, current, next, last = util.paginate(QuerySetMock(range(25)), page=3, per_page=10)
        self.assertEqual(segment, range(20, 25))
        self.assertEqual(current, 3)
        self.assertEqual(next, None)
        self.assertEqual(last, 3)
        
    def test_multipage_toohigh(self):
        segment, current, next, last = util.paginate(QuerySetMock(range(25)), page=4, per_page=10)
        self.assertEqual(segment, range(20, 25))
        self.assertEqual(current, 3)
        self.assertEqual(next, None)
        self.assertEqual(last, 3)
        
    def test_onefullpage_onlyonepage(self):
        segment, current, next, last = util.paginate(QuerySetMock(range(10)), page=1, per_page=10)
        self.assertEqual(segment, range(10))
        self.assertEqual(current, 1)
        self.assertEqual(next, None)
        self.assertEqual(last, 1)
        
    def test_onepage_current(self):
        segment, current, next, last = util.paginate(QuerySetMock(range(5)), page='current', per_page=10)
        self.assertEqual(segment, range(5))
        self.assertEqual(current, 1)
        self.assertEqual(next, None)
        self.assertEqual(last, 1)
        
    def test_onepage_large_current(self):
        segment, current, next, last = util.paginate(QuerySetMock(range(97)), page='current', per_page=100)
        self.assertEqual(segment, range(97))
        self.assertEqual(current, 1)
        self.assertEqual(next, None)
        self.assertEqual(last, 1)
        
    def test_multipage_current(self):
        segment, current, next, last = util.paginate(QuerySetMock(range(15)), page='current', per_page=10)
        self.assertEqual(segment, range(5,15))
        self.assertEqual(current, 2)
        self.assertEqual(next, None)
        self.assertEqual(last, 2)

class TestClamp(CanvasTestCase):
    def test_within_range_returns_value(self):
        self.assertEqual(4, util.clamp(0, 4, 10))
        self.assertEqual(0, util.clamp(-10, 0, 10))
        self.assertEqual(9, util.clamp(0, 9, 9))

    def test_below_lower_bound_returns_boundary(self):
        self.assertEqual(0, util.clamp(0, -4, 10))
        self.assertEqual(-10, util.clamp(-10, -15, 10))

    def test_above_upper_bound_returns_boundary(self):
        self.assertEqual(10, util.clamp(0, 15, 10))
        self.assertEqual(-10, util.clamp(-100, 42, -10))
